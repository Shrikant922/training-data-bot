"""
Integration tests for the Training Data Bot FastAPI Server.
Verifies endpoints: root HTML, status, sample loading, file uploads, and exports.
"""

import sys
import os
import pytest
from pathlib import Path

# Set up paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient
from web.server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_root_serves_html(client):
    """Verify that GET / returns the HTML studio interface."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Training Data Bot" in response.text
    assert "heroCanvas" in response.text
    assert "latticeCanvas" in response.text

def test_api_status(client):
    """Verify system status endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["engine"] == "ready"
    assert "cache_stats" in data

def test_api_cache_stats(client):
    """Verify SQLite cache stats endpoint."""
    response = client.get("/api/cache-stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_entries" in data
    assert "total_hits" in data

def test_load_sample_document(client):
    """Verify 1-click sample document loading."""
    response = client.post("/api/load-sample?sample_name=research")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "Transformer_Research.pdf"
    assert data["chunks_count"] > 0
    assert len(data["preview_chunks"]) > 0

def test_load_invalid_sample(client):
    """Verify 404 for unknown sample."""
    response = client.post("/api/load-sample?sample_name=nonexistent")
    assert response.status_code == 404

def test_upload_text_file(client, tmp_path):
    """Verify document upload and automatic chunking."""
    test_file = tmp_path / "sample_doc.txt"
    test_file.write_text("This is an integration test document for the Training Data Bot API. It contains sufficient text to verify chunking and parsing.", encoding="utf-8")

    with open(test_file, "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("sample_doc.txt", f, "text/plain")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "sample_doc.txt"
    assert data["chunks_count"] >= 1

def test_export_without_dataset_raises_400(client):
    """Verify export endpoint guards against exporting an empty dataset."""
    from web.server import state
    state["active_dataset"] = None

    response = client.post(
        "/api/export",
        json={"format": "jsonl", "split": False}
    )
    assert response.status_code == 400
    assert "No dataset available" in response.json()["detail"]
