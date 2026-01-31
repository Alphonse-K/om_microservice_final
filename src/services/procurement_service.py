from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import logging

from src.models.transaction import (
    Procurement, 
    CompanyCountryBalance, 
    Company, 
    Country,
    ProcurementStatus,
    User
)
from src.schemas.transaction import ProcurementCreate, ProcurementAction

logger = logging.getLogger(__name__)

class ProcurementService:
    
    @staticmethod
    def create_procurement(
        db: Session,
        procurement_data: ProcurementCreate,
        initiated_by_user_id: int,
        file_path: str = None
    ) -> Procurement:
        """
        Create a new procurement.
        Balance is NOT updated until procurement is approved.
        """
        try:
            # Check if slip number already exists
            print(f"Checking slip_number: '{procurement_data.slip_number}'")
            existing = db.query(Procurement).filter(
                Procurement.slip_number == procurement_data.slip_number
            ).first()
            print(f"Existing: {existing}")
            data = procurement_data.model_dump(exclude={"slip_file_path"})

            procurement = Procurement(
                **data,
                slip_file_path=file_path,
                status=ProcurementStatus.PENDING,
                initiated_by=initiated_by_user_id,
                initiation_date=datetime.now(timezone.utc)
            )

            db.add(procurement)
            db.commit()
            db.refresh(procurement)

            logger.info(f"Procurement created: ID={procurement.id}, Amount={procurement.amount}")
            return procurement

        except IntegrityError as e:
            db.rollback()
            if "slip_number" in str(e):
                raise ValueError(f"Slip number '{procurement_data.slip_number}' already exists")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating procurement: {e}")
            raise

    @staticmethod
    def approve_procurement(
        db: Session,
        procurement_id: int,
        validated_by_user_id: int,
        notes: str = None
    ) -> tuple[bool, str, Procurement]:
        """
        Approve a procurement and update the country's available balance
        
        Returns: (success, message, procurement)
        """
        try:
            # Get procurement
            procurement = db.query(Procurement).filter(
                Procurement.id == procurement_id,
                Procurement.status == ProcurementStatus.PENDING
            ).first()
            
            if not procurement:
                return False, f"Pending procurement with ID {procurement_id} not found", None
            
            # Get or create balance record
            balance = db.query(CompanyCountryBalance).filter(
                CompanyCountryBalance.company_id == procurement.company_id,
                CompanyCountryBalance.country_id == procurement.country_id
            ).first()
            
            if not balance:
                # Create new balance record if it doesn't exist
                company = db.query(Company).filter(Company.id == procurement.company_id).first()
                country = db.query(Country).filter(Country.id == procurement.country_id).first()
                
                if not company or not country:
                    return False, "Company or country not found", None
                
                # Generate partner code
                partner_code = f"{company.name[:7].upper()}-{country.iso_code}"
                
                balance = CompanyCountryBalance(
                    company_id=procurement.company_id,
                    country_id=procurement.country_id,
                    partner_code=partner_code,
                    available_balance=0,
                    held_balance=0
                )
                db.add(balance)
                db.commit()
                db.refresh(balance)
            
            # Link procurement to balance
            procurement.balance_id = balance.id
            
            # Update procurement status
            procurement.status = ProcurementStatus.SUCCESS
            procurement.validation_date = datetime.now(timezone.utc)
            procurement.validated_by = validated_by_user_id
            
            if notes:
                if procurement.notes:
                    procurement.notes += f"\n[Approval]: {notes}"
                else:
                    procurement.notes = notes
            
            # Update balance - add procurement amount to available balance
            balance.available_balance += procurement.amount
            
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement approved: ID={procurement.id}, Amount={procurement.amount}, New Balance={balance.available_balance}")
            
            return True, "Procurement approved and balance updated", procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error approving procurement {procurement_id}: {str(e)}")
            return False, f"Internal error: {str(e)}", None
    
    @staticmethod
    def reject_procurement(
        db: Session,
        procurement_id: int,
        validated_by_user_id: int,
        notes: str = None
    ) -> tuple[bool, str, Procurement]:
        """Reject a procurement"""
        try:
            procurement = db.query(Procurement).filter(
                Procurement.id == procurement_id,
                Procurement.status == ProcurementStatus.PENDING
            ).first()
            
            if not procurement:
                return False, f"Pending procurement with ID {procurement_id} not found", None
            
            procurement.status = ProcurementStatus.FAILED
            procurement.validation_date = datetime.now(timezone.utc)
            procurement.validated_by = validated_by_user_id
            
            if notes:
                if procurement.notes:
                    procurement.notes += f"\n[Rejection]: {notes}"
                else:
                    procurement.notes = notes
            
            db.commit()
            db.refresh(procurement)
            
            logger.info(f"Procurement rejected: ID={procurement_id}")
            
            return True, "Procurement rejected", procurement
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error rejecting procurement {procurement_id}: {str(e)}")
            return False, f"Internal error: {str(e)}", None
    
    @staticmethod
    def get_procurements(
        db: Session,
        company_id: int = None,
        country_id: int = None,
        status: ProcurementStatus = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[Procurement], int]:
        """Get procurements with filtering and pagination"""
        query = db.query(Procurement)
        
        if company_id:
            query = query.filter(Procurement.company_id == company_id)
        
        if country_id:
            query = query.filter(Procurement.country_id == country_id)
        
        if status:
            query = query.filter(Procurement.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        procurements = query.order_by(
            Procurement.initiation_date.desc()
        ).offset(offset).limit(limit).all()
        
        return procurements, total
    
    @staticmethod
    def get_procurement_summary(db: Session, company_id: int = None) -> dict:
        """Get procurement summary"""
        from sqlalchemy import func
        
        query = db.query(
            Procurement.status,
            func.count(Procurement.id).label('count'),
            func.sum(Procurement.amount).label('total_amount')
        )
        
        if company_id:
            query = query.filter(Procurement.company_id == company_id)
        
        result = query.group_by(Procurement.status).all()
        
        summary = {
            status.value: {
                'count': count,
                'total_amount': float(total_amount) if total_amount else 0.0
            }
            for status, count, total_amount in result
        }
        
        return summary