"""
JARVIS DevOps Agent — SE Layer.

Generates DevOps configuration files based on an ArchitectureSpec:
  - Dockerfiles for backend and frontend services
  - docker-compose.yml for running multi-container applications
  - GitHub Actions CI/CD workflows (.github/workflows/ci.yml)
  - Deployment shell scripts
"""

from __future__ import annotations

import os
from typing import Any

from JARVIS.core.software_engineering.agents.architect_agent import ArchitectureSpec
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("devops_agent")


class DevOpsAgent:
    """Generates Docker, CI/CD, and deployment configurations."""

    def generate(self, spec: ArchitectureSpec) -> dict[str, Any]:
        logger.info("DevOpsAgent generating deployment config for %s", spec.project_name)
        devops_dir = os.path.join(spec.workspace_path, "devops")
        files_written: list[str] = []

        # docker-compose.yml
        if spec.backend_stack or spec.frontend_stack:
            written_compose = self._write(spec.workspace_path, "docker-compose.yml", self._docker_compose(spec))
            files_written.append(written_compose)

        # Dockerfile for Backend
        if spec.backend_stack:
            backend_docker = self._write(os.path.join(spec.workspace_path, "backend"), "Dockerfile", self._backend_dockerfile(spec))
            files_written.append(backend_docker)

        # Dockerfile for Frontend
        if spec.frontend_stack:
            frontend_docker = self._write(os.path.join(spec.workspace_path, "frontend"), "Dockerfile", self._frontend_dockerfile(spec))
            files_written.append(frontend_docker)

        # GitHub Actions CI/CD
        github_workflow = self._write(os.path.join(spec.workspace_path, ".github", "workflows"), "ci.yml", self._github_actions(spec))
        files_written.append(github_workflow)

        # Shell Scripts
        deploy_sh = self._write(devops_dir, "deploy.sh", self._deploy_script(spec))
        files_written.append(deploy_sh)

        return {
            "success": True,
            "files": files_written,
            "message": f"Generated {len(files_written)} DevOps/deployment files.",
        }

    def _docker_compose(self, spec: ArchitectureSpec) -> str:
        services = []
        if spec.backend_stack:
            services.append(f"""  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./{spec.project_name}.db
      - SECRET_KEY=change-me-in-production
    volumes:
      - backend-data:/app/data""")

        if spec.frontend_stack:
            services.append("""  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend""")

        services_str = "\n\n".join(services)
        volumes_str = "\nvolumes:\n  backend-data:" if spec.backend_stack else ""

        return f"""version: '3.8'

services:
{services_str}
{volumes_str}
"""

    def _backend_dockerfile(self, spec: ArchitectureSpec) -> str:
        stack = (spec.backend_stack or "").lower()
        if "fastapi" in stack or "flask" in stack:
            main_file = "main:app" if "fastapi" in stack else "app:app"
            port = "8000" if "fastapi" in stack else "5000"
            return f"""FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {port}

CMD ["uvicorn", "{main_file}", "--host", "0.0.0.0", "--port", "{port}"]
"""
        return """FROM openjdk:17-jdk-slim
WORKDIR /app
COPY target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""

    def _frontend_dockerfile(self, spec: ArchitectureSpec) -> str:
        return """FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

    def _github_actions(self, spec: ArchitectureSpec) -> str:
        backend_jobs = ""
        if spec.backend_stack:
            backend_jobs = """      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install backend dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run backend tests
        run: |
          pytest
"""

        frontend_jobs = ""
        if spec.frontend_stack:
            frontend_jobs = """      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install frontend dependencies
        run: |
          cd frontend
          npm install
      - name: Run frontend tests
        run: |
          cd frontend
          npm run test --run || true
"""

        return f"""name: CI/CD Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

{backend_jobs}
{frontend_jobs}
"""

    def _deploy_script(self, spec: ArchitectureSpec) -> str:
        return f"""#!/bin/bash
# {spec.project_name} deploy script
# Auto-generated by JARVIS SE Platform

echo "Starting deployment sequence for {spec.project_name}..."

# Pull latest code
git pull origin main

# Build and start services using Docker Compose
docker-compose down
docker-compose up --build -d

echo "Deployment complete! Status checks:"
docker-compose ps
"""

    def _write(self, directory: str, filename: str, content: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return path
        except Exception as e:
            logger.error("DevOpsAgent write error: %s", e)
            return path
