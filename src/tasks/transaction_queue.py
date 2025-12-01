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
from decimal import Decimal
from src.worker_app import celery_app
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.core.database import SessionLocal
from src.models.transaction import PendingTransaction, CompanyCountryBalance, FeeConfig, Country
from src.models.transaction import DepositTransaction, WithdrawalTransaction, AirtimePurchase
from src.services.neogate_client import NeoGateTG400Client

om_client = NeoGateTG400Client()
MAX_REQUESTS_PER_MINUTE = 6

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
def process_transaction_queue():
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
                req.status = "processing"
                db.commit()

                # Determine destination country from request (you'll need to add country_iso to PendingTransaction)
                destination_country_id = country_router.get_destination_country(db, req.country_iso)
                
                # Get company balance for this country
                company_id = 1  # This should come from your request context
                
                balance = db.query(CompanyCountryBalance).filter(
                    CompanyCountryBalance.company_id == company_id,
                    CompanyCountryBalance.country_id == destination_country_id
                ).first()
                
                if not balance:
                    raise Exception(f"No balance configured for company {company_id} in country {destination_country_id}")

                # Convert amount to Decimal
                amount = Decimal(str(req.amount))
                
                # Calculate fees and net amount
                fee_info = fee_calculator.calculate_fee(db, destination_country_id, destination_country_id, amount)
                
                # Hold balance for the transaction
                held_balance = balance_manager.hold_balance(db, company_id, destination_country_id, amount)
                
                # Create transaction record WITHOUT balance tracking initially
                tx_data = {
                    "amount": amount,
                    "msisdn": req.msisdn,
                    "destination_country_id": destination_country_id,
                    "destination_balance_id": balance.id,
                    "partner_code": req.partner_code,
                    "transaction_type": req.transaction_type,
                    "status": "initiated",  # Will be confirmed by email confirmation task
                    "fee_amount": fee_info["fee_amount"],
                    # NO before_balance or after_balance here - only set on success
                }

                if req.transaction_type == "airtime":
                    tx = AirtimePurchase(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    response = om_client.purchase_credit(req.msisdn, float(amount))

                elif req.transaction_type == "deposit":
                    tx = DepositTransaction(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    response = om_client.send_deposit_with_confirmation(req.msisdn, float(amount))

                elif req.transaction_type == "withdrawal":
                    tx = WithdrawalTransaction(
                        sender=req.msisdn,
                        **tx_data
                    )
                    response = om_client.withdraw_cash(req.msisdn, float(fee_info["net_amount"]))

                # Store gateway response but don't confirm yet
                tx.gateway_response = response.get("response") or str(response)
                                
                db.add(tx)
                db.commit()
                db.refresh(tx)
                
                req.status = "processing"  # Changed from "pending" to "done" since processing completed
                db.commit()

            except Exception as e:
                # If transaction was created but failed, release held balance
                if transaction and transaction.destination_balance_id:
                    try:
                        balance_manager.release_balance(db, transaction.destination_balance_id, Decimal(str(req.amount)), success=False)
                    except:
                        pass
                
                req.status = "failed"
                if transaction:
                    transaction.status = "failed"
                    transaction.error_message = str(e)
                db.commit()

    finally:
        db.close()