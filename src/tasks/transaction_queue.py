# src/tasks/transaction_queue.py
import logging
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.worker_app import celery_app
from src.core.database import SessionLocal
from src.models.transaction import (
    PendingTransaction,
    CompanyCountryBalance,
    FeeConfig,
    Country,
    DepositTransaction,
    WithdrawalTransaction,
    AirtimePurchase
)
from src.services.neogate_client import NeoGateTG400Client

MAX_REQUESTS_PER_MINUTE = 6
om_client = NeoGateTG400Client()

logger = logging.getLogger("transaction_queue")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# ----------------- BALANCE MANAGER ----------------- #
class BalanceManager:
    @staticmethod
    def hold_balance(db: Session, company_id: int, country_id: int, amount: Decimal):
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).with_for_update().first()

        if not balance:
            raise Exception(f"No balance found for company {company_id} in country {country_id}")
        if balance.available_balance < amount:
            raise Exception(f"Insufficient available balance. Available: {balance.available_balance}, Required: {amount}")

        balance.available_balance -= amount
        balance.held_balance += amount
        db.add(balance)
        db.commit()
        db.refresh(balance)
        return balance

    @staticmethod
    def release_balance(db: Session, company_id: int, country_id: int, amount: Decimal, success: bool = False):
        balance = db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).with_for_update().first()

        if not balance:
            logger.warning(f"No balance found for company {company_id} in country {country_id} to release")
            return False

        balance.held_balance = max(Decimal('0'), balance.held_balance - amount)
        if not success:
            balance.available_balance += amount

        db.add(balance)
        db.commit()
        db.refresh(balance)
        return True


# ----------------- FEE CALCULATOR ----------------- #
class FeeCalculator:
    @staticmethod
    def calculate_fee(db: Session, destination_country_id: int, transaction_type, amount: Decimal) -> dict:
        fee_config: FeeConfig = db.query(FeeConfig).filter(
            FeeConfig.destination_country_id == destination_country_id,
            FeeConfig.transaction_type == transaction_type,
            FeeConfig.is_active == True
        ).first()

        if not fee_config:
            return {"fee_amount": Decimal('0'), "net_amount": amount}

        if fee_config.fee_type == "flat":
            fee_amount = Decimal(fee_config.flat_fee)
        elif fee_config.fee_type == "percent":
            fee_amount = (amount * Decimal(fee_config.percent_fee)) / Decimal('100')
        else:
            fee_amount = Decimal('0')

        if fee_config.min_fee and fee_amount < Decimal(fee_config.min_fee):
            fee_amount = Decimal(fee_config.min_fee)
        if fee_config.max_fee and fee_amount > Decimal(fee_config.max_fee):
            fee_amount = Decimal(fee_config.max_fee)

        return {"fee_amount": fee_amount, "net_amount": amount - fee_amount}


# ----------------- COUNTRY ROUTER ----------------- #
class CountryRouter:
    COUNTRY_CODES = {
        '221': 'SN', '224': 'GN', '223': 'ML', '225': 'CI', '226': 'BF'
    }

    @staticmethod
    def get_destination_country(db: Session, country_iso: str):
        if not country_iso:
            return None
        return db.query(Country).filter(
            Country.iso_code == country_iso.upper(),
            Country.is_active == True
        ).first()

    @staticmethod
    def get_country_from_msisdn(db: Session, msisdn: str):
        clean_msisdn = msisdn.lstrip('+')
        for code, iso in CountryRouter.COUNTRY_CODES.items():
            if clean_msisdn.startswith(code):
                return db.query(Country).filter(Country.iso_code == iso, Country.is_active == True).first()
        return db.query(Country).filter(Country.iso_code == 'SN').first()


