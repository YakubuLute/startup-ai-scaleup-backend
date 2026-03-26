import requests
import json

BASE = "http://127.0.0.1:5000/api"

print("🤖 Testing FR-10: AI Document Generator")
print("=" * 60)

# Step 1: Login to get token
print("\n[1/5] Logging in...")
res = requests.post(f"{BASE}/auth/login", json={
    "email": "morklah@agricohub.com",
    "password": "secure123"
})
if res.status_code != 200:
    print(f"❌ Login failed: {res.json()}")
    exit(1)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Token received")

# Step 2: List available templates
print("\n[2/5] Listing templates...")
res = requests.get(f"{BASE}/documents/templates", headers=headers)
print(f"Status: {res.status_code}")
print(f"Templates: {json.dumps(res.json(), indent=2)}")

# Step 3: Generate a Business Plan
print("\n[3/5] Generating Business Plan...")
res = requests.post(f"{BASE}/documents/generate", headers=headers, json={
    "startup_id": 1,  # Use the startup you created earlier
    "doc_type": "business_plan",
    "title": "AgriTech Ghana - Business Plan 2026",
    "inputs": {
        "executive_summary": "AgriTech Ghana provides AI-powered farming solutions to smallholder farmers in West Africa, increasing yields by 30% while reducing input costs.",
        "industry": "Agriculture & Agritech",
        "target_market": "Smallholder farmers in Ghana, Nigeria, and Côte d'Ivoire",
        "business_model": "B2B2C: Partner with agro-dealers to distribute our mobile app + sensor kits",
        "market_analysis": "West Africa has 50M+ smallholder farmers; <10% use digital tools. Market size: $2.3B by 2030.",
        "financial_projections": "Year 1: $50K revenue, Year 2: $300K, Year 3: $1.2M. Gross margin: 65%.",
        "next_steps": "Pilot with 500 farmers in Eastern Ghana; secure $150K seed funding."
    }
})
print(f"Status: {res.status_code}")
if res.status_code == 201:
    doc = res.json()["document"]
    print(f"✅ Document created: ID={doc['id']}, Title={doc['title']}")
    print(f"Preview: {doc['content'][:200]}...")
else:
    print(f"❌ Failed: {res.json()}")

# Step 4: List all documents
print("\n[4/5] Listing documents...")
res = requests.get(f"{BASE}/documents", headers=headers)
print(f"Status: {res.status_code}")
print(f"Documents: {json.dumps(res.json(), indent=2)}")

# Step 5: Get specific document
if res.status_code == 200 and res.json()["documents"]:
    doc_id = res.json()["documents"][0]["id"]
    print(f"\n[5/5] Getting document {doc_id}...")
    res = requests.get(f"{BASE}/documents/{doc_id}", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        content = res.json()["document"]["content"]
        print(f"Full content preview:\n{content[:500]}...")

print("\n" + "=" * 60)
print("✅ FR-10 Document Generator test complete!")