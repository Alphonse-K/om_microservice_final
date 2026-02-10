from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.core.auth_dependencies import get_db
from datetime import datetime

from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
    Procurement
)
from src.exports.financial_normalizer import normalize_financial_row, FINANCIAL_COLUMNS, PROCUREMENT_COLUMNS
from src.exports.csv_exporter import export_csv_from_dicts, export_excel_from_dicts


export_router = APIRouter(prefix="/api/v1", tags=["Export Reports"])


@export_router.get("/exports/financial-transactions")
def export_financial_transactions(
    format: str = "csv",
    company_id: int | None = None,
    country_id: int | None = None,
    db: Session = Depends(get_db),
):
    deposits = db.query(DepositTransaction)
    withdrawals = db.query(WithdrawalTransaction)
    airtime = db.query(AirtimePurchase)

    if company_id:
        deposits = deposits.filter(DepositTransaction.company_id == company_id)
        withdrawals = withdrawals.filter(WithdrawalTransaction.company_id == company_id)
        airtime = airtime.filter(AirtimePurchase.company_id == company_id)

    if country_id:
        deposits = deposits.filter(DepositTransaction.country_id == country_id)
        withdrawals = withdrawals.filter(WithdrawalTransaction.country_id == country_id)
        airtime = airtime.filter(AirtimePurchase.country_id == country_id)

    rows = []

    for tx in deposits.yield_per(1000):
        rows.append(normalize_financial_row(tx))

    for tx in withdrawals.yield_per(1000):
        rows.append(normalize_financial_row(tx))

    for tx in airtime.yield_per(1000):
        rows.append(normalize_financial_row(tx))

    if format == "csv":
        file = export_csv_from_dicts(rows, FINANCIAL_COLUMNS)
        return StreamingResponse(
            file,
            media_type="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=financial_transactions.csv"
            },
        )

    if format == "xlsx":
        file = export_excel_from_dicts(
            rows,
            FINANCIAL_COLUMNS,
            sheet_name="Financial Transactions"
        )
        return StreamingResponse(
            file,
            media_type=
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=financial_transactions.xlsx"
            },
        )

    raise HTTPException(400, "Invalid export format")


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
