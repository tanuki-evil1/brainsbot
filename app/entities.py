from dataclasses import dataclass, field
from datetime import datetime

AMOUNT = 250
DISCOUNT = 10

@dataclass
class Subscription:
    user_id: int
    key: str | None = None
    public_key: str | None = None
    is_notify: bool = False
    is_active: bool = False
    amount: int = AMOUNT
    id: int | None = None
    end_date: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class User:
    id: int
    first_name: str
    last_name: str
    username: str
    language_code: str
    subscription: Subscription | None = None
    referrals: list["Referral"] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Referral:
    referrer_id: int
    referral_id: int
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    referral: User | None = None
