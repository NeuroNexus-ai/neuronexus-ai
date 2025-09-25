# Plugin: `text_tools`

## Tasks
- `save_text`

## Diagrams
- Mermaid: `diagram\arch_text_tools.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/text_tools/save_text \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"text_tools","task":"save_text","payload":{"key":"value"}}'
```
