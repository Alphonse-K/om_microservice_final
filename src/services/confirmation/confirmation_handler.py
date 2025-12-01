# from datetime import datetime, timezone

# def confirm_transaction(db: Session, tx, parsed: dict, email_obj):
#     # 1. Update status
#     tx.status = "success"

#     # 2. Store validation timestamp
#     tx.validated_at = datetime.now(timezone.utc)

#     # 3. Store operator transaction ID
#     if parsed.get("transaction_id"):
#         tx.service_partner_id = parsed["transaction_id"]

#     # 4. Save gateway response (raw email metadata)
#     tx.gateway_response = email_obj.body


#     # 5. Commit all changes
#     db.commit()
#     db.refresh(tx)
#     return tx

# src/services/confirmation/confirmation_handler.py
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.models.transaction import CompanyCountryBalance

def confirm_transaction(db: Session, transaction, parsed_data, email_obj):
    """Confirm a transaction and handle balance updates"""
    
    # 1. Update transaction status and metadata
    transaction.status = "success"
    transaction.validated_at = datetime.now(timezone.utc)
    
    # 2. Store operator transaction ID
    if parsed_data.get("transaction_id"):
        transaction.service_partner_id = parsed_data["transaction_id"]
    
    # 3. Save gateway response (raw email metadata)
    transaction.gateway_response = email_obj.body
    
    # 4. Handle balance updates based on transaction type
    balance = db.query(CompanyCountryBalance).filter(
        CompanyCountryBalance.id == transaction.destination_balance_id
    ).first()
    
    if balance:
        if transaction.transaction_type == "deposit":
            # DEPOSIT: Company pays FROM their wallet TO Orange Money account
            # Company's balance DECREASES (they're spending from their pre-funded account)
            transaction.before_balance = balance.available_balance + balance.held_balance
            balance.available_balance -= transaction.amount  # Deduct from company's balance
            transaction.after_balance = balance.available_balance + balance.held_balance
            print(f"📥 DEPOSIT: Company paid {transaction.amount} to Orange Money → Balance: {transaction.after_balance}")
            
        elif transaction.transaction_type == "airtime":
            # AIRTIME: Company pays FROM their wallet FOR airtime
            # Company's balance DECREASES (they're spending from their pre-funded account)
            transaction.before_balance = balance.available_balance + balance.held_balance
            balance.available_balance -= transaction.amount  # Deduct from company's balance
            transaction.after_balance = balance.available_balance + balance.held_balance
            print(f"📱 AIRTIME: Company paid {transaction.amount} for airtime → Balance: {transaction.after_balance}")
            
        elif transaction.transaction_type == "withdrawal":
            # WITHDRAWAL: Orange Money pays TO company's wallet
            # Company's balance INCREASES (they're receiving money into their pre-funded account)
            transaction.before_balance = balance.available_balance + balance.held_balance
            balance.available_balance += transaction.amount  # Add to company's balance
            transaction.after_balance = balance.available_balance + balance.held_balance
            print(f"📤 WITHDRAWAL: Company received {transaction.amount} from Orange Money → Balance: {transaction.after_balance}")
    
    # 5. Commit all changes
    db.commit()
    db.refresh(transaction)
    return transaction