# ----------------- PROCESS TRANSACTION QUEUE ----------------- #
@celery_app.task(bind=True, max_retries=3, name='src.tasks.transaction_queue.process_transaction_queue')
def process_transaction_queue(self):
    db: Session = SessionLocal()
    balance_manager = BalanceManager()
    fee_calculator = FeeCalculator()
    country_router = CountryRouter()

    try:
        pending_requests = db.query(PendingTransaction).filter(
            PendingTransaction.status == "pending"
        ).order_by(PendingTransaction.created_at.asc()).limit(MAX_REQUESTS_PER_MINUTE).all()

        for req in pending_requests:
            transaction = None
            held_amount = None
            destination_country = None

            try:
                logger.info(f"Processing pending transaction id={req.id} type={req.transaction_type} msisdn={req.msisdn}")
                req.status = "processing"
                db.add(req)
                db.commit()

                req_type = (req.transaction_type or "").strip().lower()
                company_id = req.company_id

                # Determine destination country
                if req.country_iso:
                    destination_country = country_router.get_destination_country(db, req.country_iso)
                if not destination_country:
                    destination_country = country_router.get_country_from_msisdn(db, req.msisdn)
                if not destination_country:
                    raise Exception(f"Cannot determine country for MSISDN {req.msisdn}")

                # Company balance
                balance = db.query(CompanyCountryBalance).filter(
                    CompanyCountryBalance.company_id == company_id,
                    CompanyCountryBalance.country_id == destination_country.id
                ).first()
                if not balance:
                    raise Exception(f"No balance for company {company_id} in {destination_country.iso_code}")

                amount_decimal = Decimal(str(req.amount))

                # Calculate fees
                fee_info = fee_calculator.calculate_fee(
                    db,
                    destination_country_id=destination_country.id,
                    transaction_type=req_type,
                    amount=amount_decimal
                )

                # Hold full amount only for debit-type transactions
                if req_type in ("cashin", "airtime"):
                    held_amount = amount_decimal
                    balance_manager.hold_balance(db, company_id, destination_country.id, held_amount)

                tx_data = {
                    "company_id": company_id,
                    "pending_transaction_id": req.id,
                    "amount": amount_decimal,
                    "country_id": destination_country.id,
                    "balance_id": balance.id,
                    "partner_id": req.partner_id,
                    "service_partner_id": None,
                    "status": "initiated",
                    "fee_amount": fee_info["fee_amount"],
                    "net_amount": amount_decimal,
                    "before_balance": balance.available_balance + balance.held_balance,
                    "after_balance": balance.available_balance + balance.held_balance,
                }

                # Convert amount to int for gateway
                gateway_amount = int(amount_decimal)

                # Transaction Routing
                if req_type == "airtime":
                    transaction = AirtimePurchase(recipient=req.msisdn, **tx_data)
                    response = om_client.purchase_credit(req.msisdn, gateway_amount)

                elif req_type == "cashin":
                    transaction = DepositTransaction(recipient=req.msisdn, **tx_data)
                    response = om_client.send_deposit_with_confirmation(req.msisdn, gateway_amount)

                elif req_type == "cashout":
                    transaction = WithdrawalTransaction(sender=req.msisdn, **tx_data)
                    response = om_client.withdraw_cash(req.msisdn, gateway_amount)

                else:
                    raise Exception(f"Unknown transaction type '{req.transaction_type}'")

                # Save transaction response
                if response:
                    if isinstance(response, dict):
                        transaction.gateway_response = response.get("response") or str(response)
                        transaction.gateway_transaction_id = response.get("transaction_id")
                    else:
                        transaction.gateway_response = str(response)

                db.add(transaction)
                db.commit()
                db.refresh(transaction)

                # Finalize pending transaction
                req.status = "done"
                req.processed_at = datetime.now(timezone.utc)
                db.add(req)
                db.commit()

                logger.info(f"Processed transaction {transaction.id} (pending_id={req.id}) - amount={amount_decimal} fee={fee_info['fee_amount']}")

            except Exception as e:
                logger.error(f"Failed transaction id={req.id if req else 'N/A'}: {str(e)}", exc_info=True)
                # Release held amount if applicable
                if held_amount and destination_country:
                    try:
                        balance_manager.release_balance(db, company_id, destination_country.id, held_amount, success=False)
                    except Exception as release_err:
                        logger.error(f"Failed to release held balance for pending id={getattr(req, 'id', 'N/A')}: {release_err}")

                # Mark as failed
                try:
                    req.status = "failed"
                    req.error_message = str(e)[:500]
                    db.add(req)

                    if transaction:
                        transaction.status = "failed"
                        transaction.error_message = str(e)[:1000]
                        db.add(transaction)

                    db.commit()
                except Exception as persist_err:
                    logger.error(f"Failed to persist failure for pending id={getattr(req, 'id', 'N/A')}: {persist_err}")
                    db.rollback()

    except Exception as e:
        logger.error(f"Transaction queue processing failed: {str(e)}", exc_info=True)
        try:
            self.retry(countdown=60)
        except Exception:
            logger.error("Celery retry failed or not allowed")
    finally:
        db.close()
