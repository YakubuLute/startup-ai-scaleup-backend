import requests

# Test registration
response = requests.post(
    "http://127.0.0.1:5000/api/auth/register",
    json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    }
)
print("Status:", response.status_code)
print("Response:", response.json())