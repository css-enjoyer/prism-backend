from fastapi import APIRouter, Depends

from app.dependencies import verify_api_key

router = APIRouter()


@router.post("/review-diff", dependencies=[Depends(verify_api_key)])
async def review_diff():
    pass
