"""Point d'entrée FastAPI.

TODO: monter les routers de chaque module sous /api/v1.
"""

from fastapi import FastAPI

app = FastAPI(title="Trading Bot IA — Backend")

# from app.modules.auth.router import router as auth_router
# app.include_router(auth_router, prefix="/api/v1")
# ... (un include_router par module)


@app.get("/health")
def health():
    """Healthcheck — TODO: vérifier DB, connexion plateforme, quota Gemini."""
    return {"status": "ok"}
