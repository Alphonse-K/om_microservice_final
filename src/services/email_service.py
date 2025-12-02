from sqlalchemy.orm import Session
from src.models.email_message import EmailMessage
from src.schemas.email_message import EmailMessageCreate
import smtplib
import logging
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime
import os

logger = logging.getLogger(__name__)

def create_email(db: Session, paylaod: dict) -> EmailMessageCreate:
    # payload is a dict with fields matching EmailMessage
    email = EmailMessage(**paylaod)
    db.add(email)
    db.commit()
    db.refresh(email)
    return email

def get_email_by_message_id(db: Session, message_id: str):
    return db.query(EmailMessage).filter(EmailMessage.message_id==message_id).first()

def mark_email_matched(db: Session, email_obj: EmailMessage):
    email_obj.matched = True
    db.add(email_obj)
    db.commit()
    db.refresh(email_obj)
    return email_obj

def list_emails(db: Session, skip: int = 0, limit: int = 100):
    q = db.query(EmailMessage).order_by(EmailMessage.received_at.desc()).offset(skip).limit(limit).all()
    total = db.query(EmailMessage).count()
    return q, total


class EmailService:
    """Simple SMTP email service for CashMoov"""
    
    @staticmethod
    def send_otp_email(to_email: str, to_name: str, otp_code: str, purpose: str = None) -> bool:
        """Send OTP email in plain text"""
        try:
            subject_map = {
                "login": "CashMoov - Login OTP",
                "reset": "CashMoov - Password Reset OTP",
                "verify": "CashMoov - Email Verification OTP",
                "transaction": "CashMoov - Transaction OTP"
            }
            subject = subject_map.get(purpose, "CashMoov - OTP Code")
            
            content = f"""
                CASHMOOV SECURE OTP

                Hello {to_name},

                Your One-Time Password (OTP) is: {otp_code}

                This OTP is valid for 5 minutes.

                SECURITY NOTICE:
                - Never share this OTP with anyone
                - CashMoov staff will never ask for your OTP
                - If you didn't request this OTP, please ignore this email

                If you have any questions, contact support@cashmoov.net

                Best regards,
                CashMoov Team

                {datetime.now().year} © CashMoov. All rights reserved.
            """
            
            return EmailService._send_email(to_email, to_name, subject, content)
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(to_email: str, to_name: str) -> bool:
        """Send welcome email to new users"""
        try:
            subject = "Welcome to CashMoov"
            
            content = f"""
                WELCOME TO CASHMOOV

                Hello {to_name},

                Welcome to CashMoov! Your account has been created successfully.

                Account details:
                - Email: {to_email}
                - Created: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

                For security:
                1. Keep your password confidential
                2. Enable OTP for sensitive operations
                3. Contact us if you notice suspicious activity

                Get started: +++++++++++++++++

                Need help? Contact support@cashmoov.net

                Best regards,
                CashMoov Team

                {datetime.now().year} © CashMoov. All rights reserved.
            """
            
            return EmailService._send_email(to_email, to_name, subject, content)
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_login_notification(to_email: str, to_name: str, ip_address: str = "Unknown") -> bool:
        """Send login notification email"""
        try:
            subject = "CashMoov - New Login Detected"
            
            content = f"""
                CASHMOOV SECURITY NOTIFICATION

                Hello {to_name},

                A new login was detected on your CashMoov account.

                Login details:
                - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                - IP Address: {ip_address}

                If this was you, no action is needed.

                If this wasn't you:
                1. Change your password immediately
                2. Contact support@cashmoov.net
                3. Review your account activity

                Best regards,
                CashMoov Security Team

                {datetime.now().year} © CashMoov. All rights reserved.
            """
            
            return EmailService._send_email(to_email, to_name, subject, content)
            
        except Exception as e:
            logger.error(f"Failed to send login notification to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_change_notification(to_email: str, to_name: str) -> bool:
        """Send password change confirmation email"""
        try:
            subject = "CashMoov - Password Changed"
            
            content = f"""
                CASHMOOV PASSWORD CHANGE CONFIRMATION

                Hello {to_name},

                Your CashMoov account password has been changed successfully.

                Change details:
                - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                - Action: Password update

                If you need help, contact support@cashmoov.net

                Best regards,
                CashMoov Security Team

                {datetime.now().year} © CashMoov. All rights reserved.
                """
            
            return EmailService._send_email(to_email, to_name, subject, content)
            
        except Exception as e:
            logger.error(f"Failed to send password change email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def _send_email(to_email: str, to_name: str, subject: str, content: str) -> bool:
        """Send plain text email via SMTP"""
        try:
            # Get SMTP settings from environment
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            email_from = os.getenv("EMAIL_FROM", "noreply@cashmoov.net")
            email_from_name = os.getenv("EMAIL_FROM_NAME", "CashMoov")
            
            # # If no credentials, log to console for development
            # if not smtp_username or not smtp_password:
            #     logger.warning(f"Email credentials not configured. Email not sent.")
            #     # For development, print email to console
            #     print(f"\n[EMAIL DEBUG] To: {to_email}")
            #     print(f"Subject: {subject}")
            #     print(f"Content preview:\n{content[:200]}...")
            #     return True
            
            # Create email message
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = formataddr((email_from_name, email_from))
            msg['To'] = formataddr((to_name, to_email))
            
            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_port == 587:
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False