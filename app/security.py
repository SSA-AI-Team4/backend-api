import os
from fastapi import Header, HTTPException

API_UPLOAD_TOKEN = os.getenv("API_UPLOAD_TOKEN")

def require_token(authorization: str | None = Header(default=None)):
    if not API_UPLOAD_TOKEN:  # no token set
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    if token != API_UPLOAD_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
