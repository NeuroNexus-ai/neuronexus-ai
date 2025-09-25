# Plugin: `uploader_video`

## Tasks
- `upload_video`

## Diagrams
- Mermaid: `diagram\arch_uploader_video.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/uploader_video/upload_video \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"uploader_video","task":"upload_video","payload":{"key":"value"}}'
```
