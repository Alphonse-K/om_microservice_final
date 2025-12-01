# """
# Run this once to generate tokens for both Gmail accounts.
# It reads credentials paths from .env and writes tokens to token paths.
# """

# import os
# from dotenv import load_dotenv
# from google_auth_oauthlib.flow import InstalledAppFlow

# load_dotenv()

# SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# def generate_token(credentials_path: str, token_output: str):
#     flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
#     creds = flow.run_local_server(port=0)
#     os.makedirs(os.path.dirname(token_output), exist_ok=True)
#     with open(token_output, "w") as f:
#         f.write(creds.to_json())
#     print(f"saved token to {token_output}")

# if __name__ == "__main__":
#     withdrawal_cred = os.getenv("GMAIL_WITHDRAWAL_CREDENTIALS")
#     withdrawal_token = os.getenv("GMAIL_WITHDRAWAL_TOKEN")

#     print("Generating token for withdrawal account...")
#     generate_token(withdrawal_cred, withdrawal_token)

"""
Run this script manually to generate OAuth tokens
for BOTH Gmail accounts (withdrawal/deposit + airtime).

It reads paths from .env and saves generated tokens to disk.
"""

import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# Gmail read-only access
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def generate_token(credentials_path: str, token_output: str, label: str):
    if not credentials_path:
        print(f"[SKIP] No credentials path for: {label}")
        return

    print(f"\n=== Generating token for {label} ===")

    if not os.path.exists(credentials_path):
        print(f"[ERROR] Credentials file not found: {credentials_path}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    # Ensure directory exists
    os.makedirs(os.path.dirname(token_output), exist_ok=True)

    with open(token_output, "w") as f:
        f.write(creds.to_json())

    print(f"[OK] Saved token → {token_output}")


if __name__ == "__main__":
    # ------------------------------
    # Withdrawal/Deposit Gmail
    # ------------------------------
    withdrawal_cred = os.getenv("GMAIL_WITHDRAWAL_CREDENTIALS")
    withdrawal_token = os.getenv("GMAIL_WITHDRAWAL_TOKEN")

    generate_token(
        credentials_path=withdrawal_cred,
        token_output=withdrawal_token,
        label="WITHDRAWAL/DEPOSIT Gmail"
    )

    # ------------------------------
    # Airtime Gmail
    # ------------------------------
    airtime_cred = os.getenv("GMAIL_AIRTIME_CREDENTIALS")
    airtime_token = os.getenv("GMAIL_AIRTIME_TOKEN")

    generate_token(
        credentials_path=airtime_cred,
        token_output=airtime_token,
        label="AIRTIME Gmail"
    )

    print("\nFinished generating all tokens.\n")
