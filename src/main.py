from src.core.database import Base, engine
from fastapi import FastAPI
from src.routes.transaction import (
    transaction_router, 
    country_router, 
    user_router,
    fee_router, 
    procurement_router,
    company_router,
    finance_router
)
from src.routes.auth import auth_router  # If you have auth routes
from src.routes.emails import email_router


app = FastAPI(title="CashMoov API", version="1.0.0")

Base.metadata.create_all(bind=engine)

# Include all routers
app.include_router(auth_router)  
app.include_router(user_router)
app.include_router(company_router)  
app.include_router(country_router)
app.include_router(procurement_router)
app.include_router(fee_router)
app.include_router(finance_router)
app.include_router(transaction_router)
app.include_router(email_router) 


@app.get("/")
def root():
    return {"message": "CashMoov API is running"}





