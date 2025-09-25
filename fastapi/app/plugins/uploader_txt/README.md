# Plugin: `uploader_txt`

## Tasks
- `upload_txt`

## Diagrams
- Mermaid: `diagram\arch_uploader_txt.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_txt/upload_txt \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_txt","task":"upload_txt","payload":{"key":"value"}}'
```
