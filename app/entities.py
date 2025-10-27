from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

AMOUNT = 300
DISCOUNT = 15

class Protocol(StrEnum):
    WIREGUARD = "wg"
    XRAY = "xray"


@dataclass
class Server:
    id: int
    host: str
    port: int
    location: str
    password: str
    admin_username: str
    additional_info: dict[str, Any]

@dataclass
class Subscription:
    user_id: int
    is_notify: bool = True
    is_active: bool = True
    amount: int = AMOUNT
    id: int | None = None
    end_date: datetime | None = field(default_factory=lambda: datetime.now() + timedelta(days=1))

    active_protocol: Protocol = Protocol.XRAY
    active_server_id: int = 1

    wg_allowed_ip: str | None = None
    wg_key: str | None = None
    wg_public_key: str | None = None

    xray_key: str | None = None
    xray_uuid: UUID | None = None

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


@dataclass
class WireGuardUserConfig:
    client_public_key: str
    access_key: str
    allowed_ip: str
    username: str

@dataclass
class XrayUserConfig:
    uuid: UUID
    key: str
    username: str



