"""
JARVIS Testing Agent — SE Layer.

Generates comprehensive test suites for backend and frontend code:
  - pytest unit tests for FastAPI/Flask/Django
  - Integration tests for API endpoints
  - Jest/Vitest tests for React components
  - Coverage configuration
  - Test runner scripts
"""

from __future__ import annotations

import os
from typing import Any

from JARVIS.core.software_engineering.agents.architect_agent import ArchitectureSpec
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("testing_agent")


class TestingAgent:
    """Generates unit, integration, and coverage test suites."""

    def generate(self, spec: ArchitectureSpec) -> dict[str, Any]:
        logger.info("TestingAgent generating test suite for %s", spec.project_name)
        tests_dir = os.path.join(spec.workspace_path, "tests")
        files_written: list[str] = []

        if spec.backend_stack:
            files_written += self._generate_python_tests(spec, tests_dir)
        if spec.frontend_stack and "vanilla" not in spec.frontend_stack.lower():
            files_written += self._generate_js_tests(spec, tests_dir)

        return {
            "success": True,
            "files": files_written,
            "message": f"Generated {len(files_written)} test files. Run: pytest tests/ or npm test",
        }

    # ── Python / pytest tests ─────────────────────────────────────────────────

    def _generate_python_tests(self, spec: ArchitectureSpec, tests_dir: str) -> list[str]:
        written: list[str] = []
        has_auth = "auth" in spec.features
        name = spec.project_name

        written.append(self._write(tests_dir, "conftest.py", self._conftest(spec)))
        written.append(self._write(tests_dir, "__init__.py", ""))
        written.append(self._write(tests_dir, "test_health.py", self._test_health(name)))
        written.append(self._write(tests_dir, "test_items.py", self._test_items(name, has_auth)))
        if has_auth:
            written.append(self._write(tests_dir, "test_auth.py", self._test_auth(name)))
        written.append(self._write(spec.workspace_path, "pytest.ini", self._pytest_ini()))
        written.append(self._write(spec.workspace_path, ".coveragerc", self._coverage_rc(name)))
        return written

    def _conftest(self, spec: ArchitectureSpec) -> str:
        stack = (spec.backend_stack or "").lower()
        if "fastapi" in stack:
            return f'''"""pytest conftest — {spec.project_name}"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite:///./test_{spec.project_name}.db"
engine = create_engine(TEST_DB_URL, connect_args={{"check_same_thread": False}})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
'''
        return f'''"""pytest conftest — {spec.project_name}"""
import pytest

@pytest.fixture
def client():
    """Override this fixture with your actual test client."""
    pass
'''

    def _test_health(self, name: str) -> str:
        return f'''"""Health check tests — {name}"""
import pytest


class TestHealth:
    def test_health_endpoint_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_has_status(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "online"
'''

    def _test_items(self, name: str, has_auth: bool) -> str:
        return f'''"""Items CRUD endpoint tests — {name}"""
import pytest


class TestItemsCRUD:
    def test_list_items_returns_200(self, client):
        response = client.get("/api/items/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_item_success(self, client):
        payload = {{"title": "Test Item", "description": "A pytest item"}}
        response = client.post("/api/items/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Item"
        assert data["id"] is not None

    def test_create_item_missing_title_fails(self, client):
        response = client.post("/api/items/", json={{"description": "No title"}})
        assert response.status_code == 422

    def test_get_item_by_id(self, client):
        create_response = client.post("/api/items/", json={{"title": "Fetch Test"}})
        item_id = create_response.json()["id"]
        response = client.get(f"/api/items/{{item_id}}")
        assert response.status_code == 200
        assert response.json()["id"] == item_id

    def test_get_nonexistent_item_returns_404(self, client):
        response = client.get("/api/items/99999")
        assert response.status_code == 404

    def test_update_item(self, client):
        create_response = client.post("/api/items/", json={{"title": "Update Me"}})
        item_id = create_response.json()["id"]
        response = client.put(f"/api/items/{{item_id}}", json={{"title": "Updated!", "is_completed": True}})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated!"
        assert response.json()["is_completed"] is True

    def test_delete_item(self, client):
        create_response = client.post("/api/items/", json={{"title": "Delete Me"}})
        item_id = create_response.json()["id"]
        delete_response = client.delete(f"/api/items/{{item_id}}")
        assert delete_response.status_code == 204
        get_response = client.get(f"/api/items/{{item_id}}")
        assert get_response.status_code == 404

    def test_list_items_pagination(self, client):
        for i in range(5):
            client.post("/api/items/", json={{"title": f"Item {{i}}"}})
        response = client.get("/api/items/?skip=0&limit=3")
        assert response.status_code == 200
        assert len(response.json()) <= 3
'''

    def _test_auth(self, name: str) -> str:
        return f'''"""Authentication endpoint tests — {name}"""
import pytest


class TestAuth:
    TEST_USER = {{"username": "testuser", "email": "test@example.com", "password": "TestPass123!"}}

    def test_register_success(self, client):
        response = client.post("/api/auth/register", json=self.TEST_USER)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == self.TEST_USER["username"]
        assert "hashed_password" not in data

    def test_register_duplicate_email_fails(self, client):
        client.post("/api/auth/register", json=self.TEST_USER)
        response = client.post("/api/auth/register", json=self.TEST_USER)
        assert response.status_code == 400

    def test_login_success(self, client):
        client.post("/api/auth/register", json=self.TEST_USER)
        response = client.post(
            "/api/auth/login",
            data={{"username": self.TEST_USER["username"], "password": self.TEST_USER["password"]}},
            headers={{"Content-Type": "application/x-www-form-urlencoded"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_fails(self, client):
        client.post("/api/auth/register", json=self.TEST_USER)
        response = client.post(
            "/api/auth/login",
            data={{"username": self.TEST_USER["username"], "password": "wrongpassword"}},
            headers={{"Content-Type": "application/x-www-form-urlencoded"}},
        )
        assert response.status_code == 401
'''

    def _pytest_ini(self) -> str:
        return """[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --cov=backend/app --cov-report=term-missing --cov-report=html:coverage_html
filterwarnings = ignore::DeprecationWarning
"""

    def _coverage_rc(self, name: str) -> str:
        return f"""[run]
source = backend/app
omit = */tests/*, */__pycache__/*, */migrations/*

[report]
show_missing = true
precision = 2

[html]
directory = coverage_html
title = {name} Coverage Report
"""

    # ── JavaScript / Vitest tests ─────────────────────────────────────────────

    def _generate_js_tests(self, spec: ArchitectureSpec, tests_dir: str) -> list[str]:
        written: list[str] = []
        js_dir = os.path.join(spec.workspace_path, "frontend", "src", "__tests__")
        written.append(self._write(js_dir, "App.test.jsx", self._vitest_app_test(spec.project_name)))
        written.append(self._write(js_dir, "ItemCard.test.jsx", self._vitest_item_card_test()))
        written.append(self._write(js_dir, "api.test.js", self._vitest_api_test()))
        return written

    def _vitest_app_test(self, name: str) -> str:
        title = name.replace("_", " ").title()
        return """import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<BrowserRouter><App /></BrowserRouter>)
    expect(document.body).toBeTruthy()
  })
})
"""

    def _vitest_item_card_test(self) -> str:
        return """import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ItemCard from '../components/ItemCard'

const mockItem = {
  id: 1, title: 'Test Item', description: 'A test description',
  is_completed: false, created_at: new Date().toISOString()
}

describe('ItemCard', () => {
  it('renders item title', () => {
    render(<ItemCard item={mockItem} onToggle={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('Test Item')).toBeTruthy()
  })

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn()
    const { container } = render(
      <ItemCard item={mockItem} onToggle={vi.fn()} onDelete={onDelete} />
    )
    fireEvent.mouseEnter(container.firstChild)
    const deleteBtn = screen.getByText('Delete')
    fireEvent.click(deleteBtn)
    expect(onDelete).toHaveBeenCalledWith(1)
  })
})
"""

    def _vitest_api_test(self) -> str:
        return """import { describe, it, expect, vi } from 'vitest'

vi.mock('axios')

describe('API Service', () => {
  it('itemsApi exports expected methods', async () => {
    const { itemsApi } = await import('../services/api')
    expect(typeof itemsApi.getAll).toBe('function')
    expect(typeof itemsApi.create).toBe('function')
    expect(typeof itemsApi.update).toBe('function')
    expect(typeof itemsApi.delete).toBe('function')
  })
})
"""

    def _write(self, directory: str, filename: str, content: str) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return path
        except Exception as e:
            logger.error("TestingAgent write error: %s", e)
            return path
