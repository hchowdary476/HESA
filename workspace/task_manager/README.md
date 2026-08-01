# Task Manager

> build a FastAPI REST API named task_manager with SQLite database

**Generated autonomously by [JARVIS SE Platform](https://github.com/JARVIS)**

---

## Tech Stack

- **Backend:** FastAPI
- **Database:** SQLite
- **Authentication:** None

## Features

- Crud

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Backend API: http://localhost:8000
Interactive docs: http://localhost:8000/api/docs



## API Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| `GET` | `/api/items` | List all items | ✅ |
| `POST` | `/api/items` | Create new item | ✅ |
| `GET` | `/api/items/{id}` | Get item by ID | ✅ |
| `PUT` | `/api/items/{id}` | Update item | ✅ |
| `DELETE` | `/api/items/{id}` | Delete item | ✅ |

## Project Structure

```
task_manager/
├── backend/            # FastAPI API
├── frontend/           # N/A UI
├── mobile/             # N/A App
├── tests/              # Test suites
├── devops/             # Docker + CI/CD
└── docs/               # Documentation
```

## Documentation

- [API Documentation](docs/API_DOCS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Changelog](docs/CHANGELOG.md)

---

*Built with JARVIS Autonomous Software Engineering Platform | v1.0.0*
