# Backend deployment (Render)

This backend is a FastAPI app and should be started with:

uvicorn app.main:app --host 0.0.0.0 --port $PORT

## Quick deploy

1. Push this repository to GitHub.
2. In Render, choose Blueprint deployment and select this repository.
3. Render will read render.yaml and create the backend service.
4. Wait for deploy to finish.
5. Copy the backend URL from Render.
6. Verify endpoints:
   - <BACKEND_URL>/health
   - <BACKEND_URL>/facilities?q=Mom

## Connect frontend (Vercel)

1. Open frontend project settings in Vercel.
2. Set NEXT_PUBLIC_API_URL to the Render backend URL (exact base URL).
3. Redeploy Production.

Important: Do not use placeholder values like your_backend_domain.
