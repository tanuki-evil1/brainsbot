from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, BigInteger, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from vi_core.sqlalchemy.base_model import Base, TimestampMixin

from app.entities import AMOUNT


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    is_notify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=AMOUNT)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    key: Mapped[str] = mapped_column(String(500), nullable=True, default=None)
    public_key: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    allowed_ip: Mapped[str] = mapped_column(String(255), nullable=True, default=None)
    # One-to-one связь
    user: Mapped["User"] = relationship("User", back_populates="subscription", uselist=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=True)

    # One-to-one связь с подпиской
    subscription: Mapped[Subscription | None] = relationship("Subscription", back_populates="user", uselist=False)

    # Реферальные связи
    # Те, кого пригласил этот пользователь (один ко многим)
    referrals: Mapped[list["Referral"]] = relationship(
        "Referral", foreign_keys="Referral.referrer_id", back_populates="referrer", uselist=True
    )


class Referral(Base, TimestampMixin):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Пользователь, которого пригласили
    referral_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    # Пользователь, который пригласил (реферер)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # Связи
    referral: Mapped["User"] = relationship("User", foreign_keys=[referral_id], uselist=False)
    referrer: Mapped["User"] = relationship(
        "User", foreign_keys=[referrer_id], back_populates="referrals", uselist=False
    )
