# Plugin: `payload_maker`

## Tasks
- `make_b64_payload`

## Diagrams
- Mermaid: `diagram\arch_payload_maker.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/payload_maker/make_b64_payload \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"payload_maker","task":"make_b64_payload","payload":{"key":"value"}}'
```
