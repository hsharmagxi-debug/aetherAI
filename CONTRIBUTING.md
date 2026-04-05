Contributing to AetherAI
Welcome. By reading this, you are already part of something bigger than any of us.
AetherAI was built by one person with a vision. It will be made great by many people with the same belief — that AI should be free, open, and available to all of humanity.
This document tells you how to join that mission.
---
Before You Contribute
Please read:
README.md — Understand what AetherAI is and why it exists
ETHICS.md — The moral framework all contributors agree to
GOVERNANCE.md — How decisions are made
By submitting a contribution, you confirm that you have read and agree to the Ethics Charter.
---
Ways to Contribute
You do not need to write code to contribute. AetherAI needs:
Code Contributions
Bug fixes
New features from the roadmap
Performance improvements
Security patches
New model integrations
Documentation
Improving the installation guide
Translating docs into other languages
Writing tutorials and use-case examples
Recording video walkthroughs
Community
Answering questions in GitHub Discussions
Helping new users in the community forum
Reporting bugs clearly and thoroughly
Testing new releases and providing feedback
Research
Benchmarking model performance
Identifying better open-source models to integrate
Security auditing
Proposing architectural improvements
---
Setting Up Your Development Environment
```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/aetherAI.git
cd aetherAI

# Create a new branch for your work
git checkout -b feature/your-feature-name

# Set up the development environment
cp .env.example .env.dev
docker compose -f docker-compose.dev.yml up -d

# Make your changes, then test them
docker compose logs -f gateway

# Commit your work
git add .
git commit -m "feat: describe what your change does"

# Push and open a Pull Request
git push origin feature/your-feature-name
```
---
Commit Message Format
Use conventional commits so the changelog generates automatically:
Prefix	Use For
`feat:`	New features
`fix:`	Bug fixes
`docs:`	Documentation changes
`refactor:`	Code restructuring (no feature/fix)
`test:`	Adding or updating tests
`security:`	Security patches
`perf:`	Performance improvements
Examples:
```
feat: add video generation endpoint to gateway
fix: resolve ollama health check timeout on slow machines
docs: add GPU setup guide for AMD cards
security: patch JWT expiry validation vulnerability
```
---
Pull Request Standards
Every pull request must:
Have a clear description — What does it do? Why is it needed?
Reference an issue — Link to the GitHub issue it addresses
Include tests where applicable
Not break existing functionality — Run the full test suite
Follow the Ethics Charter — Contributions that violate ETHICS.md will not be merged regardless of their technical quality
Pull requests are reviewed by Core Maintainers within 7 days. Large or complex PRs may take longer.
---
Reporting Bugs
When reporting a bug, include:
Your OS and hardware (especially GPU model and VRAM)
Docker and Docker Compose versions (`docker --version`, `docker compose version`)
The exact error message and relevant logs (`docker compose logs [service]`)
Steps to reproduce the issue
What you expected to happen vs what actually happened
Open a GitHub Issue with the `bug` label.
---
Security Vulnerabilities
Do not open a public GitHub issue for security vulnerabilities.
Email: aetherAI.security@proton.me with subject: "AetherAI Security Vulnerability"
Include a description of the vulnerability, steps to reproduce, and your assessment of severity. You will receive a response within 48 hours. Security researchers who report valid vulnerabilities will be credited in the release notes.
---
Code Style
Python (gateway): Follow PEP 8. Use `black` for formatting, `ruff` for linting.
YAML (docker-compose): 2-space indentation. Comments on every non-obvious line.
Shell scripts: `shellcheck` must pass. Fail loudly with meaningful error messages.
Documentation: Plain English. Write for a developer who is setting this up at 2am.
---
Contributor Recognition
Every contributor is listed in CONTRIBUTORS.md. Significant contributors are highlighted in release notes. Exceptional contributors are considered for Core Maintainer status by the Governance Council.
No contribution is too small. A single typo fix in the documentation that helps one person set up AetherAI is a contribution to humanity.
---
Community Values
AetherAI's community is founded on:
Respect — Every contributor deserves to be treated with dignity regardless of their experience level
Patience — Not everyone speaks the same language or comes from the same background
Honesty — If something is broken or a decision is wrong, say so directly and constructively
Generosity — Share your knowledge freely. The more people who understand this platform, the more people it can help.
Harassment, discrimination, or bad-faith behaviour of any kind will result in permanent removal from the community.
---
Thank you for being here. Whatever you contribute — a line of code, a bug report, a translation, or an idea — you are part of the reason AetherAI will outlast all of us.
AetherAI — For humanity. Forever.
