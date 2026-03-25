import requests

BASE = "http://127.0.0.1:5000/api/auth"

print("=== Testing Registration ===")
res = requests.post(f"{BASE}/register", json={
    "name": "Python Test",
    "email": "python@test.com",
    "password": "test123"
})
print(f"Status: {res.status_code}")
print(f"Response: {res.json()}\n")

print("=== Testing Login ===")
res = requests.post(f"{BASE}/login", json={
    "email": "python@test.com",
    "password": "test123"
})
print(f"Status: {res.status_code}")
print(f"Response: {res.json()}")