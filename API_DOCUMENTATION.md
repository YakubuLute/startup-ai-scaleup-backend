# 🚀 Startup AI Scaleup - Backend API Documentation

**Version:** 1.0  
**Last Updated:** April 9, 2026  
**Environment:** `dev` branch  
**Base URL:** `https://startup-ai-scaleup-backend.onrender.com/api`  
**Auth:** `Authorization: Bearer <jwt_token>`  

---

## 🔐 Authentication

All protected endpoints require a valid JWT token in the header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Auth Endpoints
POST /auth/register
Create a new user.
Request:

{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "securePassword123",
  "role": "Founder"
}

{
  "message": "User created successfully",
  "user": {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane@example.com",
    "role": "Founder"
  }
}

POST /auth/login
Authenticate and receive JWT + user data.
Request:

{
  "email": "jane@example.com",
  "password": "securePassword123"
}

{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane@example.com",
    "role": "Founder",
    "created_at": "2026-04-09T14:30:00Z"
  }
}


GET /auth/me (Protected)
Get current user profile.
Response (200):

{
  "id": 1,
  "name": "Jane Doe",
  "email": "jane@example.com",
  "role": "Founder",
  "created_at": "2026-04-09T14:30:00Z"
}


Startup Endpoints
GET /startups
List startups. Supports query filters: ?sector=, ?stage=, ?location=
Response (200):
{
  "startups": [
    {
      "id": 1,
      "name": "TechVenture",
      "sector": "ICT",
      "stage": "Early stage",
      "location": "Accra",
      "description": "AI-powered solutions",
      "founder_id": 1,
      "created_at": "2026-04-01T12:00:00Z"
    }
  ],
  "total": 1
}

POST /startups (Protected)
Create a startup (auto-linked to authenticated user).
Request:

{
  "name": "My Startup",
  "sector": "Fintech",
  "stage": "Ideation",
  "location": "Accra",
  "description": "Solving X for Y",
  "website": "https://example.com",
  "contact_email": "founder@example.com",
  "contact_phone": "0549875117"
}

{
  "message": "Startup created successfully",
  "startup": {
    "id": 2,
    "name": "My Startup",
    "founder_id": 1,
    "sector": "Fintech",
    "stage": "Ideation",
    "location": "Accra",
    "description": "Solving X for Y",
    "created_at": "2026-04-09T15:00:00Z"
  }
}

GET /startups/:id
Get single startup details.
Response (200):
{
  "id": 1,
  "name": "TechVenture",
  "founder_id": 1,
  "sector": "ICT",
  "stage": "Early stage",
  "location": "Accra",
  "description": "AI-powered solutions",
  "products": ["Product A", "Product B"],
  "team_size": 5,
  "revenue_range": "$10k-$50k",
  "created_at": "2026-04-01T12:00:00Z",
  "updated_at": "2026-04-05T10:00:00Z"
}

PUT /startups/:id (Protected, Founder only)
Update startup. Supports partial updates.
Request:
{
  "stage": "Growth stage",
  "description": "Updated description"
}
{
  "message": "Startup updated successfully",
  "startup": { /* updated object */ }
}

DELETE /startups/:id (Protected, Founder only)
Delete startup.
Response (200):
{ "message": "Startup deleted successfully" }
Other Modules
All follow REST conventions (GET, POST, PUT, DELETE) and require authentication unless noted.

Module
Base Path
Description
📄 Documents
/api/documents
Upload & manage files
💰 Valuations
/api/valuations
Valuation requests & reports
🔍 Diagnostics
/api/diagnostics
Business health checks
✅ Verification
/api/verification
KYC & compliance
💳 Billing
/api/billing
Stripe subscriptions
👔 Investors
/api/investors
Investor matching
🔔 Notifications
/api/notifications
User alerts
🎯 Programs
/api/programs
Incubation programs
📊 Analytics
/api/analytics
Dashboard metrics



 Error Handling
All errors return consistent JSON:
{
  "msg": "Human-readable error message"
}

Common Status Codes:
Code
Meaning
200 / 201
Success
400
Validation error
401
Missing/invalid token
403
Insufficient permissions
404
Not found
500
Server error

CORS Configuration

 Allowed Origins: http://localhost:3000, http://127.0.0.1:3000
✅ Methods: GET, POST, PUT, DELETE, OPTIONS
✅ Headers: Content-Type, Authorization
✅ Credentials: true
Preflight OPTIONS requests return 204 No Content with proper headers.



Quick Integration Examples
JavaScript (Fetch)
const API = 'https://startup-ai-scaleup-backend.onrender.com/api';

async function login(email, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await res.json();
  if (res.ok) {
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
  }
  return data;
}

async function fetchStartups() {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API}/startups`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return res.json();
}

cURL

# Login
curl -X POST https://startup-ai-scaleup-backend.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Get Startups
curl -X GET https://startup-ai-scaleup-backend.onrender.com/api/startups \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"


  Notes
Signup uses /auth/register (not /signup)
All timestamps are ISO 8601 UTC
Rate limiting: Not yet enforced (coming soon)
Pagination: Not yet implemented (coming soon)