from fastapi import FastAPI
from Routers import user_router

app = FastAPI(title="BlockFlow API")

app.include_router(user_router.router, prefix="/api")