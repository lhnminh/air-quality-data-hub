# AirTrace frontend

This folder contains the dashboard that people see in their browser.

## Files your team will edit

| File | What it does |
|---|---|
| `app/page.tsx` | Builds the dashboard and requests PostgreSQL rows from the Python API. |
| `app/mock-data.ts` | Provides clearly labeled sample data when the API is unavailable. |
| `app/globals.css` | Controls colors, spacing, desktop layout, and mobile layout. |
| `app/layout.tsx` | Sets the browser tab title and page description. |

The remaining files are standard Next.js build settings used by Vercel. You
normally do not need to change them.

## Run the dashboard locally

The dashboard and Python API run in two separate terminal windows.

### Terminal 1: start the Python API

From the main project folder:

```bash
uv run uvicorn api:app --reload --port 8000
```

The API reads existing rows from PostgreSQL. It does not make a new IQAir
request.

### Terminal 2: start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

- **Reading PostgreSQL** means the Python API returned real database rows.
- **Demo data** means the API was unavailable or the database was empty.

## Check the frontend

```bash
npm run lint
npm test
```

`npm test` creates a production build and checks that the important dashboard
content appears in the generated page.

## Later deployment note

The frontend is intended for Vercel. The application uses hosted PostgreSQL so
the deployed Python API can read persistent observations without relying on a
local database file.
