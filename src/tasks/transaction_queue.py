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
    Country, Company,
    DepositTransaction, WithdrawalTransaction, AirtimePurchase
)
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
    def hold_balance(db: Session, company_id: int, country_id: int, amount: Decimal):
        """Hold balance for a transaction"""
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).first()
        
        if not balance:
            raise Exception(f"No balance found for company {company_id} in country {country_id}")
        
        if balance.available_balance < amount:
            raise Exception(f"Insufficient available balance. Available: {balance.available_balance}, Required: {amount}")
        
        # Hold the funds
        balance.available_balance -= amount
        balance.held_balance += amount
        
        db.commit()
        return balance

    @staticmethod
    def release_balance(db: Session, company_id: int, country_id: int, amount: Decimal, success: bool = False):
        """Release held balance - success=False means return to available"""
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).first()
        
        if not balance:
            return False
            
        # Reduce held balance
        balance.held_balance -= amount
        
        # If transaction failed, return to available balance
        if not success:
            balance.available_balance += amount
        
        db.commit()
        return True


class FeeCalculator:
    @staticmethod
    def calculate_fee(db: Session, source_country_id: int, destination_country_id: int, amount: Decimal) -> dict:
        """Calculate fees for a transaction"""
        
        fee_config = db.query(FeeConfig).filter(
            FeeConfig.source_country_id == source_country_id,
            FeeConfig.destination_country_id == destination_country_id,
            FeeConfig.is_active == True
        ).first()
        
        if not fee_config:
            return {
                "fee_amount": Decimal('0'), 
                "net_amount": amount
            }
        
        # Calculate fee
        if fee_config.fee_type == "flat":
            fee_amount = fee_config.flat_fee
        elif fee_config.fee_type == "percent":
            fee_amount = (amount * fee_config.percent_fee) / Decimal('100')
        elif fee_config.fee_type == "mixed":
            fee_amount = fee_config.flat_fee + (amount * fee_config.percent_fee) / Decimal('100')
        else:
            fee_amount = Decimal('0')
        
        # Apply min/max
        if fee_config.min_fee and fee_amount < fee_config.min_fee:
            fee_amount = fee_config.min_fee
            
        if fee_config.max_fee and fee_amount > fee_config.max_fee:
            fee_amount = fee_config.max_fee
        
        net_amount = amount - fee_amount
        
        return {
            "fee_amount": fee_amount,
            "net_amount": net_amount
        }


class CountryRouter:
    @staticmethod
    def get_destination_country(db: Session, country_iso: str):
        """Get country by ISO code"""
        if not country_iso:
            return None
            
        return db.query(Country).filter(
            Country.iso_code == country_iso.upper(),
            Country.is_active == True
        ).first()
    
    @staticmethod
    def get_country_from_msisdn(db: Session, msisdn: str):
        """Determine country from MSISDN"""
        # Simple implementation - adjust based on your needs
        clean_msisdn = msisdn.lstrip('+')
        
        # Country code mappings
        country_codes = {
            '221': 'SN',  # Senegal
            '224': 'GN',  # Guinea
            '223': 'ML',  # Mali
            '225': 'CI',  # Ivory Coast
            '226': 'BF',  # Burkina Faso
        }
        
        for code, iso in country_codes.items():
            if clean_msisdn.startswith(code):
                return db.query(Country).filter(
                    Country.iso_code == iso,
                    Country.is_active == True
                ).first()
        
        # Default to Senegal
        return db.query(Country).filter(Country.iso_code == 'SN').first()

