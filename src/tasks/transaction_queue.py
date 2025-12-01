# src/tasks/transaction_queue.py
import logging
import secrets
from decimal import Decimal
from src.worker_app import celery_app
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from src.core.database import SessionLocal
from src.models.transaction import (
    PendingTransaction, CompanyCountryBalance, FeeConfig, 
    Country, Company, PendingStatus, TransactionStatus, TransactionType,
    DepositTransaction, WithdrawalTransaction, AirtimePurchase
)
from src.services.neogate_client import NeoGateTG400Client
# If you have email confirmation tasks, uncomment this:
# from src.tasks.email_tasks import send_transaction_confirmation_email

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
    def release_balance(db: Session, company_id: int, country_id: int, amount: Decimal, success: bool = True):
        """Release held balance - either commit or rollback using Decimal"""
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).first()
        
        if not balance:
            return False
            
        if success:
            # Transaction succeeded - keep the held amount deducted
            balance.held_balance -= amount
        else:
            # Transaction failed - return funds to available balance
            balance.held_balance -= amount
            balance.available_balance += amount
        
        db.commit()
        return True

    @staticmethod
    def record_balance_snapshot(db: Session, transaction, balance):
        """Record before/after balance only for successful transactions"""
        if transaction.status == "success":
            transaction.before_balance = balance.available_balance + balance.held_balance + transaction.amount
            transaction.after_balance = balance.available_balance + balance.held_balance
            db.commit()


class FeeCalculator:
    @staticmethod
    def calculate_fee(db: Session, source_country_id: int, destination_country_id: int, amount: Decimal, transaction_type: str = None) -> dict:
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
                # Update status to processing
                req.status = "processing"
                db.commit()

                company_id = req.company_id
                
                # Determine destination country
                destination_country = None
                if hasattr(req, 'country_iso') and req.country_iso:
                    destination_country = db.query(Country).filter(
                        Country.iso_code == req.country_iso.upper(),
                        Country.is_active == True
                    ).first()
                
                if not destination_country:
                    raise Exception(f"Could not determine destination country for MSISDN: {req.msisdn}")
                
                # Get company balance for this country
                balance = db.query(CompanyCountryBalance).filter(
                    CompanyCountryBalance.company_id == company_id,
                    CompanyCountryBalance.country_id == destination_country.id
                ).first()
                
                if not balance:
                    raise Exception(f"No balance configured for company {company_id} in country {destination_country.iso_code}")

                # Convert amount to Decimal
                amount = Decimal(str(req.amount))
                
                # Calculate fees - using same country for source/destination for now
                # You might want to track source country separately
                fee_info = fee_calculator.calculate_fee(
                    db, 
                    source_country_id=destination_country.id,  # Same for now
                    destination_country_id=destination_country.id,
                    amount=amount,
                    transaction_type=req.transaction_type
                )
                
                # Check if balance is sufficient
                if balance.available_balance < amount:
                    raise Exception(f"Insufficient balance. Available: {balance.available_balance}, Required: {amount}")

                # Hold balance for the transaction
                held_balance = balance_manager.hold_balance(
                    db, 
                    company_id, 
                    destination_country.id, 
                    amount
                )
                
                if not held_balance:
                    raise Exception("Failed to hold balance for transaction")
                
                # Get current balance snapshot
                before_balance = balance.available_balance + balance.held_balance
                
                # Create transaction data dict
                tx_data = {
                    "company_id": company_id,
                    "pending_transaction_id": req.id,
                    "amount": amount,
                    "msisdn": req.msisdn,
                    "country_id": destination_country.id,
                    "balance_id": balance.id,
                    "partner_code": req.partner_code,
                    "status": "initiated",
                    "fee_amount": fee_info.get("fee_amount", Decimal('0')),
                    "net_amount": fee_info.get("net_amount", amount),
                    "before_balance": before_balance,
                    "after_balance": before_balance - amount,  # This will be updated on success
                }
                
                # Create specific transaction type based on your separate tables
                if req.transaction_type == "airtime":
                    transaction = AirtimePurchase(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    # Call Orange Money API for airtime purchase
                    response = om_client.purchase_credit(req.msisdn, float(amount))

                elif req.transaction_type == "deposit":
                    transaction = DepositTransaction(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    # Call Orange Money API for deposit
                    response = om_client.send_deposit_with_confirmation(req.msisdn, float(amount))

                elif req.transaction_type == "withdrawal":
                    transaction = WithdrawalTransaction(
                        sender=req.msisdn,
                        **tx_data
                    )
                    # Call Orange Money API for withdrawal
                    response = om_client.withdraw_cash(req.msisdn, float(amount))
                else:
                    raise Exception(f"Unknown transaction type: {req.transaction_type}")
                
                # Store gateway response
                if response and isinstance(response, dict):
                    transaction.gateway_response = response.get("response") or str(response)
                elif response:
                    transaction.gateway_response = str(response)
                
                db.add(transaction)
                db.commit()
                db.refresh(transaction)
                
                # Update pending request status
                req.status = "done"
                req.processed_at = datetime.now(timezone.utc)
                db.commit()

                # Send confirmation email asynchronously (uncomment when ready)
                # if transaction:
                #     send_transaction_confirmation_email.delay(transaction.id)
                
                logger.info(f"Successfully processed transaction {transaction.id} ({req.transaction_type}) for {req.msisdn}")

            except Exception as e:
                logger.error(f"Failed to process pending transaction {req.id}: {str(e)}")
                
                # Release held balance if it was held
                if 'held_balance' in locals() and held_balance and 'destination_country' in locals():
                    try:
                        balance_manager.release_balance(
                            db, 
                            company_id, 
                            destination_country.id, 
                            amount,
                            success=False  # Failed transaction
                        )
                    except Exception as balance_error:
                        logger.error(f"Failed to release balance for failed transaction {req.id}: {str(balance_error)}")
                
                # Update pending transaction status
                req.status = "failed"
                req.error_message = str(e)[:500]
                
                # If transaction was created, update its status too
                if transaction:
                    transaction.status = "failed"
                    transaction.error_message = str(e)
                    db.add(transaction)
                
                db.commit()

    except Exception as e:
        logger.error(f"Transaction queue processing failed: {str(e)}")
        # Retry the entire task if something went wrong
        self.retry(countdown=60)
    
    finally:
        db.close()