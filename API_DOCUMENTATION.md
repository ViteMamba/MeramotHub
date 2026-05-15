# How APIs Connect with Frontend via JSON

This document explains how the backend APIs work and how they communicate with the frontend using JSON.

---

## 1. Where APIs Are Created

All API endpoints are defined in the `app/routers/` folder:

| File | Endpoints | Purpose |
|------|-----------|---------|
| `app/routers/auth.py` | `/auth/register`, `/auth/login`, `/auth/me` | User authentication |
| `app/routers/bookings.py` | `/bookings/...` | Booking management |
| `app/routers/services.py` | `/services/...` | Service catalogue |
| `app/routers/providers.py` | `/providers/...` | Service provider profiles |
| `app/routers/payments.py` | `/payments/...` | Payment processing |
| `app/routers/reviews.py` | `/reviews/...` | Ratings & reviews |
| `app/routers/complaints.py` | `/complaints/...` | Complaint handling |
| `app/routers/admin.py` | `/admin/...` | Admin dashboard |
| `app/routers/chatbot.py` | `/chat/...` | AI chatbot |
| `app/routers/priyo.py` | `/priyo/...` | Subscription/instant booking |

---

## 2. How JSON Communication Works

### Example: Login API

**1. Backend defines endpoint (app/routers/auth.py):**
```python
@router.post("/login", response_model=TokenSchema)
def login(credentials: OAuth2PasswordRequestForm = Depends()):
    # Check user exists
    user = db.query(User).filter(User.phone_number == credentials.username).first()
    
    # Verify password
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Return JSON response
    return TokenSchema(access_token=access_token, token_type="bearer")
```

**2. Frontend sends JSON request:**
```javascript
// JavaScript/Fetch request
fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/x-www-form-urlencoded' 
    },
    body: 'username=01500000000&password=pass123'
})
.then(response => response.json())
.then(data => {
    console.log(data.access_token); // Store this token
});
```

**3. Backend returns JSON response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

---

## 3. Complete API Flow Diagram

```
┌─────────────┐     JSON Request      ┌─────────────┐
│   Frontend  │ ───────────────────►  │   Backend   │
│  (React/    │   POST /auth/login    │  (FastAPI)  │
│  Vue/Etc)   │   {phone, password}    │             │
└─────────────┘                       └─────────────┘
       │                                      │
       │      JSON Response                   │
       │  ◄───────────────────                │
       │   {access_token, token_type}        │
       │                                      │
       ▼                                      ▼
┌─────────────┐                       ┌─────────────┐
│  Store      │                       │  Database   │
│  Token in   │                       │  (Postgres) │
│  LocalStorage│                      │             │
└─────────────┘                       └─────────────┘
```

---

## 4. All API Endpoints Summary

### Authentication APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | No | Register new user |
| POST | `/auth/login` | No | Login, get JWT token |
| GET | `/auth/me` | Token | Get current user profile |

### Service Catalogue APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/services/categories` | No | List all service categories |
| GET | `/services/items` | No | List all service items |
| GET | `/services/items/{id}` | No | Get single service detail |

### Service Provider APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/providers/` | No | List verified providers |
| GET | `/providers/nearby` | No | Search nearby providers |
| GET | `/providers/pending` | AM/Admin | List pending verifications |
| POST | `/providers/profile` | Provider | Create profile |
| GET | `/providers/profile/me` | Provider | Get own profile |
| PATCH | `/providers/profile/location` | Provider | Update location |
| PATCH | `/providers/{id}/verify` | AM/Admin | Verify/reject provider |

### Booking APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/bookings/` | Customer | Create new booking |
| GET | `/bookings/my` | Customer | Get my bookings |
| GET | `/bookings/assigned` | Provider | Get assigned jobs |
| PATCH | `/bookings/{id}/accept` | Provider | Accept booking |
| PATCH | `/bookings/{id}/start` | Provider | Start job |
| PATCH | `/bookings/{id}/complete` | Provider | Complete job |
| PATCH | `/bookings/{id}/cancel` | Token | Cancel booking |

### Payment APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/payments/my` | Customer | My payment history |
| GET | `/payments/earnings` | Provider | My earnings |
| GET | `/payments/dashboard` | Provider | Payment stats |

### Review APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/reviews/` | Customer | Add review for completed booking |
| GET | `/reviews/my` | Customer | My reviews |
| GET | `/reviews/provider/{id}` | No | Provider's reviews |

### Complaint APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/complaints/` | Token | File complaint |
| GET | `/complaints/my` | Customer | My complaints |
| GET | `/complaints/` | AM/Admin | List all complaints |
| PATCH | `/complaints/{id}/assign` | AM | Assign complaint |
| PATCH | `/complaints/{id}/resolve` | AM | Resolve complaint |

### Admin & Area Manager APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/admin/stats` | Admin | Platform statistics |
| GET | `/admin/users` | Admin | List all users |
| PATCH | `/admin/users/{id}/deactivate` | Admin | Deactivate user |
| PATCH | `/admin/users/{id}/activate` | Admin | Activate user |
| PATCH | `/admin/users/{id}/role` | Admin | Change user role |
| GET | `/admin/area-manager/stats` | Area Manager | AM statistics |

### Chatbot APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/chat/bot` | Token | Chat with AI |
| POST | `/chat/whatsapp` | Token | Generate WhatsApp link |

### Priyo (Subscription) APIs
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/priyo/subscribe` | Provider | Subscribe to Priyo |
| GET | `/priyo/subscription` | Provider | Get subscription |
| DELETE | `/priyo/unsubscribe` | Provider | Cancel subscription |
| POST | `/priyo/instant-book` | Customer | Instant booking |

---

## 5. Testing APIs with JSON

### Using Python
```python
import requests

BASE = "http://127.0.0.1:8000"

# 1. Register a new user
r = requests.post(f"{BASE}/auth/register", json={
    "full_name": "Test User",
    "phone_number": "01812345678",
    "email": "test@test.com",
    "password": "pass123",
    "role": "customer"
})
print("Register:", r.status_code, r.json())

# 2. Login
r = requests.post(f"{BASE}/auth/login", data={
    "username": "01812345678",
    "password": "pass123"
})
token = r.json()["access_token"]
print("Login: OK")

# 3. Get my profile
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
print("Profile:", r.json())

# 4. Get services
r = requests.get(f"{BASE}/services/items")
print("Services:", r.json())
```

### Using cURL
```bash
# Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"John","phone_number":"01800000001","email":"john@test.com","password":"pass123","role":"customer"}'

# Login
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=01800000001&password=pass123"

# Get Profile (with token)
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Using JavaScript
```javascript
// Register
fetch('http://127.0.0.1:8000/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        full_name: "John",
        phone_number: "01800000001",
        email: "john@test.com",
        password: "pass123",
        role: "customer"
    })
})
.then(res => res.json())
.then(data => console.log(data));

// Login
fetch('http://127.0.0.1:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'username=01800000001&password=pass123'
})
.then(res => res.json())
.then(data => {
    localStorage.setItem('token', data.access_token); // Store token
});

// Get profile with token
const token = localStorage.getItem('token');
fetch('http://127.0.0.1:8000/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 6. JSON Response Examples

### Register Response (201 Created)
```json
{
    "id": "78e62c2b-cc02-42fd-91f0-261d31e1e6b2",
    "full_name": "John Doe",
    "phone_number": "01800000001",
    "email": "john@test.com",
    "role": "customer",
    "is_active": true,
    "is_verified": false,
    "created_at": "2026-05-14T05:40:41.007780Z",
    "updated_at": "2026-05-14T05:40:41.007784Z"
}
```

### Login Response (200 OK)
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Error Response (401 Unauthorized)
```json
{
    "detail": "Invalid phone number or password"
}
```

### Error Response (403 Forbidden)
```json
{
    "detail": "Role UserRole.customer is not authorized to access this resource. Allowed roles: ['admin']"
}
```

---

## 7. API Testing with Server Running

Make sure the server is running:
```bash
python -m uvicorn app.main:app --reload
```

Then access the interactive API documentation:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## 8. Quick Test Script

Create `test_quick.py`:

```python
import requests

BASE = "http://127.0.0.1:8000"

# Test 1: Get Services (public)
print("=== Services ===")
r = requests.get(f"{BASE}/services/items")
print(f"Status: {r.status_code}")
print(f"Data: {r.json()[:2]}")  # First 2 items

# Test 2: Get Providers (public)
print("\n=== Providers ===")
r = requests.get(f"{BASE}/providers/")
print(f"Status: {r.status_code}")
print(f"Data: {r.json()}")

# Test 3: Register & Login
print("\n=== Auth ===")
phone = "01900000001"
r = requests.post(f"{BASE}/auth/register", json={
    "full_name": "Test",
    "phone_number": phone,
    "email": "test@test.com",
    "password": "pass123",
    "role": "customer"
})
print(f"Register: {r.status_code}")

r = requests.post(f"{BASE}/auth/login", data={"username": phone, "password": "pass123"})
print(f"Login: {r.status_code}")
token = r.json()["access_token"]

# Test 4: Get Profile
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
print(f"Profile: {r.json()['full_name']}")
```

Run: `python test_quick.py`