@celery_app.task(bind=True, max_retries=3, name='src.tasks.transaction_queue.process_transaction_queue')
def process_transaction_queue(self):
    """Process pending transactions"""
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
                # Update status
                req.status = "processing"
                db.commit()

                company_id = req.company_id
                
                # Determine destination country
                destination_country = None
                if req.country_iso:
                    destination_country = country_router.get_destination_country(db, req.country_iso)
                
                if not destination_country:
                    destination_country = country_router.get_country_from_msisdn(db, req.msisdn)
                
                if not destination_country:
                    raise Exception(f"Could not determine country for MSISDN: {req.msisdn}")
                
                # Get company balance
                balance = db.query(CompanyCountryBalance).filter(
                    CompanyCountryBalance.company_id == company_id,
                    CompanyCountryBalance.country_id == destination_country.id
                ).first()
                
                if not balance:
                    raise Exception(f"No balance for company {company_id} in {destination_country.iso_code}")

                amount = Decimal(str(req.amount))
                
                # Calculate fees - for reconciliation only
                fee_info = fee_calculator.calculate_fee(
                    db, 
                    source_country_id=destination_country.id,
                    destination_country_id=destination_country.id,
                    amount=amount
                )
                
                # IMPORTANT: For ALL transaction types, we hold and send the FULL amount
                # The fee is calculated for reconciliation but NOT deducted from the amount sent
                
                # Check if balance is sufficient for the FULL amount
                if balance.available_balance < amount:
                    raise Exception(f"Insufficient balance. Available: {balance.available_balance}, Required: {amount}")
                
                # Hold the FULL amount (no fee deduction)
                hold_amount = amount
                
                # Hold balance
                held_balance = balance_manager.hold_balance(
                    db, 
                    company_id, 
                    destination_country.id, 
                    hold_amount
                )
                
                # Get balance snapshot
                before_balance = balance.available_balance + balance.held_balance
                
                # Common transaction data
                tx_data = {
                    "company_id": company_id,
                    "pending_transaction_id": req.id,
                    "amount": amount,  # FULL amount
                    "msisdn": req.msisdn,
                    "country_id": destination_country.id,
                    "balance_id": balance.id,
                    "partner_code": req.partner_code,
                    "status": "initiated",
                    "fee_amount": fee_info["fee_amount"],  # For reconciliation only
                    "net_amount": amount,  # Same as amount (no fee deduction for now)
                    "before_balance": before_balance,
                    "after_balance": before_balance - hold_amount,  # Based on FULL amount
                }
                
                # Create specific transaction type and call NeoGate with FULL amount
                if req.transaction_type == "airtime":
                    transaction = AirtimePurchase(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    # Send FULL amount to NeoGate
                    response = om_client.purchase_credit(req.msisdn, float(amount))
                    logger.info(f"Sending airtime: {amount} to {req.msisdn} (fee: {fee_info['fee_amount']} for reconciliation)")

                elif req.transaction_type == "deposit":
                    transaction = DepositTransaction(
                        recipient=req.msisdn,
                        **tx_data
                    )
                    # Send FULL amount to NeoGate
                    response = om_client.send_deposit_with_confirmation(req.msisdn, float(amount))
                    logger.info(f"Sending deposit: {amount} to {req.msisdn} (fee: {fee_info['fee_amount']} for reconciliation)")

                elif req.transaction_type == "withdrawal":
                    transaction = WithdrawalTransaction(
                        sender=req.msisdn,
                        **tx_data
                    )
                    # For withdrawal: collect FULL amount from customer
                    # IMPORTANT: The fee is OUR revenue, not deducted from customer
                    response = om_client.withdraw_cash(req.msisdn, float(amount))
                    logger.info(f"Withdrawing: {amount} from {req.msisdn} (fee: {fee_info['fee_amount']} is our revenue)")
                else:
                    raise Exception(f"Unknown transaction type: {req.transaction_type}")
                
                # Store response
                if response:
                    if isinstance(response, dict):
                        transaction.gateway_response = response.get("response") or str(response)
                        transaction.gateway_transaction_id = response.get("transaction_id")
                    else:
                        transaction.gateway_response = str(response)
                
                db.add(transaction)
                db.commit()
                
                req.status = "done"
                req.processed_at = datetime.now(timezone.utc)
                db.commit()
                
                logger.info(f"Processed transaction {transaction.id} ({req.transaction_type}) - Amount: {amount}, Fee: {fee_info['fee_amount']}")

            except Exception as e:
                logger.error(f"Failed to process transaction {req.id if req else 'N/A'}: {str(e)}")
                
                # Release held balance if applicable
                if 'hold_amount' in locals() and 'destination_country' in locals():
                    try:
                        balance_manager.release_balance(
                            db, 
                            company_id, 
                            destination_country.id, 
                            hold_amount,
                            success=False
                        )
                    except Exception as balance_error:
                        logger.error(f"Failed to release balance: {str(balance_error)}")
                
                # Update status
                req.status = "failed"
                req.error_message = str(e)[:500]
                
                if transaction:
                    transaction.status = "failed"
                    transaction.error_message = str(e)
                    db.add(transaction)
                
                db.commit()

    except Exception as e:
        logger.error(f"Transaction queue processing failed: {str(e)}")
        self.retry(countdown=60)
    
    finally:
        db.close()