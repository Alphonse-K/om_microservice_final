from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.core.auth_dependencies import get_db, require_role
from datetime import datetime

from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    Procurement,
    User
)
from src.exports.financial_normalizer import (
    normalize_financial_row, 
    FINANCIAL_COLUMNS, 
    PROCUREMENT_COLUMNS, 
    FinancialExportFilters,
    apply_common_filters
)
from src.exports.csv_exporter import export_csv_from_dicts, export_excel_from_dicts


export_router = APIRouter(prefix="/api/v1", tags=["Export Reports"])


@export_router.get("/exports/financial-transactions")
def export_financial_transactions(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    transaction_type: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    company_id: int | None = None,
    country_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(["ADMIN"])),
):
    filters = FinancialExportFilters(
        transaction_type=transaction_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        company_id=company_id,
        country_id=country_id,
    )

    rows = []

    # -----------------
    # Deposits
    # -----------------
    if not filters.transaction_type or filters.transaction_type == "cashin":
        q = db.query(DepositTransaction)
        q = apply_common_filters(q, DepositTransaction, filters)

        for tx in q.yield_per(1000):
            rows.append(normalize_financial_row(tx))

    # -----------------
    # Withdrawals
    # -----------------
    if not filters.transaction_type or filters.transaction_type == "cashout":
        q = db.query(WithdrawalTransaction)
        q = apply_common_filters(q, WithdrawalTransaction, filters)

        for tx in q.yield_per(1000):
            rows.append(normalize_financial_row(tx))

    # -----------------
    # Airtime
    # -----------------
    if not filters.transaction_type or filters.transaction_type == "airtime":
        q = db.query(AirtimePurchase)
        q = apply_common_filters(q, AirtimePurchase, filters)

        for tx in q.yield_per(1000):
            rows.append(normalize_financial_row(tx))

    if not rows:
        raise HTTPException(404, "No data found for given filters")

    if format == "csv":
        file = export_csv_from_dicts(rows, FINANCIAL_COLUMNS)
        filename = "financial_transactions.csv"
        media_type = "text/csv"

    else:
        file = export_excel_from_dicts(
            rows,
            FINANCIAL_COLUMNS,
            "Financial Transactions"
        )
        filename = "financial_transactions.xlsx"
        media_type = (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )

    return StreamingResponse(
        file,
        media_type=media_type,
        headers={
            "Content-Disposition":
            f"attachment; filename={filename}"
        },
    )


@export_router.get("/exports/procurements")
def export_procurements(
    format: str = "csv",
    db: Session = Depends(get_db),
):
    query = db.query(Procurement).yield_per(1000)

    rows = [{
        col[1]: getattr(p, col[1])
        for col in PROCUREMENT_COLUMNS
    } for p in query]

    if format == "csv":
        file = export_csv_from_dicts(rows, PROCUREMENT_COLUMNS)
        return StreamingResponse(
            file,
            media_type="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=procurements.csv"
            },
        )

    if format == "xlsx":
        file = export_excel_from_dicts(
            rows,
            PROCUREMENT_COLUMNS,
            sheet_name="Procurements"
        )
        return StreamingResponse(
            file,
            media_type=
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=procurements.xlsx"
            },
        )

    raise HTTPException(400, "Invalid export format")
