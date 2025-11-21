from dataclasses import dataclass, field
from datetime import datetime, timedelta

AMOUNT = 300
DISCOUNT = 15


@dataclass
class Subscription:
    user_id: int
    is_notify: bool = True
    is_active: bool = True
    amount: int = AMOUNT
    id: int | None = None
    end_date: datetime | None = field(default_factory=lambda: datetime.now() + timedelta(days=3))
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
