from src.models.transaction import (
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase,
)

def normalize_financial_row(row):
    if isinstance(row, DepositTransaction):
        return {
            "id": row.id,
            "type": "deposit",
            "counterparty": row.recipient,
            "amount": row.amount,
            "fee_amount": row.fee_amount,
            "net_amount": row.net_amount,
            "status": row.status,
            "company_id": row.company_id,
            "country_id": row.country_id,
            "partner_id": row.partner_id,
            "gateway_transaction_id": row.gateway_transaction_id,
            "created_at": row.created_at,
        }

    if isinstance(row, WithdrawalTransaction):
        return {
            "id": row.id,
            "type": "withdrawal",
            "counterparty": row.sender,
            "amount": row.amount,
            "fee_amount": row.fee_amount,
            "net_amount": row.net_amount,
            "status": row.status,
            "company_id": row.company_id,
            "country_id": row.country_id,
            "partner_id": row.partner_id,
            "gateway_transaction_id": row.gateway_transaction_id,
            "created_at": row.created_at,
        }

    if isinstance(row, AirtimePurchase):
        return {
            "id": row.id,
            "type": "airtime",
            "counterparty": row.recipient,
            "amount": row.amount,
            "fee_amount": row.fee_amount,
            "net_amount": row.net_amount,
            "status": row.status,
            "company_id": row.company_id,
            "country_id": row.country_id,
            "partner_id": row.partner_id,
            "gateway_transaction_id": row.gateway_transaction_id,
            "created_at": row.created_at,
        }


FINANCIAL_COLUMNS = [
    ("Transaction ID", "id"),
    ("Type", "type"),
    ("Counterparty", "counterparty"),
    ("Amount", "amount"),
    ("Fee", "fee_amount"),
    ("Net Amount", "net_amount"),
    ("Status", "status"),
    ("Company ID", "company_id"),
    ("Country ID", "country_id"),
    ("Partner ID", "partner_id"),
    ("Gateway Tx ID", "gateway_transaction_id"),
    ("Created At", "created_at"),
]


PROCUREMENT_COLUMNS = [
    ("ID", "id"),
    ("Slip Number", "slip_number"),
    ("Bank", "bank_name"),
    ("Amount", "amount"),
    ("Status", "status"),
    ("Initiation Date", "initiation_date"),
    ("Validation Date", "validation_date"),
    ("Initiated By", "initiated_by"),
    ("Validated By", "validated_by"),
    ("Company ID", "company_id"),
    ("Country ID", "country_id"),
]
