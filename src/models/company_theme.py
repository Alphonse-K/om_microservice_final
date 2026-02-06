# src/models/company_theme.py
from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, ForeignKey, func, UniqueConstraint
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class CompanyTheme(Base):
    __tablename__ = "company_themes"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    theme_color = Column(String(50), nullable=False)

    theme_primary = Column(String(50), nullable=True)
    theme_secondary = Column(String(50), nullable=True)
    theme_angle = Column(Integer, nullable=True)

    theme_is_solid = Column(Boolean, default=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    company = relationship("Company", back_populates="theme")
