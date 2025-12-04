from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from src.models.transaction import CompanyCountryBalance, Company, Country

logger = logging.getLogger(__name__)

class FinanceService:
    
    @staticmethod
    def get_company_balance(
        db: Session,
        company_id: int,
        country_id: int
    ):
        """Get company's balance for a specific country"""
        return db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id,
            CompanyCountryBalance.country_id == country_id
        ).first()
    
    @staticmethod
    def get_all_company_balances(db: Session, company_id: int):
        """Get all country balances for a company"""
        return db.query(CompanyCountryBalance).filter(
            CompanyCountryBalance.company_id == company_id
        ).all()
    
    @staticmethod
    def update_balance(
        db: Session,
        company_id: int,
        country_id: int,
        amount: Decimal,
        operation: str  # "add", "deduct", "hold", "release"
    ) -> tuple[bool, str]:
        """Update company balance"""
        try:
            balance = FinanceService.get_company_balance(db, company_id, country_id)
            
            if not balance:
                return False, f"No balance found for company {company_id} in country {country_id}"
            
            if operation == "add":
                balance.available_balance += amount
                message = f"Added {amount} to available balance"
            
            elif operation == "deduct":
                if balance.available_balance < amount:
                    return False, f"Insufficient available balance. Available: {balance.available_balance}"
                balance.available_balance -= amount
                message = f"Deducted {amount} from available balance"
            
            elif operation == "hold":
                if balance.available_balance < amount:
                    return False, f"Insufficient available balance to hold. Available: {balance.available_balance}"
                balance.available_balance -= amount
                balance.held_balance += amount
                message = f"Held {amount} for transaction"
            
            elif operation == "release":
                if balance.held_balance < amount:
                    return False, f"Insufficient held balance to release. Held: {balance.held_balance}"
                balance.held_balance -= amount
                balance.available_balance += amount
                message = f"Released {amount} from held balance"
            
            else:
                return False, f"Invalid operation: {operation}"
            
            db.commit()
            return True, message
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating balance: {str(e)}")
            return False, f"Internal error: {str(e)}"
    
    @staticmethod
    def get_balance_summary(db: Session, company_id: int):
        """Get comprehensive balance summary for a company"""
        balances = FinanceService.get_all_company_balances(db, company_id)
        
        total_available = Decimal('0')
        total_held = Decimal('0')
        total_effective = Decimal('0')
        
        country_details = []
        
        for balance in balances:
            total_available += Decimal(str(balance.available_balance))
            total_held += Decimal(str(balance.held_balance))
            total_effective += Decimal(str(balance.effective_balance))
            
            # Get country name
            country = db.query(Country).filter(Country.id == balance.country_id).first()
            country_name = country.name if country else f"Country {balance.country_id}"
            
            country_details.append({
                "country_id": balance.country_id,
                "country_name": country_name,
                "partner_code": balance.partner_code,
                "available_balance": float(balance.available_balance),
                "held_balance": float(balance.held_balance),
                "effective_balance": float(balance.effective_balance)
            })
        
        return {
            "company_id": company_id,
            "total_available": float(total_available),
            "total_held": float(total_held),
            "total_effective": float(total_effective),
            "country_balances": country_details
        }