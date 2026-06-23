from fastapi import APIRouter
from Handlers.user_handler import login_handler

router = APIRouter()

router.post("/login")(login_handler)