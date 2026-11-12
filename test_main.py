from fastapi.testclient import TestClient
from main import app #FastAPI app from main.py


#Test client for FastAPI
client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "German Bureaucracy Helper" in response.json()["title"]
