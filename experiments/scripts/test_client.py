import sys
sys.path.append(r"D:\VINA")

from app import app
from fastapi.testclient import TestClient

client = TestClient(app)
with open(r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg", "rb") as f:
    response = client.post("/v1/eval/predict", files={"image": f})
    print(response.status_code)
    print(response.text)
