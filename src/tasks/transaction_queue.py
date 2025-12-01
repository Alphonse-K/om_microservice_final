# # src/tasks/transaction_queue.py
# from src.worker_app import celery_app
# from sqlalchemy.orm import Session
# from datetime import datetime, timezone
# from src.core.database import SessionLocal
# from src.models.transaction import PendingTransaction
# from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase
# from src.services.neogate_client import NeoGateTG400Client

# om_client = NeoGateTG400Client()
# MAX_REQUESTS_PER_MINUTE = 6

# @celery_app.task(bind=True, max_retries=3, name='src.tasks.transaction_que.process_transaction_queue')
# def process_transaction_queue():
#     db: Session = SessionLocal()
#     try:
#         pending_requests = (
#             db.query(PendingTransaction)
#             .filter(PendingTransaction.status == "pending")
#             .order_by(PendingTransaction.created_at.asc())
#             .limit(MAX_REQUESTS_PER_MINUTE)
#             .all()
#         )

#         for req in pending_requests:
#             try:
#                 req.status = "processing"
#                 db.commit()

#                 if req.transaction_type == "airtime":
#                     tx = AirtimePurchase(
#                         recipient=req.msisdn,
#                         amount=req.amount,
#                         transaction_type="airtime",
#                         partner_id=req.partner_id,
#                         status="created",
#                         created_at=datetime.now(timezone.utc)
#                     )
#                     db.add(tx)
#                     db.commit()
#                     db.refresh(tx)
#                     response = om_client.purchase_credit(req.msisdn, req.amount)

#                 elif req.transaction_type == "deposit":
#                     tx = DepositTransaction(
#                         recipient=req.msisdn,
#                         amount=req.amount,
#                         transaction_type="deposit",
#                         partner_id=req.partner_id,
#                         status="created",
#                         created_at=datetime.now(timezone.utc)
#                     )
#                     db.add(tx)
#                     db.commit()
#                     db.refresh(tx)
#                     response = om_client.send_deposit_with_confirmation(req.msisdn, req.amount)

#                 elif req.transaction_type == "withdrawal":
#                     tx = WithdrawalTransaction(
#                         sender=req.msisdn,
#                         amount=req.amount,
#                         transaction_type="withdrawal",
#                         partner_id=req.partner_id,
#                         status="initiated",
#                         created_at=datetime.now(timezone.utc)
#                     )
#                     db.add(tx)
#                     db.commit()
#                     db.refresh(tx)
#                     response = om_client.withdraw_cash(req.msisdn, req.amount)

#                 tx.gateway_response = response.get("response") or str(response)
#                 tx.status = "pending"  # Waiting for email confirmation
#                 db.commit()

#                 req.status = "done"
#                 db.commit()

#             except Exception as e:
#                 req.status = "failed"
#                 db.commit()

#     finally:
#         db.close()


# src/tasks/transaction_queue.py
import logging
from decimal import Decimal
from src.worker_app import celery_app
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.core.database import SessionLocal
from src.models.transaction import PendingTransaction, CompanyCountryBalance, FeeConfig, Country, Company
from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase
from src.services.neogate_client import NeoGateTG400Client

om_client = NeoGateTG400Client()
MAX_REQUESTS_PER_MINUTE = 6

