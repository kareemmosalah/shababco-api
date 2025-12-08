# Shababco API

The **Shababco API** is the backend service powering the Shababco Events Marketplace.  
It provides all server-side functionality, including admin operations, marketplace browsing APIs, Shopify integrations, ID verification, and webhook handling.

---

## Features

### **Admin Platform**
- Admin authentication (JWT)
- Create + manage events
- Ticket management (Milestone 2+)
- Image upload service (GCS)
- Shopify synchronization

### **Marketplace APIs**
- Retrieve published events from Shopify
- Retrieve ticket types (Shopify variants)
- Cart and checkout (Milestone 3–4)

### **Integrations**
- Shopify Admin API (products, variants, inventory)
- Shopify Storefront API (carts, checkout)
- IDV (Identity Verification) microservice
- Scar AI Product Definer (AI-generated ticket details)
- Webhooks (Shopify orders, IDV results)

---

## Tech Stack

- **FastAPI** (Python)
- **PostgreSQL** (Cloud SQL)
- **Google Cloud Run** (deployment)
- **Google Cloud Storage** (image uploads)
- **Secret Manager** (credentials)
- **Shopify Admin & Storefront API**
- **JWT Authentication**

---

## Branching Strategy

The repository uses **environment-based branches**:

| Branch | Purpose | Deployment |
|--------|----------|-------------|
| `dev` | Active development branch | Deploys to **Dev environment** |
| `stage` | Pre-production testing & UAT | Deploys to **Staging environment** |
| `prod` | Production-ready code | Deploys to **Production** |

All feature work must branch off `dev`:
