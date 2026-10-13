# Deploy MASAR on Render

## 1. Push the project to GitHub

Push the repository containing `backend/Dockerfile`, `backend/requirements.txt`,
`backend/app`, `backend/data/pricing_training_data.csv`, and `frontend/` to a
GitHub repository. Do not commit `.env`, `backend/masar.db`, or real credentials.

## 2. Create PostgreSQL on Render

1. In the Render dashboard, choose **New > PostgreSQL**.
2. Choose a name and region. Use the same region for the web service.
3. Create the database and wait until its status is available.
4. Copy its **Internal Database URL**. Keep this URL private.

Use an instance/retention plan suitable for the project; confirm its current
price and backup policy in Render before creating a paid resource.

## 3. Create the web service

1. Choose **New > Web Service** and connect the GitHub repository.
2. Select the branch to deploy.
3. Set **Runtime** to **Docker**.
4. Leave **Root Directory** empty (the repository root). The Docker build
   context must include both `backend/` and `frontend/`.
5. Set **Dockerfile Path** to `backend/Dockerfile`.
6. Add an environment variable named `DATABASE_URL` and set it to the
   PostgreSQL **Internal Database URL** from step 2.
7. Set the health check path to `/`.
8. Choose an instance plan, review any charges, and create the service.

The container binds to Render's `PORT` and listens on `0.0.0.0`. On startup,
FastAPI creates missing tables and adds the task pricing columns if needed.
The web service and database must remain in the same Render region to use the
internal database URL.

## 4. Check the deployment

When the service is live, open its `onrender.com` URL:

- `/` should return `{"message":"MASAR API is running","status":"ok"}`.
- `/docs` opens the FastAPI interactive API documentation.
- `/ui/` serves the web frontend.
- `/openapi.json` should include `/users/login` and `/ai/pricing/estimate`.

After deployment, use Render's logs to check application startup and its
database connection. The XGBoost model loads its 500-row demonstration dataset
from the image at startup; those synthetic prices are not verified market data.

## Important

This deployment does not make the current demo token into secure
authentication. The current ledger and task APIs do not enforce user
authorization, so do not use this service for real wallet balances or payments
until server-side authentication and authorization have been implemented and
reviewed. Restrict or remove public registration/listing endpoints before
handling real users' data.