logger = logging.getLogger("transaction_queue")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class BalanceManager:
    @staticmethod
    def hold_balance(db: Session, company_id: int, country_id: int, amount: Decimal) -> CompanyCountryBalance:
        """Hold balance for a transaction using Decimal"""
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).first()
        
        if not balance:
            raise Exception(f"No balance found for company {company_id} in country {country_id}")
        
        if balance.available_balance < amount:
            raise Exception("Insufficient available balance")
        
        # Hold the funds using Decimal arithmetic
        balance.available_balance -= amount
        balance.held_balance += amount
        
        db.commit()
        return balance

    @staticmethod
    def release_balance(db: Session, balance_id: int, amount: Decimal, success: bool = True):
        """Release held balance - either commit or rollback using Decimal"""
        balance = db.query(CompanyCountryBalance).filter(CompanyCountryBalance.id == balance_id).first()
        if not balance:
            return
        
        if success:
            # Transaction succeeded - keep the held amount deducted
            balance.held_balance -= amount
        else:
            # Transaction failed - return funds to available balance
            balance.held_balance -= amount
            balance.available_balance += amount
        
        db.commit()

    @staticmethod
    def record_balance_snapshot(db: Session, transaction, balance):
        """Record before/after balance only for successful transactions"""
        if transaction.status == "success":
            transaction.before_balance = balance.available_balance + balance.held_balance + transaction.amount
            transaction.after_balance = balance.available_balance + balance.held_balance
            db.commit()

class FeeCalculator:
    @staticmethod
    def calculate_fee(db: Session, source_country_id: int, destination_country_id: int, amount: Decimal) -> dict:
        """Calculate fees for a transaction corridor"""
        
        # Find fee configuration for this country pair
        fee_config = db.query(FeeConfig).filter(
            FeeConfig.source_country_id == source_country_id,
            FeeConfig.destination_country_id == destination_country_id,
            FeeConfig.is_active == True
        ).first()
        
        # If no specific fee config, no fees apply
        if not fee_config:
            return {
                "fee_amount": Decimal('0'), 
                "net_amount": amount, 
                "fee_config_used": None
            }
        
        # Calculate based on fee type
        if fee_config.fee_type == "flat":
            fee_amount = fee_config.flat_fee
        elif fee_config.fee_type == "percent":
            fee_amount = (amount * fee_config.percent_fee) / Decimal('100')
        elif fee_config.fee_type == "mixed":
            fee_amount = fee_config.flat_fee + (amount * fee_config.percent_fee) / Decimal('100')
        else:
            fee_amount = Decimal('0')
        
        # Apply minimum fee protection
        if fee_config.min_fee and fee_amount < fee_config.min_fee:
            fee_amount = fee_config.min_fee
            
        # Apply maximum fee cap  
        if fee_config.max_fee and fee_amount > fee_config.max_fee:
            fee_amount = fee_config.max_fee
        
        # Final amount after fees
        net_amount = amount - fee_amount
        
        return {
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "fee_config_used": fee_config.id,
            "fee_type": fee_config.fee_type
        }
    
    
class CountryRouter:
    @staticmethod
    def get_destination_country(db: Session, country_iso: str) -> int:
        """Determine country from explicit ISO code - most reliable approach"""
        
        if not country_iso:
            raise ValueError("Country ISO code is required")
        
        country = db.query(Country).filter(
            Country.iso_code == country_iso.upper(),
            Country.is_active == True
        ).first()
        
        if not country:
            raise ValueError(f"Country with ISO code '{country_iso}' not found or inactive")
        
        return country.id    
    

