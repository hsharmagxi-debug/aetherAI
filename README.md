🌌 AetherAI
> *"I built this because I believe every human being on earth deserves access to the most powerful AI tools ever created — not just those who can afford a subscription."*
> — H. Sharma, Creator of AetherAI (2026)
---
What is AetherAI?
AetherAI is the world's first unified, self-hosted AI operating system — a single platform that brings together every capability modern AI can offer:
🧠 Local LLM Chat — Run the latest open-source language models on your own hardware
💻 Code Assistant — AI pair programmer powered by DeepSeek Coder and others
📄 Document RAG — Upload any PDF and have a conversation with it
🎨 Image Generation — Stable Diffusion running entirely on your GPU
🎬 Video Generation — Coming in v2.0
🤖 Autonomous Agents — Coming in v2.0
🔑 Master API Key System — One key per user, all capabilities unified
No cloud. No subscriptions. No data leaving your machine. Ever.
---
The Vision
In 2026, access to AI was fragmented — you needed OpenAI for language, Midjourney for images, GitHub Copilot for code, and a different subscription for every capability. The barrier to entry was cost, geography, and corporate approval.
H. Sharma believed this was wrong.
AetherAI was built on the conviction that:
AI access is a human right, not a product
Privacy is non-negotiable — your data belongs to you
Open source is the only way to ensure AI serves humanity, not shareholders
One platform should be enough for any individual, researcher, or community
This project is H. Sharma's contribution to humanity — designed to outlast him, to be improved by the global community, and to remain free forever.
---
Hardware Requirements
Component	Minimum	Recommended
GPU	NVIDIA 8GB VRAM	NVIDIA RTX 3060 12GB+
RAM	16 GB	32 GB
Storage	100 GB SSD	500 GB NVMe
OS	Windows 11 + WSL2 / Ubuntu	Ubuntu 22.04+
---
Quick Start
```bash
# Clone the repository
git clone https://github.com/hsharma/aetherAI.git
cd aetherAI

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Launch all services
docker compose up -d

# Pull your first LLM model
docker exec ollama ollama pull mistral:7b-instruct-q4_K_M

# Open the chat interface
# Navigate to http://localhost:3000
```
Full installation guide: docs/INSTALL.md
---
Architecture
AetherAI runs 5 services orchestrated via Docker Compose:
```
┌─────────────────────────────────────────┐
│           User (Browser / API)          │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     AI Gateway (FastAPI — Port 8080)    │
│     Master API Key · Rate Limiting      │
│     Intent Router · JWT Auth           │
└──┬───────┬──────────┬────────┬──────────┘
   │       │          │        │
 Ollama  ChromaDB  Auto1111  Open WebUI
 :11434   :8000     :7860     :3000
   │
 RTX GPU (CUDA)
```
---
Roadmap
v1.0 — Current (2026)
[x] Unified chat interface (Open WebUI)
[x] Local LLM inference (Ollama)
[x] Code assistant (DeepSeek Coder)
[x] Document RAG (ChromaDB)
[x] Image generation (Automatic1111 / SDXL)
[x] Master API key system (FastAPI gateway)
v2.0 — In Development
[ ] Video generation (CogVideoX / Open-Sora)
[ ] Autonomous agent framework
[ ] Voice interface (Whisper + TTS)
[ ] Mobile companion app
[ ] Multi-user workspace with role-based access
v3.0 — Community Vision
[ ] Federated AetherAI network (multiple nodes sharing compute)
[ ] Plugin marketplace
[ ] Fine-tuning interface for custom models
[ ] AetherAI Foundation governance
---
License
AetherAI is licensed under the GNU Affero General Public License v3 (AGPL v3).
This means:
✅ Free to use, modify, and distribute
✅ Free to run as a self-hosted service
⚠️ Any modifications must be open sourced under the same license
⚠️ If you run it as a network service, users must have access to the source
❌ Cannot be taken private by any company
For commercial use in proprietary products, contact: aetherAI.commercial@proton.me
See LICENSE and COMMERCIAL_LICENSE.md for full details.
---
Contributing
AetherAI belongs to its community. See CONTRIBUTING.md to join.
Every pull request, bug report, and idea is a contribution to a platform that will outlast all of us.
---
Ethics
AetherAI has a moral framework. See ETHICS.md for what this platform stands for and what it must never be used for.
---
In Memory
This project was created by H. Sharma with the hope that long after he is gone, AetherAI will continue to serve humanity — freely, openly, and without discrimination. If you are reading this after his passing, please carry this mission forward with the same intention with which it was created.
The code is the legacy. The community is the immortality.
---
AetherAI — For humanity. Forever.
⭐ Star this repository if you believe AI should be free for everyone.
