from fastapi import Header, HTTPException
from app.config import settings


# This is a dependency function that can be used in any route to require API key authentication.
# Usage: @router.get("/some-route", dependencies=[Depends(verify_api_key)])
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
