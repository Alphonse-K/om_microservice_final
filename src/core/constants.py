from enum import Enum


class TransactionStatus(str, Enum):
    CREATED = 'created'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    PENDING = 'pending'


class WithdrawalStatus(str, Enum):
    INITIATED = 'initiated'
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    FAILED = 'failed'
    TIMEOUT = 'timeout'


class TransactionType(str, Enum):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    CREDIT_PURCHASE = 'credit_purchase'


# Used for Gmail background tasks
class GmailAccountType(str, Enum):
    AIRTIME = 'airtime'
    WITHDRAWAL = 'withdrawal'
