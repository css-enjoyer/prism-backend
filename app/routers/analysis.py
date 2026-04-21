from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import verify_api_key
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisResponse

router = APIRouter()


# ? Not sure if needed, code reviews are tied with github prs
@router.post("/review-diff", dependencies=[Depends(verify_api_key)])
async def review_diff():
    pass


@router.get(
    "/analyses",
    response_model=list[AnalysisResponse],
    dependencies=[Depends(verify_api_key)],
)
async def list_analyses(
    repo_full_name: str | None = Query(default=None),
    pr_number: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Analysis).order_by(Analysis.created_at.desc())

    if repo_full_name is not None:
        stmt = stmt.where(Analysis.repo_full_name == repo_full_name)
    if pr_number is not None:
        stmt = stmt.where(Analysis.pr_number == pr_number)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)

    return result.scalars().all()


@router.get(
    "/analyses/{id}",
    response_model=AnalysisResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_analysis(id: int, db: AsyncSession = Depends(get_db)) -> AnalysisResponse:
    stmt = select(Analysis).where(Analysis.id == id)

    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis
