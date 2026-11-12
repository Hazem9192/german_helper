from fastapi.testclient import TestClient
from Main import app #FastAPI app from main.py


#Test client for FastAPI
client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert "German Bureaucracy Helper" in response.text

def test_get_guides():
    response = client.get("/guides")  # Beispiel für eine API-Route
    assert response.status_code == 200
    assert isinstance(response.json(), list)
