# 🤝 Contributing to HESA (JARVIS)

Thank you for your interest in contributing to HESA! We welcome contributions from developers of all skill levels.

---

## 📜 Code of Conduct
This project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold these standards.

---

## 🛠️ Getting Started

### 1. Fork & Clone
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/HESA.git
   cd HESA
   ```

### 2. Set Up Development Environment
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 🔄 Development Workflow

### 1. Create a Branch
```bash
git checkout -b feature/my-new-feature
```

### 2. Code Quality & Linting
We use **Ruff** for linting and code formatting:
```bash
python -m ruff check .
```

### 3. Running Unit & Integration Tests
Before submitting a PR, ensure all tests pass:
```bash
python -m unittest discover -s tests -q
```

### 4. Commit Messages
Use standard conventional commit prefixes:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation updates
- `test:` Adding or updating tests
- `refactor:` Code improvements without functionality changes

---

## 📥 Submitting Pull Requests

1. Push your branch to GitHub:
   ```bash
   git push origin feature/my-new-feature
   ```
2. Open a Pull Request against `main`.
3. Complete the PR template checklist.
4. Ensure all automated CI checks pass.
