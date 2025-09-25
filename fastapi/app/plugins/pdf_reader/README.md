# Plugin: `pdf_reader`

## Tasks
- `extract_text`

## Diagrams
- Mermaid: `diagram\arch_pdf_reader.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/pdf_reader/extract_text \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"pdf_reader","task":"extract_text","payload":{"key":"value"}}'
```
