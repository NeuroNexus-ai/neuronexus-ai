# 🚀 NeuroNexus-ai Dashboard  

<!-- TOC -->
## 📑 Table of Contents
- [Tech / Stack](#-tech--stack)
- [CI Status](#-ci-status)
- [Releases](#-releases)
- [Overview](#-overview)
- [Demo](#-demo)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Setup](#-quick-setup)
- [Run with Orchestrator](#-run-with-orchestrator)
- [Streamlit Dashboard](#-streamlit-dashboard)
- [FastAPI Server](#-fastapi-server)
- [Plugins & Workflows](#-plugins--workflows)
- [Customization](#-customization)
- [Screenshots](#-screenshots)
- [Deployment Notes](#-deployment-notes)
- [Contributing](#-contributing)
- [Roadmap](#-roadmap)
- [License](#-license)
- [Community & Membership](#-community--membership)

---

<!-- Tech / Stack -->
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI 0.116.x](https://img.shields.io/badge/FastAPI-0.116.x-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit 1.x](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![PyTorch 2.6.x](https://img.shields.io/badge/PyTorch-2.6.x-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![CUDA Ready](https://img.shields.io/badge/CUDA-Ready-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-zone)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-33CCFF.svg)](https://docs.astral.sh/ruff/)

<!-- CI Status (GitHub Actions) -->
[![CI • API](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-api.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-api.yml)
[![CI • Ubuntu](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-ubuntu.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-ubuntu.yml)
[![CI • Windows](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-windows.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-windows.yml)
[![CI • macOS](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-macos.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-macos.yml)
[![CI • Streamlit](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-streamlit.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-streamlit.yml)
[![CI • Windows Self-Hosted + GPU](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-gpu.yml/badge.svg?branch=main)](https://github.com/NeuroNexus-ai/neuronexus-ai/actions/workflows/ci-gpu.yml)

---

## 📦 Releases
[![GitHub release](https://img.shields.io/github/v/release/NeuroNexus-ai/neuronexus-ai?color=blue)](https://github.com/NeuroNexus-ai/neuronexus-ai/releases)
[![GitHub stars](https://img.shields.io/github/stars/NeuroNexus-ai/neuronexus-ai?style=social)](https://github.com/NeuroNexus-ai/neuronexus-ai/stargazers)

➡️ [View all releases](https://github.com/NeuroNexus-ai/neuronexus-ai/releases)

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
| Feature | Description | Status |
|---------|-------------|--------|
| Orchestration | Run and monitor FastAPI + Streamlit with one command | ✅ Ready |
| Multi-service management | Add, delete, test connectivity, and store tokens | ✅ Ready |
| Unified Inference API | Single entrypoint for plugin tasks | ✅ Ready |
| Plugins & Workflows | Modular extensibility for AI tasks | ✅ Ready |
| Custom UI Theme | Dashboard customization via CSS | ✅ Ready |
| JWT Authentication | Demo authentication & security | ⚙️ In Progress |
| Docker Support | One-click deployment | ⏳ Planned |

---

## 🧱 Architecture
```text
neuronexus-ai/
├── fastapi/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # Routers (auth, inference, uploads, plugins, services, workflows)
│   │   ├── plugins/  # Plugins (dummy, pdf_reader, whisper, ...)
│   │   ├── services/ # Services (parallel to plugins)
│   │   ├── workflows/# Orchestrator + registry
│   │   └── core/     # Config, errors, logging, path utils
│   └── tools/        # Diagram generators, plugin wrapper scripts
├── streamlit/        # Streamlit Dashboard (UI)
│   ├── core/         # API calls, state, storage
│   └── ui/           # Sidebar + tabs (inference, uploads, workflows, etc.)
└── uploads/          # User uploads (pdf, audio, video, images, txt)

```

---

# ⚡ Quick Setup

## 🪟 Windows (PowerShell)

```powershell
# 1) Clone
git clone https://github.com/NeuroNexus-ai/neuronexus-ai.git
cd neuronexus-ai

# 2) Bootstrap via reposmith
py tools/rs.py bootstrap

# 3) Run
py -m run_all
```

---

## 🐧 Linux / macOS (bash)

```bash
# 1) Clone
git clone https://github.com/NeuroNexus-ai/neuronexus-ai.git
cd neuronexus-ai

# 2) Bootstrap via reposmith
python3 tools/rs.py bootstrap

# 3) Run
python3 -m run_all
```

---

### 💡 Notes

  - By default, reposmith bootstrap will create separate virtual environments for API + UI.

  - If you want a single shared environment, you can still set it up manually.

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
- [ ] 📦 Docker one-click deployment.  
- [ ] ⚙️ CLI generator for Plugins & Workflows.  
- [ ] 🔐 Extended Auth system (JWT + user management).  
- [ ] ✅ Expanded integration tests (CI/CD).  
- [ ] 🧩 Example Plugins: translation, summarization, image classification.  

---

## 📜 License  
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)  

Licensed under the **MIT License** → [LICENSE](./LICENSE).  
For more details, see the official [OSI page](https://opensource.org/licenses/MIT).  

⚠️ Some AI/ML models have separate licenses: [Model Licenses](fastapi/docs/LICENSES.md).

---

## 🌍 Community & Membership
[![PSF Member](https://img.shields.io/badge/PSF%20Member-TamerOnLine-success?logo=python&logoColor=white)](https://www.python.org/users/TamerOnLine/)
[![GitHub](https://img.shields.io/badge/GitHub-TamerOnLine-181717?logo=github&logoColor=white)](https://github.com/TamerOnLine)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Profile-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/tameronline/)
[![PyPI - TamerOnLine](https://img.shields.io/badge/PyPI-TamerOnLine-blue?logo=pypi&logoColor=white)](https://pypi.org/user/TamerOnLine/)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/@mystrotamer)

---
