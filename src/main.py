from fastapi import FastAPI
from src.core.database import Base, engine
from src.routes.transaction import (
    transaction_router, 
    country_router, 
    user_router, 
    balance_router, 
    fee_router, 
    procurement_router
)
from src.routes.auth import auth_router
from src.routes.emails import email_router

app = FastAPI(title="OM via PROXY API")


Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(email_router)
app.include_router(transaction_router)
app.include_router(country_router)
app.include_router(user_router)
app.include_router(balance_router)
app.include_router(fee_router)
app.include_router(procurement_router)


@app.get('/')
async def entry_point():
    return {"Message": "Welcome to this Proxy API"}