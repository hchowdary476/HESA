"""Items CRUD endpoint tests — task_manager"""
import pytest


class TestItemsCRUD:
    def test_list_items_returns_200(self, client):
        response = client.get("/api/items/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_item_success(self, client):
        payload = {"title": "Test Item", "description": "A pytest item"}
        response = client.post("/api/items/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Item"
        assert data["id"] is not None

    def test_create_item_missing_title_fails(self, client):
        response = client.post("/api/items/", json={"description": "No title"})
        assert response.status_code == 422

    def test_get_item_by_id(self, client):
        create_response = client.post("/api/items/", json={"title": "Fetch Test"})
        item_id = create_response.json()["id"]
        response = client.get(f"/api/items/{item_id}")
        assert response.status_code == 200
        assert response.json()["id"] == item_id

    def test_get_nonexistent_item_returns_404(self, client):
        response = client.get("/api/items/99999")
        assert response.status_code == 404

    def test_update_item(self, client):
        create_response = client.post("/api/items/", json={"title": "Update Me"})
        item_id = create_response.json()["id"]
        response = client.put(f"/api/items/{item_id}", json={"title": "Updated!", "is_completed": True})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated!"
        assert response.json()["is_completed"] is True

    def test_delete_item(self, client):
        create_response = client.post("/api/items/", json={"title": "Delete Me"})
        item_id = create_response.json()["id"]
        delete_response = client.delete(f"/api/items/{item_id}")
        assert delete_response.status_code == 204
        get_response = client.get(f"/api/items/{item_id}")
        assert get_response.status_code == 404

    def test_list_items_pagination(self, client):
        for i in range(5):
            client.post("/api/items/", json={"title": f"Item {i}"})
        response = client.get("/api/items/?skip=0&limit=3")
        assert response.status_code == 200
        assert len(response.json()) <= 3
