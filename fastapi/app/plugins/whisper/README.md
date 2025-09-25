# Plugin: `whisper`

## Tasks
_No tasks discovered._

## Diagrams
- Mermaid: `diagram\arch_whisper.mmd`

## Example API Call
```bash
curl -X POST http://localhost:8000/plugins/whisper/<task> \
     -H 'Content-Type: application/json' \
     -d '{"key":"value"}'
```

## Example Unified Inference
```bash
curl -X POST http://localhost:8000/inference \
     -H 'Content-Type: application/json' \
     -d '{"plugin":"whisper","task":"<task>","payload":{"key":"value"}}'
```
