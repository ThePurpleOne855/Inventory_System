# Madre Tierra — front end

React + TypeScript + Vite + Tailwind admin UI for the inventory API.

## Running it

The API must be running first:

```bash
# terminal 1 — API on :8000
cd Madre_Tierra_Inventory_System
uvicorn app.main:app --reload

# terminal 2 — UI on :5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in with the operator credentials created by
`python -m app.core.setup_auth`.

Vite proxies `/api/*` to `http://127.0.0.1:8000`, so the browser stays on one
origin and CORS never comes into play in development. Point it elsewhere with
`VITE_API_TARGET=http://host:port npm run dev`, or build against an absolute API
URL with `VITE_API_URL=https://api.example.com npm run build`.

## Pages

| Route | What it does |
| --- | --- |
| `/clients` | List, filter, add, edit and delete clients; WhatsApp link per client |
| `/inventory` | Current stock with availability badges, inline restocking, stock-value totals, and product add/edit/delete |
| `/orders` | List orders, create one from products in stock, preview an invoice, download it as PDF, email it to the client |
| `/messages` | Pick recipients, compose with `{name}` placeholders, send one email each; per-client WhatsApp links |

On **Orders → New order**, search and select an existing client to fill their contact
details, or enter a new client's name, email, phone, street address, city, state,
country, and ZIP/postal code. These contact and address fields are required for new
profiles. Phone numbers format automatically on blur using the selected country or
an explicit international calling code. Saving creates the
new profile (or updates the selected profile) together with the order. Failed orders
do not save client changes. Add products and quantities; totals use inventory prices
and ordered quantities are deducted from stock. Apply the latest Alembic migration
before using client addresses.

## Layout

```
src/
├── lib/
│   ├── api.ts       # typed fetch wrapper; attaches the bearer token, maps errors
│   ├── auth.tsx     # session context; any 401 drops back to the login screen
│   ├── format.ts    # money, dates, phone and placeholder helpers
│   └── types.ts     # mirrors app/schema/*.py
├── components/      # Layout plus shared Button/Card/Modal/Alert primitives
└── pages/           # Login, Clients, Products, Orders, Messages
```

The token is kept in `localStorage` and sent as `Authorization: Bearer …`.
Sessions are stored server-side and expire after 8 hours.
