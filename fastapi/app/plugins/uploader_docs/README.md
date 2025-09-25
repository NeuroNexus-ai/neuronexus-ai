# Plugin: `uploader_docs`

## Tasks
- `upload_doc`

## Diagrams
- Mermaid: `diagram\arch_uploader_docs.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_docs/upload_doc \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_docs","task":"upload_doc","payload":{"key":"value"}}'
```
