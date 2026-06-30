from fastapi import FastAPI
from Routers import user_router

app = FastAPI(title="BlockFlow API")

# Prepends all route collections under a clean global api scope
app.include_router(user_router.router, prefix="/api")