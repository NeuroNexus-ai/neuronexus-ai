# Plugin: `embeddings`

## Tasks
- `upsert`
- `search`

## Diagrams
- Mermaid: `diagram\arch_embeddings.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/embeddings/upsert \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"embeddings","task":"upsert","payload":{"key":"value"}}'
```
