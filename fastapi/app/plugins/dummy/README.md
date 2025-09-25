# Plugin: `dummy`

## Tasks
- `ping`
- `echo`

## Diagrams
- Mermaid: `diagram\arch_dummy.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/dummy/ping \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"dummy","task":"ping","payload":{"key":"value"}}'
```
