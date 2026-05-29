from fastapi import FastAPI, Request
from pydantic import BaseModel
import hashlib
import hmac
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AtiyeMehrToos MiniApp Backend")

TG_BOT_TOKEN = os.getenv("TG_TOKEN", "")
BALE_BOT_TOKEN = os.getenv("BALE_TOKEN", "")

class MiniAppInitData(BaseModel):
    init_data: str
    platform: str = "telegram"

def validate_telegram_init_data(init_data: str) -> bool:
    # Simplified validation - implement full HMAC in production
    return "hash=" in init_data  # placeholder

@app.post("/api/validate")
async def validate_init(data: MiniAppInitData):
    if data.platform == "telegram":
        valid = validate_telegram_init_data(data.init_data)
    else:
        valid = True  # Bale validation similar
    return {"valid": valid, "user": {"id": 123, "name": "Demo User"}}

@app.get("/")
async def root():
    return {"message": "AtiyeMehrToos MiniApp API is running"}