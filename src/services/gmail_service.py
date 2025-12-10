import base64
import quopri
from email import message_from_bytes
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from src.core.config import settings
from bs4 import BeautifulSoup
import re



SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def _load_credentials(token_path: str) -> Credentials:
    return Credentials.from_authorized_user_file(token_path, SCOPES)

def build_service_for_token(token_path: str):
    creds = _load_credentials(token_path)
    service = build('gmail', 'v1', credentials=creds)
    return service

def _extract_body(payload: dict) -> str:
    if not payload:
        return ""

    if 'body' in payload and payload['body'].get('data'):
        try:
            raw = base64.urlsafe_b64decode(payload['body']['data'].encode('ASCII'))
            html_text = raw.decode(errors='ignore')
            return clean_email_body(html_text)
        except Exception:
            return ""
    if 'parts' in payload:
        for part in payload['parts']:
            body = _extract_body(part)
            if body:
                return body
    return ""


def clean_email_body(html: str) -> str:
    # Parse HTML
    soup = BeautifulSoup(html, "lxml")

    # Get visible text
    text = soup.get_text(separator="\n")

    # Remove duplicate consecutive lines
    lines = text.splitlines()
    deduped = []
    seen = set()
    for line in lines:
        line_clean = line.strip()
        if line_clean and line_clean not in seen:
            deduped.append(line_clean)
            seen.add(line_clean)

    # Join lines and normalize spaces
    cleaned = "\n".join(deduped)
    cleaned = re.sub(r"\s+\n", "\n", cleaned)
    cleaned = re.sub(r"\n+", "\n", cleaned)  # multiple newlines → single newline

    return cleaned.strip()



def fetch_recent_emails(token_path: str, max_results: int = 100, query: str = None):
    svc = build_service_for_token(token_path)

    params = {
        "userId": "me",
        "maxResults": max_results,
        "includeSpamTrash": True,
    }

    if query:
        params["q"] = query

    resp = svc.users().messages().list(**params).execute()
    msgs = resp.get('messages', [])
    
    result = []
    for m in msgs:
        msg = svc.users().messages().get(userId='me', id=m['id'], format='full').execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        subject = next((h['value'] for h in headers if h.get('name', '').lower() == 'subject'), '')
        sender = next((h['value'] for h in headers if h.get('name', '').lower() == 'from'), '')
        body = _extract_body(payload) or msg.get('snippet', '')

        internal_date = int(msg.get('internalDate', 0)) / 1000  # milliseconds → seconds

        result.append({
            'id': msg.get('id'),
            'threadId': msg.get('threadId'),
            'subject': subject,
            'sender': sender,
            'body': body,
            'snippet': msg.get('snippet'),
            'internalDate': internal_date,
        })

    return result

