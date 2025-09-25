from __future__ import annotations

"""Whisper transcription service with flexible audio backends.

This module provides a `Service` class for transcription/translation using
OpenAI Whisper via Hugging Face `transformers`. It includes robust utilities to
load audio from various sources (local path, relative path, URL, Base64),
convert it to mono 16 kHz float32 samples using multiple optional backends, and
run recognition either via a `pipeline` or directly with model/processor.

All code is formatted to PEP 8, with English-only comments and docstrings.
"""

from pathlib import Path
import base64
import io
from typing import Any
from urllib.parse import urlparse

import requests  # Lightweight and useful for fetching audio from URLs

from app.services.base import BaseService

# ======== Discovery & configuration shims (for wrapper generators) ========
MODEL_ID = "openai/whisper-small"  # centralize model id

# Some generators look for module-level tasks or a callable instead of class attrs
TASKS = ["transcribe"]

def get_tasks() -> list[str]:
    """Return available task identifiers (discovery shim)."""
    return TASKS


# ========= Optional safe imports =========
try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None  # type: ignore[assignment]

# Try several audio packages; any one is sufficient.
try:
    import soundfile as sf  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    sf = None  # type: ignore[assignment]

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    librosa = None  # type: ignore[assignment]

try:
    import torch  # type: ignore
    import torchaudio  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    torch = None  # type: ignore[assignment]
    torchaudio = None  # type: ignore[assignment]

# Optional transformers; prefer `pipeline`, then direct model/processor.
try:
    from transformers import (
        AutoProcessor,
        WhisperForConditionalGeneration,
        pipeline,
    )  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    AutoProcessor = None  # type: ignore[assignment]
    WhisperForConditionalGeneration = None  # type: ignore[assignment]
    pipeline = None  # type: ignore[assignment]


# ========= General helper utilities =========

