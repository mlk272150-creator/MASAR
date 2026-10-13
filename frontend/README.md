# Masar Frontend

- Login: `/ui/`
- Main dashboard: `/ui/dashboard.html`
- AI task pricing: `/ui/ai-pricing.html`
- API documentation: `/docs`

The backend stores SQLite data persistently in `backend/masar.db` by default.
The project `.env` selects that file with `MASAR_DATABASE_URL`; the existing
PostgreSQL settings remain available if you later remove that override.

The XGBoost pricing model trains once at backend startup from
`backend/data/pricing_training_data.csv`. The generated dataset has 500
synthetic rows covering five Palestinian cities and four professions, with
prices between 50 and 500 points. It is demonstration data, not verified market
history, so its predictions must not be treated as accurate local prices. A
held-out check yielded a 15.24-point MAE against synthetic labels only; this is
not a measure of real-market pricing accuracy.

Creating a task accepts its city, profession, demand, and supply indicators.
The backend predicts and stores the reward in `reward_points`; it also requires
a worker ID and enough wallet points to reserve that reward in escrow.
`POST /users/login` and the existing `POST /auth/login` both verify the stored
password and return the existing account ID and balance.

When serving files separately, serve this directory on a local origin and keep
FastAPI running on port 8000. The API permits local development origins. The
frontend uses `http://127.0.0.1:8000` by default when served from another port;
to override it, set `localStorage.setItem("masar-api-base", "http://localhost:8000")`
in the browser before opening the frontend.

Phone login requires an account with `phone_number` created through
`POST /auth/register`. Existing accounts without a phone number must be updated
before phone login. The current backend issues a demo token and does not enforce
authentication or authorization; client-side login is not a security boundary.

Replace the synthetic pricing CSV with representative, consented historical
local data before using predictions in production.
