# Plugin: `uploader_pdf`

## Tasks
- `upload_pdf`

## Diagrams
- Mermaid: `diagram\arch_uploader_pdf.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_pdf/upload_pdf \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_pdf","task":"upload_pdf","payload":{"key":"value"}}'
```
