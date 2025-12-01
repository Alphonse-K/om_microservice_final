# import re

# def parse_transaction_email(body: str):
#     """
#     Extracts transaction_id, amount, msisdn, transaction_type.
#     """

#     patterns = {
#         "withdrawal": r"Retrait de (\d+) effectue\. Montant ([\d\.]+)",
#         "deposit": r"Depot vers (\d+) reussi\. Montant ([\d\.]+)",
#         "airtime": r"Rechargement reussi\. .*Montant .*: ([\d\.]+).*Other msisdn (\d+)",
#     }

#     # transaction ID (common to all)
#     txid_match = re.search(r"ID (?:Transaction|transaction)\s*[: ]\s*([A-Z0-9\.]+)", body)
#     transaction_id = txid_match.group(1) if txid_match else None

#     # withdrawal
#     m = re.search(patterns["withdrawal"], body)
#     if m:
#         msisdn, amount = m.groups()
#         return {
#             "transaction_type": "withdrawal",
#             "msisdn": msisdn,
#             "amount": float(amount),
#             "transaction_id": transaction_id
#         }

#     # deposit
#     m = re.search(patterns["deposit"], body)
#     if m:
#         msisdn, amount = m.groups()
#         return {
#             "transaction_type": "deposit",
#             "msisdn": msisdn,
#             "amount": float(amount),
#             "transaction_id": transaction_id
#         }

#     # airtime
#     m = re.search(patterns["airtime"], body)
#     if m:
#         amount, msisdn = m.groups()
#         return {
#             "transaction_type": "airtime",
#             "msisdn": msisdn,
#             "amount": float(amount),
#             "transaction_id": transaction_id
#         }

#     return {}
import re

def parse_transaction_email(body: str):
    """
    Parse the transaction email body and extract:
    - transaction_id
    - msisdn
    - amount
    - transaction_type
    - status ('success' or 'failed')
    """

    body_l = body.lower()

    # Patterns for each transaction type
    patterns = {
        "withdrawal": r"retrait de (\d+) effectue\. montant ([\d\.]+)",
        "deposit": r"depot vers (\d+) reussi\. montant ([\d\.]+)",
        "airtime": r"rechargement reussi\. montant de la transaction [: ]*([\d\.]+).*other msisdn (\d+)",
    }

    # Transaction ID (case insensitive)
    txid_match = re.search(
        r"id\s*(?:transaction)?\s*[: ]\s*([A-Z0-9\.]+)",
        body,
        flags=re.IGNORECASE
    )
    transaction_id = txid_match.group(1) if txid_match else None

    # Detect failure words
    failure_patterns = [
        r"echec", r"échoué", r"failed", r"not completed",
        r"unsuccessful", r"cancelled", r"rejet", r"refuse",
    ]
    if any(re.search(p, body_l) for p in failure_patterns):
        return {
            "transaction_type": None,
            "status": "failed",
            "transaction_id": transaction_id
        }

    # Withdrawal
    m = re.search(patterns["withdrawal"], body_l)
    if m:
        msisdn, amount = m.groups()
        return {
            "transaction_type": "withdrawal",
            "msisdn": msisdn,
            "amount": float(amount),
            "transaction_id": transaction_id,
            "status": "success"
        }

    # Deposit
    m = re.search(patterns["deposit"], body_l)
    if m:
        msisdn, amount = m.groups()
        return {
            "transaction_type": "deposit",
            "msisdn": msisdn,
            "amount": float(amount),
            "transaction_id": transaction_id,
            "status": "success"
        }

    # Airtime
    m = re.search(patterns["airtime"], body_l)
    if m:
        amount, msisdn = m.groups()
        return {
            "transaction_type": "airtime",
            "msisdn": msisdn,
            "amount": float(amount),
            "transaction_id": transaction_id,
            "status": "success"
        }

    # If none matched, consider failed
    return {
        "transaction_type": None,
        "status": "failed",
        "transaction_id": transaction_id
    }