def _is_url(s: str) -> bool:
    """Return True if *s* looks like an HTTP(S) URL."""
    try:
        parsed = urlparse(str(s))
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def _fetch_bytes_from_url(url: str, timeout: int = 30) -> bytes:
    """Fetch raw bytes from a URL."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _ensure_numpy() -> None:
    """Ensure NumPy is available, otherwise raise a runtime error."""
    if np is None:  # type: ignore[truthy-bool]
        raise RuntimeError("numpy not installed")


# ========= Load audio to mono@16k =========

def _load_audio_mono16k(audio_bytes: bytes) -> tuple[list[float], int]:
    """Convert arbitrary audio bytes to mono float32 samples at 16 kHz."""
    # soundfile (+ librosa for resampling)
    if sf is not None:
        try:
            with io.BytesIO(audio_bytes) as bio:
                data, sr = sf.read(bio, dtype="float32", always_2d=False)

            # Ensure mono: average channels if needed.
            if getattr(data, "ndim", 1) > 1:
                try:
                    import numpy as _np
                    if data.ndim == 2:
                        if data.shape[0] < data.shape[1]:
                            data = data.mean(axis=0)
                        else:
                            data = data.mean(axis=1)
                    else:
                        data = data.squeeze()
                except Exception:
                    data = data.mean(axis=0) if hasattr(data, "mean") else data

            # Resample to 16 kHz.
            if sr != 16000:
                if librosa is not None:
                    data = librosa.resample(y=data, orig_sr=sr, target_sr=16000)
                    sr = 16000
                else:
                    _ensure_numpy()
                    ratio = 16000 / float(sr)
                    new_len = int(round(len(data) * ratio))
                    if new_len > 1:
                        x_old = np.linspace(0, 1, num=len(data), endpoint=False)
                        x_new = np.linspace(0, 1, num=new_len, endpoint=False)
                        data = np.interp(x_new, x_old, data).astype("float32")
                        sr = 16000

            return (data.tolist(), 16000)
        except Exception:
            pass

    # librosa directly
    if librosa is not None:
        try:
            y, _sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)
            return (y.astype("float32").tolist(), 16000)
        except Exception:
            pass

    # torchaudio
    if (torch is not None) and (torchaudio is not None):
        try:
            with io.BytesIO(audio_bytes) as bio:
                wav, sr = torchaudio.load(bio)  # [C, T]

            if wav.dim() == 2 and wav.size(0) > 1:
                wav = wav.mean(dim=0, keepdim=True)

            wav = wav.squeeze(0)

            if sr != 16000:
                wav = torchaudio.transforms.Resample(sr, 16000)(wav)
                sr = 16000

            _ensure_numpy()
            return (
                wav.to(dtype=torch.float32).cpu().numpy().tolist(),
                16000,
            )
        except Exception:
            pass

    raise RuntimeError(
        "No audio backend available. Install one of: soundfile, librosa, or torchaudio."
    )


def _read_audio_from_payload(payload: dict[str, Any]) -> tuple[list[float], int]:
    """Read audio contents from the given payload and convert to mono 16 kHz."""
    rel_path = payload.get("rel_path")
    if rel_path:
        p = Path("uploads") / str(rel_path)
        if not p.is_file():
            p = Path("uploads") / Path(str(rel_path))
        p = p.resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Audio file not found: {p}")
        return _load_audio_mono16k(p.read_bytes())

    path = payload.get("path")
    if path and not _is_url(str(path)):
        p = Path(str(path)).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Audio file not found: {p}")
        return _load_audio_mono16k(p.read_bytes())

    url = payload.get("url")
    if url and _is_url(str(url)):
        return _load_audio_mono16k(_fetch_bytes_from_url(str(url)))

    b64 = payload.get("base64")
    if b64:
        if isinstance(b64, dict):
            b64 = b64.get("data")
        return _load_audio_mono16k(base64.b64decode(str(b64)))

    raise ValueError("Provide one of: rel_path | path | url | base64")


# ========= Whisper Service =========

class Service(BaseService):
    """Whisper service wrapping `transformers` ASR/translation."""

    name = "whisper"
    tasks = ["transcribe"]

    _MODEL = None
    _PROCESSOR = None
    _PIPELINE = None

    def load(self) -> None:
        return

    def _ensure_loaded(self) -> None:
        if (
            self._PIPELINE is not None
            or (self._MODEL is not None and self._PROCESSOR is not None)
        ):
            return

        if pipeline is not None and AutoProcessor is not None:
            try:
                proc = AutoProcessor.from_pretrained(MODEL_ID)
                self._PIPELINE = pipeline(
                    "automatic-speech-recognition",
                    model=MODEL_ID,
                    tokenizer=proc.tokenizer,
                    feature_extractor=proc.feature_extractor,
                    device_map="auto",
                )
                return
            except Exception:
                self._PIPELINE = None

        if AutoProcessor is not None and WhisperForConditionalGeneration is not None:
            try:
                self._PROCESSOR = AutoProcessor.from_pretrained(MODEL_ID)
                self._MODEL = WhisperForConditionalGeneration.from_pretrained(MODEL_ID)
            except Exception:
                self._PROCESSOR = None
                self._MODEL = None

    def transcribe(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Transcribe or translate audio using Whisper."""
        if np is None:  # type: ignore[truthy-bool]
            return {"ok": False, "error": "numpy not installed"}

        try:
            samples, sr = _read_audio_from_payload(payload or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return_segments = bool(payload.get("return_segments", False))
        explicit_lang = payload.get("language")

        task = (payload.get("task") or "").strip().lower()
        if task not in ("", "transcribe", "translate"):
            task = "transcribe"
        if str(payload.get("translate", "")).lower() in ("1", "true", "yes"):
            task = "translate"

        self._ensure_loaded()

        if self._PIPELINE is not None:
            try:
                pipe_kwargs: dict[str, Any] = {
                    "return_timestamps": "word" if return_segments else False
                }
                if payload.get("chunk_length_s") is not None:
                    pipe_kwargs["chunk_length_s"] = float(payload["chunk_length_s"])
                if payload.get("stride_length_s") is not None:
                    pipe_kwargs["stride_length_s"] = float(payload["stride_length_s"])

                if explicit_lang:
                    pipe_kwargs["generate_kwargs"] = {
                        "language": explicit_lang,
                        "task": task or "transcribe",
                    }
                elif task:
                    pipe_kwargs["generate_kwargs"] = {"task": task}

                audio_np = np.asarray(samples, dtype="float32")  # type: ignore[attr-defined]
                out = self._PIPELINE(audio_np, **pipe_kwargs)

                text = (
                    out.get("text") if isinstance(out, dict) and "text" in out else str(out)
                )
                language = (
                    out.get("language") if isinstance(out, dict) else explicit_lang or None
                )
                result: dict[str, Any] = {
                    "ok": True,
                    "text": text,
                    "language": language,
                    "sample_rate": sr,
                }

                if return_segments:
                    segments = []
                    if (
                        isinstance(out, dict)
                        and "chunks" in out
                        and isinstance(out["chunks"], list)
                    ):
                        for ch in out["chunks"]:
                            segments.append(
                                {
                                    "text": ch.get("text"),
                                    "timestamp": ch.get("timestamp"),
                                }
                            )
                    result["segments"] = segments

                return result
            except Exception:
                pass

        if self._MODEL is None or self._PROCESSOR is None or AutoProcessor is None:
            return {
                "ok": False,
                "error": "transformers not available (pipeline/model/processor)",
            }

        try:
            feats = self._PROCESSOR.feature_extractor(  # type: ignore[union-attr]
                np.asarray(samples, dtype="float32"),  # type: ignore[attr-defined]
                sampling_rate=sr,
                return_tensors="pt",
            )
            input_features = feats.input_features

            gen_kwargs: dict[str, Any] = {}
            if explicit_lang:
                gen_kwargs["language"] = explicit_lang
            if task in ("transcribe", "translate"):
                gen_kwargs["task"] = task

            self._MODEL.eval()  # type: ignore[union-attr]
            pred_ids = self._MODEL.generate(  # type: ignore[union-attr]
                input_features,
                max_new_tokens=int(payload.get("max_new_tokens", 448)),
                num_beams=int(payload.get("num_beams", 1)),
            )
            text = self._PROCESSOR.tokenizer.batch_decode(  # type: ignore[union-attr]
                pred_ids, skip_special_tokens=True
            )[0]
            return {"ok": True, "text": text, "language": explicit_lang, "sample_rate": sr}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
