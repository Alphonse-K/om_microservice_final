# src/services/company_theme_service.py
from sqlalchemy.orm import Session
from src.models.company_theme import CompanyTheme
from src.schemas.transaction import CompanyThemeCreateUpdate


def get_company_theme(db: Session, company_id: int):
    return db.query(CompanyTheme).filter(
        CompanyTheme.company_id == company_id
    ).first()


def upsert_company_theme(
    db: Session,
    company_id: int,
    data: CompanyThemeCreateUpdate
):
    theme = get_company_theme(db, company_id)

    if theme:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(theme, key, value)
    else:
        theme = CompanyTheme(
            company_id=company_id,
            **data.model_dump()
        )
        db.add(theme)

    db.commit()
    db.refresh(theme)
    return theme
