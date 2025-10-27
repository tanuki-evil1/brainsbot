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
        active_server_id=subscription.active_server_id,
        active_protocol=subscription.active_protocol,
        wg_key=subscription.wg_key,
        wg_public_key=subscription.wg_public_key,
        wg_allowed_ip=subscription.wg_allowed_ip,
        xray_key=subscription.xray_key,
        xray_uuid=subscription.xray_uuid,
    )


def subscription_to_model(subscription: entities.Subscription) -> models.Subscription:
    return models.Subscription(
        id=subscription.id if subscription.id else None,
        user_id=subscription.user_id,
        is_notify=subscription.is_notify,
        end_date=subscription.end_date,
        amount=subscription.amount,
        is_active=subscription.is_active,
        active_server_id=subscription.active_server_id,
        active_protocol=subscription.active_protocol,
        wg_key=subscription.wg_key,
        wg_public_key=subscription.wg_public_key,
        wg_allowed_ip=subscription.wg_allowed_ip,
        xray_key=subscription.xray_key,
        xray_uuid=subscription.xray_uuid,
    )


def referral_to_entity(referral: models.Referral) -> entities.Referral:
    return entities.Referral(
        id=referral.id,
        referral_id=referral.referral_id,
        referrer_id=referral.referrer_id,
        created_at=referral.created_at,
        updated_at=referral.updated_at,
        referral=user_to_entity(referral.referral) if referral.referral else None,
    )


def referral_to_model(referral: entities.Referral) -> models.Referral:
    return models.Referral(
        id=referral.id if referral.id else None,
        referral_id=referral.referral_id,
        referrer_id=referral.referrer_id,
        created_at=referral.created_at,
        updated_at=referral.updated_at,
    )


def server_to_entity(server: models.Server) -> entities.Server:
    return entities.Server(
        id=server.id,
        host=server.host,
        port=server.port,
        location=server.location,
        password=server.password,
        admin_username=server.admin_username,
        additional_info=server.additional_info,
    )


def server_to_model(server: entities.Server) -> models.Server:
    return models.Server(
        id=server.id,
        host=server.host,
        port=server.port,
        admin_username=server.admin_username,
        location=server.location,
        password=server.password,
        additional_info=server.additional_info,
    )

mapper.register(models.Referral, entities.Referral, referral_to_entity, True)
mapper.register(entities.Referral, models.Referral, referral_to_model)
mapper.register(models.User, entities.User, user_to_entity, True)
mapper.register(entities.User, models.User, user_to_model)
mapper.register(models.Subscription, entities.Subscription, subscription_to_entity, True)
mapper.register(entities.Subscription, models.Subscription, subscription_to_model)
mapper.register(models.Server, entities.Server, server_to_entity, True)
mapper.register(entities.Server, models.Server, server_to_model)
