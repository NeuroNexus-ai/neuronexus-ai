# Plugin: `uploader_image`

## Tasks
- `upload_image`

## Diagrams
- Mermaid: `diagram\arch_uploader_image.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_image/upload_image \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_image","task":"upload_image","payload":{"key":"value"}}'
```
