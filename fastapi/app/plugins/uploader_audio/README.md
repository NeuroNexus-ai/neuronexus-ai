# Plugin: `uploader_audio`

## Tasks
- `upload_audio`

## Diagrams
- Mermaid: `diagram\arch_uploader_audio.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_audio/upload_audio \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_audio","task":"upload_audio","payload":{"key":"value"}}'
```
