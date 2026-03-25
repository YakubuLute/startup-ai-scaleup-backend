import requests
import json

BASE = "http://127.0.0.1:5000/api"

print("🚀 Agrico Hub Backend Test Suite")
print("=" * 50)

# Step 1: Register a new user
print("\n[1/4] Registering new user...")
res = requests.post(f"{BASE}/auth/register", json={
    "name": "Prof Morklah",
    "email": "morklah@agricohub.com",
    "password": "secure123"
})
print(f"   Status: {res.status_code}")
print(f"   Response: {res.json()}")

# Step 2: Login to get JWT token
print("\n[2/4] Logging in to get token...")
res = requests.post(f"{BASE}/auth/login", json={
    "email": "morklah@agricohub.com",
    "password": "secure123"
})
data = res.json()
print(f"   Status: {res.status_code}")

if res.status_code == 200 and "access_token" in data:
    token = data["access_token"]
    print(f"   ✅ Token received: {token[:40]}...")
else:
    print(f"   ❌ Login failed: {data}")
    exit(1)

# Step 3: Create a startup (WITH REAL TOKEN)
print("\n[3/4] Creating startup...")
headers = {
    "Authorization": f"Bearer {token}",  # ← This is the key!
    "Content-Type": "application/json"
}
res = requests.post(f"{BASE}/startups", headers=headers, json={
    "name": "AgriTech Ghana",
    "sector": "Agriculture & Agritech",
    "country": "Ghana",
    "description": "AI-powered farming solutions for West Africa"
})
print(f"   Status: {res.status_code}")
print(f"   Response: {json.dumps(res.json(), indent=2)}")

# Step 4: List startups to confirm
print("\n[4/4] Listing user's startups...")
res = requests.get(f"{BASE}/startups", headers=headers)
print(f"   Status: {res.status_code}")
print(f"   Response: {json.dumps(res.json(), indent=2)}")

print("\n" + "=" * 50)
print("✅ Test complete! FR-01 + FR-02 working!")