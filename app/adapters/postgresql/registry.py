from vi_core import Mapper

from app import entities
from app.adapters.postgresql import models

mapper = Mapper()


def user_to_entity(user: models.User) -> entities.User:
    return entities.User(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
        subscription=subscription_to_entity(user.subscription) if user.subscription else None,
    )


def user_to_model(user: entities.User) -> models.User:
    return models.User(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
    )


def subscription_to_entity(subscription: models.Subscription) -> entities.Subscription:
    return entities.Subscription(
        id=subscription.id,
        user_id=subscription.user_id,
        is_notify=subscription.is_notify,
        end_date=subscription.end_date,
        is_active=subscription.is_active,
        amount=subscription.amount,
        key=subscription.key,
        public_key=subscription.public_key,
    )


def subscription_to_model(subscription: entities.Subscription) -> models.Subscription:
    return models.Subscription(
        id=subscription.id if subscription.id else None,
        user_id=subscription.user_id,
        is_notify=subscription.is_notify,
        end_date=subscription.end_date,
        amount=subscription.amount,
        is_active=subscription.is_active,
        key=subscription.key,
        public_key=subscription.public_key,
    )


mapper.register(models.User, entities.User, user_to_entity, True)
mapper.register(entities.User, models.User, user_to_model)
mapper.register(models.Subscription, entities.Subscription, subscription_to_entity, True)
mapper.register(entities.Subscription, models.Subscription, subscription_to_model)
