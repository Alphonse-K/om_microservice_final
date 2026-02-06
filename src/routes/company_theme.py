from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.transaction import CompanyThemeResponse, CompanyThemeCreateUpdate
from src.models.transaction import User
from fastapi import HTTPException
from src.core.auth_dependencies import get_current_user
from src.services.company_theme_service import upsert_company_theme, get_company_theme

theme_router = APIRouter(prefix="/api/v1/company", tags=['Company Themes'])


@theme_router.put(
    "/{company_id}/theme",
    response_model=CompanyThemeResponse
)
@theme_router.post(
    "/{company_id}/theme",
    response_model=CompanyThemeResponse
)
def create_or_update_company_theme(
    company_id: int,
    data: CompanyThemeCreateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.company_id != company_id:
        raise HTTPException(403, "Access denied")

    if current_user.role != "ADMIN":
        raise HTTPException(403, "Admin only")

    return upsert_company_theme(db, company_id, data)

@theme_router.get(
    "/{company_id}/theme",
    response_model=CompanyThemeResponse
)
def read_company_theme(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.company_id != company_id:
        raise HTTPException(403, "Access denied")

    theme = get_company_theme(db, company_id)
    if not theme:
        raise HTTPException(404, "Theme not found")

    return theme
