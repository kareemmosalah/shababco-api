# Backend Team – Milestone 1 (Admin + Shopify Events)

**Milestone:** Week 1 – Admin foundation

**Focus:**
1. Backend Core (Auth, media, admin APIs)
2. Shopify Integration for Events (create + list + fetch)

---

## Section A — Backend Core Work (Non-Shopify)

### A.1 Admin Authentication (JWT)

**Goal:** 

**Deliverables**

1. **Endpoint: POST /admin/auth/login**
   - Request:
   - Response:

2. **Endpoint: POST /admin/auth/refresh**
   - Request:
   - Response:

---

### A.2 Media Upload (Cloudinary)

**Goal:**

**Deliverables**

1. **Endpoint: POST /admin/media/upload**
   - Request:
   - Response:

---

### A.3 Admin CRUD for Events

**Goal:**

**Deliverables**

1. **Endpoint: POST /admin/events**
   - Request:
   - Response:

2. **Endpoint: GET /admin/events**
   - Request:
   - Response:

3. **Endpoint: GET /admin/events/:id**
   - Request:
   - Response:

4. **Endpoint: PUT /admin/events/:id**
   - Request:
   - Response:

5. **Endpoint: DELETE /admin/events/:id**
   - Request:
   - Response:

---

## Section B — Shopify Integration

### B.1 Shopify Event Sync (Create)

**Goal:**

**Deliverables**

1. **Service: createShopifyEvent(eventData)**
   - Input:
   - Output:

---

### B.2 Shopify Event Sync (List)

**Goal:**

**Deliverables**

1. **Service: listShopifyEvents()**
   - Input:
   - Output:

---

### B.3 Shopify Event Sync (Fetch Single)

**Goal:**

**Deliverables**

1. **Service: fetchShopifyEvent(eventId)**
   - Input:
   - Output:

---

## Database Schema

### Events Table

**Table:** `events`

**Columns:**
- 
- 
- 

---

### Admin Users Table

**Table:** `admin_users`

**Columns:**
- 
- 
- 

---

## Environment Variables

```
# Database

# Shopify

# Cloudinary

# JWT

```

---

## Testing Checklist

- [ ] Admin login works and returns valid JWT
- [ ] Admin refresh token works
- [ ] Media upload to Cloudinary works
- [ ] Create event in database
- [ ] List all events
- [ ] Get single event by ID
- [ ] Update event
- [ ] Delete event
- [ ] Shopify event creation
- [ ] Shopify event listing
- [ ] Shopify event fetch

---

## Notes

-
