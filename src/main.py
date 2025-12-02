from src.core.database import Base, engine
from fastapi import FastAPI
from src.routes.transaction import (
    transaction_router, 
    country_router, 
    user_router,
    balance_router, 
    fee_router, 
    procurement_router,
    company_router  # Add this import
)
from src.routes.auth import auth_router  # If you have auth routes
from src.routes.emails import email_router


app = FastAPI(title="CashMoov API", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Include all routers
app.include_router(auth_router)  # If you have auth
app.include_router(user_router)
app.include_router(company_router)  # Add this line
app.include_router(country_router)
app.include_router(balance_router)
app.include_router(fee_router)
app.include_router(procurement_router)
app.include_router(transaction_router)
app.include_router(email_router)  # If you have auth


@app.get("/")
def root():
    return {"message": "CashMoov API is running"}


# # scripts/create_admin.py
# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from sqlalchemy.orm import Session
# from src.core.database import SessionLocal, engine
# from src.models.transaction import User, Company
# from src.core.security import SecurityUtils

# def create_admin_user():
#     db = SessionLocal()
#     try:
#         # First, check if company exists
#         company = db.query(Company).filter(Company.name == "System Admin").first()
#         if not company:
#             # Create a system company
#             company = Company(              
#                 name="CASHMOOV",
#                 email="contact@cashmoov.net",
#                 phone="622481010",
#                 address="Conakry - Kipe",
#                 is_active=True,
#             )
            
#             db.add(company)
#             db.commit()
#             db.refresh(company)
#             print(f"Created company: {company.name}")
        
#         # Check if admin user exists
#         admin = db.query(User).filter(User.email == "contact@cashmoov.net").first()
#         if not admin:
#             # Create admin user
#             admin = User(
#                 name="System Administrator",
#                 email="admin@cashmoov.net",
#                 password_hash=SecurityUtils.hash_password("Admin123"),  # Change this password!
#                 role="admin",
#                 company_id=company.id,
#                 is_active=True
#             )
#             db.add(admin)
#             db.commit()
#             print("✅ Admin user created successfully!")
#             print(f"Email: admin@cashmoov.com")
#             print(f"Password: Admin123!")  # Change immediately after first login
#         else:
#             print("ℹ️ Admin user already exists")
            
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
#         db.rollback()
#     finally:
#         db.close()

# if __name__ == "__main__":
#     create_admin_user()