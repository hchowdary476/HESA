"""Health check tests — task_manager"""
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
