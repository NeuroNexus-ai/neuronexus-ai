# fastapi/app/services/embeddings/service.py
from __future__ import annotations

import os
import json
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.base import BaseService

# ========== Imports الآمنة ==========
try:
    import torch
except Exception:
    torch = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None


# ========== إعدادات عامة ==========
DEFAULT_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "intfloat/multilingual-e5-base")
EMBED_DIM = int(os.getenv("EMBEDDINGS_DIM", "768"))  # غيّرها لو اخترت نموذج أبعاد مختلفة
DATABASE_URL = os.getenv("DATABASE_URL")

# جداول / أسماء
EXTENSION_SQL = "CREATE EXTENSION IF NOT EXISTS vector;"
TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS doc_chunks (
  id         TEXT PRIMARY KEY,
  doc_id     TEXT NOT NULL,
  rel_path   TEXT,
  mime       TEXT,
  hash       TEXT,
  page       INT,
  text       TEXT NOT NULL,
  embedding  VECTOR({EMBED_DIM}) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
"""
# فهرس تقريب تقارب (HNSW) – يتطلب pgvector >= 0.5.0
INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_doc_chunks_emb_hnsw ON doc_chunks USING hnsw (embedding vector_cosine_ops);"


def _as_vector_literal(vec: Sequence[float]) -> str:
    # صيغة pgvector: '[0.12, -0.3, ...]'
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"


class Service(BaseService):
    """
    خدمة embeddings:
      - upsert: إدخال (أو تحديث) مقاطع نصية مع embedding
      - search: بحث دلالي عبر التشابه الكوزايني
    """
    name = "embeddings"
    tasks = ["upsert", "search"]

    def __init__(self) -> None:
        # تحميل النموذج عند إنشاء الخدمة (مرة واحدة)
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers غير مثبت. ثبّت: pip install sentence-transformers")

        self.model = SentenceTransformer(DEFAULT_MODEL_NAME)
        # استعمل GPU لو متاح (اختياري)
        if torch is not None and torch.cuda.is_available():
            self.model = self.model.to("cuda")

        if psycopg is None:
            raise RuntimeError("psycopg غير مثبت. ثبّت: pip install 'psycopg[binary]'")

        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL غير معرّف في البيئة.")

        # تهيئة قاعدة البيانات (امتداد + جدول + فهرس)
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(EXTENSION_SQL)
                cur.execute(TABLE_SQL)
                cur.execute(INDEX_SQL)
            conn.commit()

    # -------------------------
    #          API
    # -------------------------
    def upsert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload = {
          "items": [
            { "id": "doc#1", "text": "...", "doc_id": "doc", "rel_path": "pdf/x.pdf", "page": 1, "mime": "application/pdf", "hash": "..." },
            ...
          ]
        }
        - يحسب embeddings لكل نص
        - يُدخل/يُحدث الصفوف في doc_chunks
        """
        items = (payload or {}).get("items") or []
        if not items:
            return {"ok": False, "error": "items is required (non-empty list)"}

        texts: List[str] = []
        rows: List[Dict[str, Any]] = []
        for itm in items:
            text = (itm or {}).get("text")
            if not text:
                return {"ok": False, "error": "each item must include 'text'"}
            _id = itm.get("id")
            if not _id:
                return {"ok": False, "error": "each item must include 'id'"}
            doc_id = itm.get("doc_id") or _id.split("#", 1)[0]
            rows.append({
                "id": _id,
                "doc_id": doc_id,
                "rel_path": itm.get("rel_path"),
                "mime": itm.get("mime"),
                "hash": itm.get("hash"),
                "page": itm.get("page"),
                "text": text,
            })
            texts.append(text)

        # حساب embeddings
        # e5-base يحب صيغة "query: ..." و "passage: ..." عادةً، لكن للبساطة سنأخذ النص كما هو.
        embs: List[List[float]] = self.model.encode(texts, convert_to_numpy=True).tolist()

        # upsert إلى PostgreSQL
        inserted = 0
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                for row, vec in zip(rows, embs):
                    vec_lit = _as_vector_literal(vec)
                    cur.execute(
                        """
                        INSERT INTO doc_chunks (id, doc_id, rel_path, mime, hash, page, text, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (id) DO UPDATE SET
                          doc_id = EXCLUDED.doc_id,
                          rel_path = EXCLUDED.rel_path,
                          mime = EXCLUDED.mime,
                          hash = EXCLUDED.hash,
                          page = EXCLUDED.page,
                          text = EXCLUDED.text,
                          embedding = EXCLUDED.embedding;
                        """,
                        (row["id"], row["doc_id"], row["rel_path"], row["mime"], row["hash"], row["page"], row["text"], vec_lit),
                    )
                    inserted += 1
            conn.commit()

        return {"ok": True, "upserted": inserted, "model": DEFAULT_MODEL_NAME, "dim": EMBED_DIM}

    def search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload = {
          "query": "سؤال البحث",
          "top_k": 5,
          "doc_id": "اختياري لتقييد البحث",
          "rel_path": "اختياري",
        }
        """
        query = (payload or {}).get("query")
        if not query:
            return {"ok": False, "error": "query is required"}

        top_k = int((payload or {}).get("top_k") or 5)
        top_k = max(1, min(top_k, 100))

        # حساب embedding للاستعلام
        q_vec = self.model.encode([query], convert_to_numpy=True)[0].tolist()
        q_lit = _as_vector_literal(q_vec)

        where = []
        params: List[Any] = []
        doc_id = (payload or {}).get("doc_id")
        if doc_id:
            where.append("doc_id = %s")
            params.append(doc_id)
        rel_path = (payload or {}).get("rel_path")
        if rel_path:
            where.append("rel_path = %s")
            params.append(rel_path)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        # NOTE: (embedding <=> $q) = cosine distance. نحولها لدرجة تشابه 1 - distance
        sql = f"""
            SELECT id, doc_id, rel_path, page, text,
                   1 - (embedding <=> %s::vector) AS score
            FROM doc_chunks
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT {top_k};
        """

        results: List[Dict[str, Any]] = []
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [q_lit, q_lit, *params] if params else [q_lit, q_lit])
                for row in cur.fetchall():
                    results.append(row)

        return {"ok": True, "results": results, "model": DEFAULT_MODEL_NAME}
