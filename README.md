# RetailPOS — Billing & Inventory Management Software

A full-stack retail billing and inventory management system built with **FastAPI** (Python) and **React** (TypeScript).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite |
| Styling | Tailwind CSS v4 |
| Charts | Recharts |
| Backend | Python + FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Auth | JWT + bcrypt |
| Validation | Pydantic v2 |

## Features

- **POS Billing** — Barcode scanning, product search, cart, discounts, tax, payment
- **Product Management** — Add/edit/deactivate products with barcode, SKU, pricing
- **Inventory Management** — Stock-in, adjustments, low-stock alerts, audit trail
- **Sales History** — Invoice lookup, date/payment filters, sale cancellation
- **Reports & Dashboard** — Daily sales, top products, payment summary, charts
- **User Management** — Admin/staff/inventory roles with role-based access
- **Invoice Printing** — Printable HTML invoices with store branding
- **Database Backup** — Create, list, and download SQLite backups
- **Settings** — Store profile, GSTIN, invoice prefix configuration

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend will:
- Create the SQLite database automatically
- Seed a default admin user: `admin` / `admin123`
- Seed default product categories

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open the App

Navigate to **http://localhost:5173** in your browser.

Login with: **admin** / **admin123**

## Project Structure

```
Billing_Software/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # App settings
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── auth.py          # JWT + bcrypt
│   │   ├── models/          # 7 ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   └── utils/           # Seed, helpers
│   ├── data/                # SQLite database
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios client
│   │   ├── context/         # Auth context
│   │   ├── components/      # Layout, UI
│   │   ├── pages/           # 11 route pages
│   │   └── index.css        # Design system
│   ├── vite.config.ts
│   └── package.json
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| GET | `/api/auth/me` | Current user |
| CRUD | `/api/products` | Product management |
| GET | `/api/products/barcode/{bc}` | Barcode lookup |
| CRUD | `/api/categories` | Categories |
| POST | `/api/billing/complete` | Complete a sale |
| GET | `/api/billing/invoice/{id}` | Print invoice |
| GET | `/api/sales` | Sales history |
| POST | `/api/sales/{id}/cancel` | Cancel sale |
| POST | `/api/inventory/stock-in` | Add stock |
| POST | `/api/inventory/adjust` | Adjust stock |
| GET | `/api/reports/dashboard` | Dashboard stats |
| CRUD | `/api/users` | User management |
| PUT | `/api/settings` | App settings |
| POST | `/api/backup/create` | Database backup |

## Business Rules

- Products identified by unique barcode/SKU (BR-01)
- Sales cannot reduce stock below zero (BR-02)
- Completed sales decrease stock atomically (BR-03)
- Cancelled sales restore stock (BR-04)
- Products persist when stock reaches zero (BR-05)
- All stock changes logged in transaction audit trail (BR-06)
- Invoice numbers are unique (BR-07)
- Sensitive operations require authorized roles (BR-08)

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
