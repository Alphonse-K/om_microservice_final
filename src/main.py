from src.core.database import Base, engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

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

# UPLOAD_DIR = "/app/uploads/slips"

# os.makedirs(UPLOAD_DIR, exist_ok=True)

# app.mount("/procurements/slip", StaticFiles(directory=UPLOAD_DIR), name="procurement_slips")

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



# seed_initial_emails_multi.py
# import logging
# from datetime import datetime, timezone
# from src.core.database import SessionLocal
# from src.services.gmail_service import fetch_recent_emails
# from src.services.email_service import create_email, get_email_by_message_id
# from src.utils.parser import parse_transaction_email

# # --- CONFIG: list of Gmail accounts and their tokens ---
# GMAIL_ACCOUNTS = [
#     {"label": "airtime", "token_path": "/app/credentials/airtime_token.json"},
#     {"label": "cashin/cashout", "token_path": "/app/credentials/withdrawal_token.json"},
# ]

# NUM_EMAILS = 2  # fetch the 2 most recent emails per account

# # --- LOGGER ---
# logger = logging.getLogger("seed_emails")
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
# handler.setFormatter(formatter)
# logger.addHandler(handler)

# def fetch_and_store_emails(label: str, token_path: str):
#     db = SessionLocal()
#     try:
#         emails = fetch_recent_emails(token_path, max_results=NUM_EMAILS)
#         logger.info(f"[{label}] Fetched {len(emails)} emails from Gmail.")

#         for msg in emails:
#             msg_id = msg.get("id")
#             if get_email_by_message_id(db, msg_id):
#                 logger.info(f"[{label}] Skipping duplicate email {msg_id}")
#                 continue

#             body_text = msg.get("body") or ""
#             # detect type from body content
#             body_lower = body_text.lower()
#             if "retrait de" in body_lower:
#                 detected_type = "cashout"
#             elif "depot vers" in body_lower:
#                 detected_type = "cashin"
#             elif "rechargement" in body_lower:
#                 detected_type = "airtime"
#             else:
#                 detected_type = "unknown"

#             parsed = parse_transaction_email(body_text)

#             payload = {
#                 "gmail_account": detected_type,
#                 "message_id": msg_id,
#                 "subject": msg.get("subject"),
#                 "sender": msg.get("sender"),
#                 "body": body_text,
#                 "received_at": datetime.fromtimestamp(msg.get("internalDate", 0), tz=timezone.utc),
#                 "parsed_transaction_id": parsed.get("transaction_id"),
#             }

#             try:
#                 email_obj = create_email(db, payload)
#                 logger.info(f"[{label}] Inserted email {msg_id} into database.")
#             except Exception as db_err:
#                 logger.error(f"[{label}] Failed to insert email {msg_id}: {db_err}")

#     finally:
#         db.close()
#         logger.info(f"[{label}] DB session closed.")

# def main():
#     for account in GMAIL_ACCOUNTS:
#         fetch_and_store_emails(account["label"], account["token_path"])

# if __name__ == "__main__":
#     main()





