# 🚀 NeuroNexus-ai Dashboard  

<!-- Tech / Stack -->
[![PSF Member - TamerOnLine](https://img.shields.io/badge/PSF%20Member-TamerOnLine-success?logo=python&logoColor=white)](https://www.python.org/users/TamerOnLine/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI 0.116.x](https://img.shields.io/badge/FastAPI-0.116.x-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit 1.x](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![PyTorch 2.6.x](https://img.shields.io/badge/PyTorch-2.6.x-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![CUDA Ready](https://img.shields.io/badge/CUDA-Ready-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-zone)

<!-- CI Status (GitHub Actions) -->
[![CI • Ubuntu](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-ubuntu.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-ubuntu.yml)
[![CI • Windows](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-windows.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-windows.yml)
[![CI • macOS](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-macos.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-macos.yml)
[![CI • Windows Self-Hosted + GPU](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-gpu.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-gpu.yml)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)



---

## 📖 Overview
**NeuroNexus-ai Dashboard** is a **multi-server orchestrator** for managing and running **multiple FastAPI services** through a unified **Streamlit interface**.  

It provides:
- 🔄 Orchestration with health checks and graceful startup/shutdown.
- ⚙️ Server management (add, delete, test connectivity, and store tokens).
- 📢 Broadcast requests to multiple servers at once.
- 🔌 Extensible **Plugins & Workflows** system.
- 🎨 Customizable **UI Theme** with CSS.
- 🛡️ Demo JWT authentication.

---

## 🎥 Demo

<p align="center">
  <img src="docs/video/NeuroNexus-ai.gif" alt="Dashboard Demo" width="800">
</p>


---

## ✨ Features
- Orchestrate **FastAPI + Streamlit** with one command.
- Manage multiple services easily via sidebar.
- Unified **Inference API** for plugin tasks.
- Plugins & workflows for modular extensibility.
- Professional dashboard interface with custom CSS.

---

## 🧱 Architecture
```text
repo-server/
├─ fastapi/      # FastAPI server (APIs, Plugins, Workflows, Docs, Tests)
├─ streamlit/    # Streamlit dashboard + .streamlit/servers.json
├─ run_all.py    # Orchestrator: launches + health checks + graceful shutdown
└─ servers.json  # Service definitions (paths, python_exe, health URLs…)
```

---

## ⚡ Quick Setup

### 1. Clone
```bash
git clone https://github.com/TamerOnLine/repo-server
cd repo-server
```

### 2. Virtualenvs (recommended)
```bash
cd fastapi
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd ../streamlit
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Run with Orchestrator

```bash
py -m run_all        # start API + Dashboard
py -m run_all api    # start only API
```

Example `servers.json`:
```json
{
  "launch_order": ["api", "streamlit"],
  "services": {
    "api": {
      "cwd": "fastapi",
      "python_exe": "fastapi/.venv/Scripts/python.exe",
      "cmd": ["-m", "uvicorn", "main:app", "--app-dir", "app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
      "health": "http://127.0.0.1:8000/health"
    },
    "streamlit": {
      "cwd": "streamlit",
      "python_exe": "streamlit/.venv/Scripts/python.exe",
      "cmd": ["-m", "streamlit", "run", "app.py", "--server.address", "127.0.0.1", "--server.port", "8501"],
      "health": "http://127.0.0.1:8501/_stcore/health",
      "exports": { "url": "http://127.0.0.1:8501" }
    }
  }
}
```

---

## 🖥️ Streamlit Dashboard
- Sidebar for managing servers.  
- Tabs:
  - 🔑 Auth (`/auth/login`, `/auth/me`)
  - 📂 Uploads (`/uploads`)
  - 🔌 Plugins (`/plugins/{name}/{task}`)
  - 🧠 Inference (`/inference`)
  - 🔗 Workflows (`/workflows/run`)
  - ❤️ Health & Info (`/`, `/docs`, `/redoc`)
  - 📢 Broadcast (send requests to all servers)

---

## ⚙️ FastAPI Server
- Core endpoints: `/health`, `/env`, `/plugins`, `/workflows`.
- Routers: Auth, Uploads, Plugins, Inference, Services, Workflows.
- Includes CORS, logging, and unified responses.

---

## 🔌 Plugins & Workflows
- Plugins under: `app/plugins/<name>/`
- Workflows under: `app/workflows/<name>/`

API:
```http
POST /plugins/{name}/{task}
POST /inference
POST /workflows/run
```

---

## 🎨 Customization
UI customization via:  
`streamlit/.streamlit/neuroserve.css`

---

## 🖼️ Screenshots
<p align="center">
  <img src="docs/images/NeuroNexus-ai.gif" alt="Dashboard Plugins" width="800">
</p>

---

## 🏭 Deployment Notes
- Run Uvicorn behind a reverse proxy (e.g., Nginx).  
- Use environment variables `APP_*` instead of hardcoded values.  
- Docker setup planned in the roadmap.  

---

## 🤝 Contributing
- Open **Issues** for ideas or bugs.  
- Submit **Pull Requests** for improvements.  
- Follow style guidelines (Ruff + pre-commit).  
- See [Code Style Guide](fastapi/docs/CODE_STYLE_GUIDE.md).  

---

## 🗺️ Roadmap
- [ ] Docker one-click deployment.  
- [ ] CLI generator for Plugins & Workflows.  
- [ ] Extended Auth system (JWT + user management).  
- [ ] Expanded integration tests (CI/CD).  
- [ ] Example Plugins: translation, summarization, image classification.  

---

## 📜 License
Licensed under the **MIT License** → [LICENSE](./LICENSE).  
⚠️ Some AI/ML models have separate licenses: [Model Licenses](fastapi/docs/LICENSES.md).