@celery_app.task(bind=True, max_retries=3, name='src.tasks.transaction_queue.process_transaction_queue')
def process_transaction_queue(self):
    """Process transactions but keep them as INITIATED until email confirmation"""
    db: Session = SessionLocal()
    balance_manager = BalanceManager()
    fee_calculator = FeeCalculator()
    country_router = CountryRouter()
    
    try:
        pending_requests = (
            db.query(PendingTransaction)
            .filter(PendingTransaction.status == "pending")
            .order_by(PendingTransaction.created_at.asc())
            .limit(MAX_REQUESTS_PER_MINUTE)
            .all()
        )

        for req in pending_requests:
            transaction = None
            try:
                # Use the company_id from the pending transaction
                company_id = req.company_id
                
                # Validate company exists and is active
                company = db.query(Company).filter(
                    Company.id == company_id,
                    Company.is_active == True
                ).first()
                
                if not company:
                    raise Exception(f"Company {company_id} not found or inactive")
                
                req.status = "processing"
                db.commit()

                # Determine destination country
                destination_country_id = country_router.get_destination_country(db, req.country_iso)
                
                if not destination_country_id:
                    raise Exception(f"Could not determine destination country for ISO: {req.country_iso}")
                
                # Get company balance for this country
                balance = db.query(CompanyCountryBalance).filter(
                    CompanyCountryBalance.company_id == company_id,
                    CompanyCountryBalance.country_id == destination_country_id
                ).first()
                
                if not balance:
                    raise Exception(f"No balance configured for company {company_id} in country {destination_country_id}")

                # Check if balance is sufficient
                if balance.available_balance < Decimal(str(req.amount)):
                    raise Exception(f"Insufficient balance. Available: {balance.available_balance}, Required: {req.amount}")

                # Convert amount to Decimal
                amount = Decimal(str(req.amount))
                
                # Calculate fees and net amount
                fee_info = fee_calculator.calculate_fee(
                    db, 
                    company_id,  # Pass company_id for company-specific fees
                    destination_country_id, 
                    amount, 
                    req.transaction_type
                )
                
                # Hold balance for the transaction
                held_balance = balance_manager.hold_balance(
                    db, 
                    company_id, 
                    destination_country_id, 
                    amount
                )
                
                if not held_balance:
                    raise Exception("Failed to hold balance for transaction")
                
                # Create transaction record
                tx_data = {
                    "company_id": company_id,  # Include company_id in transaction
                    "amount": amount,
                    "msisdn": req.msisdn,
                    "destination_country_id": destination_country_id,
                    "destination_balance_id": balance.id,
                    "partner_code": req.partner_code,
                    "transaction_type": req.transaction_type,
                    "status": "initiated",
                    "fee_amount": fee_info["fee_amount"],
                    "net_amount": fee_info["net_amount"],
                    "pending_transaction_id": req.id,  # Link back to pending transaction
                }

                # Create specific transaction type
                if req.transaction_type == "airtime":
                    transaction = AirtimePurchase(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    response = om_client.purchase_credit(req.msisdn, float(amount))

                elif req.transaction_type == "deposit":
                    transaction = DepositTransaction(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    response = om_client.send_deposit_with_confirmation(req.msisdn, float(amount))

                elif req.transaction_type == "withdrawal":
                    transaction = WithdrawalTransaction(
                        sender=req.msisdn,
                        **tx_data
                    )
                    response = om_client.withdraw_cash(req.msisdn, float(fee_info["net_amount"]))

                else:
                    raise Exception(f"Unknown transaction type: {req.transaction_type}")

                # Store gateway response
                transaction.gateway_response = response.get("response") or str(response)
                transaction.gateway_transaction_id = response.get("transaction_id")
                
                db.add(transaction)
                db.commit()
                db.refresh(transaction)
                
                # Update pending request status
                req.status = "processed"
                req.processed_at = datetime.now(timezone.utc)
                db.commit()

                # Schedule email confirmation task
                if transaction:
                    send_transaction_confirmation_email.delay(transaction.id)

            except Exception as e:
                logger.error(f"Failed to process pending transaction {req.id}: {str(e)}")
                
                # Release held balance if it was held
                if 'held_balance' in locals() and held_balance:
                    try:
                        balance_manager.release_balance(
                            db, 
                            company_id, 
                            destination_country_id, 
                            amount
                        )
                    except Exception as balance_error:
                        logger.error(f"Failed to release balance for failed transaction {req.id}: {str(balance_error)}")
                
                # Update status to failed
                req.status = "failed"
                req.error_message = str(e)[:500]  # Truncate if too long
                
                if transaction:
                    transaction.status = "failed"
                    transaction.error_message = str(e)
                
                db.commit()

    except Exception as e:
        logger.error(f"Transaction queue processing failed: {str(e)}")
        # Retry the entire task if something went wrong
        self.retry(countdown=60)
    
    finally:
        db.close()