from enum import StrEnum

# Основные сообщения системы
WELCOME_MESSAGE = """🔐 Brains Secure

👋 Добро пожаловать\\!

Это бот для управления вашим аккаунтом в Brains Secure\\.

🎯 Выберите действие:"""

ACCOUNT_TEXT = """👤 *Имя пользователя:* `{username}`

💎 *Статус подписки:* `{subscription_status}`

📅 *Дата окончания:* `{end_date}`

🔑 *Ваш ключ, нажмите для копирования:*
`{key}`
"""

REFERRAL_TEXT = """👥 *Реферальная программа*

Скидка за реферальную программу: `{discount}%`

Ваши рефералы:
{referrals}

Ваша реферальная ссылка:
`https://t\\.me/brains\\_secure\\_bot?start\\=ref\\_{referral_link}`
"""

INSTRUCTIONS_TEXT = """📋 *Инструкции по использованию Brains Secure*

⚙️ *Поддерживаемые устройства:*
• iOS \\(iPhone/iPad\\)
• Android \\(телефоны/планшеты\\)
• Windows \\(ПК/ноутбуки\\)
• macOS \\(Mac\\)
• Linux \\(различные дистрибутивы\\)
• Android TV"""

SUBSCRIPTION_EXPIRED_MESSAGE = "🔔 Время оплатить подписку\\!"

# Сообщения для рассылки
BROADCAST_REQUEST_MESSAGE = """📢 *Массовая рассылка*

Отправьте сообщение, которое будет разослано всем пользователям бота\\."""

BROADCAST_CONFIRMATION_MESSAGE = """📢 Подтверждение рассылки

Сообщение будет отправлено {count} пользователям.

Вы уверены?"""

BROADCAST_SUCCESS_MESSAGE = "✅ Рассылка завершена! Отправлено сообщений: {sent} из {total}"

BROADCAST_CANCELLED_MESSAGE = "❌ Рассылка отменена"


# Enum для статусных сообщений
class StatusMessages(StrEnum):
    # Уведомления
    NOTIFICATIONS_ENABLED = "✅ Уведомления включены"
    NOTIFICATIONS_DISABLED = "❌ Уведомления отключены"

    # Подписка
    SUBSCRIPTION_ACTIVE = "активна"
    SUBSCRIPTION_INACTIVE = "неактивна"
    SUBSCRIPTION_NO_END_DATE = "необходима подписка"
    SUBSCRIPTION_ALREADY_ACTIVE = "У вас уже есть активная подписка, можете продлить ее"
    SUBSCRIPTION_NO_KEY = "необходима подписка"

    # Сообщения
    MESSAGE_SENT = "Ваше сообщение отправлено"
    MESSAGE_SENT_ACCESS_GRANTED = "Ваше сообщение отправлено, проверьте ваш аккаунт"
    ONLY_PHOTO_OR_DOCUMENT = "Необходимо отправить только фото или документ"


# Enum для сообщений с требованиями действий
class ActionRequiredMessages(StrEnum):
    NOTIFICATIONS_ACTIVATION_REQUIRED = "Для того чтобы включить уведомления, вам нужно активировать подписку"
    SUPPORT_REQUEST = (
        "Опишите проблему и при необходимости прикрепите фото\\. Мы передадим ваше сообщение в поддержку\\."
    )
    SUPPORT_CHECK_REQUEST = "Прикрепите фото или документ с чеком"


# Enum для шаблонов сообщений
class MessageTemplates(StrEnum):
    SUPPORT_MESSAGE = "🆘 Поддержка\nId: {user_id} \nUsername: @{username}\n\nСообщение:\n{text}"
    CHECK_INFO = "💸 *Проверка чека:* \nОт: @{username}\n\nСообщение:\n{text}"
    PAYMENT_INFO = """💰 *Оплатить:*

1️⃣ Перейдите по ссылке
2️⃣ Оплатите `{amount} рублей`
3️⃣ Отправьте скриншот оплаты в поддержку"""
    END_DATE_FORMAT = "{date} - {days}{days_text}"
    REFERRAL_USER_FORMAT = "{first_name} \\(@{username}\\){separator}{status}\n"


# Enum для текстов кнопок
class ButtonTexts(StrEnum):
    # Главное меню
    ACCOUNT = "💼 Мой Аккаунт"
    NOTIFICATIONS = "🔔 Уведомления"
    INSTRUCTIONS = "⚙️ Инструкции"
    DONATE = "⭐️ Оплатить"
    TEAM = "👥 Рефералы"
    SUPPORT = "🆘 Поддержка"

    # Инструкции
    INSTRUCTION_CONNECT = "Как подключиться?"
    INSTRUCTION_SPEED = "Как увеличить скорость?"
    INSTRUCTION_REFERRAL = "Кто такие рефы?"
    INSTRUCTION_EXCLUDE = "Как добавить сайт/сервис в исключения?   "
    INSTRUCTION_UPDATE = "Как помочь нам?"

    # Действия
    SEND_CHECK = "💸 Отправить чек"
    DISABLE_NOTIFICATIONS = "❌ Отключить уведомления"

    # Рассылка
    BROADCAST_CONFIRM = "✅ Подтвердить"
    BROADCAST_CANCEL = "❌ Отменить"


# Enum для инструкций
class InstructionTexts(StrEnum):
    CONNECT = """🔧 *Настройка подключения:*

1️⃣ Скачайте приложение Amnezia
\\- [Play Market](https://play.google.com/store/apps/details?id=org.amnezia.vpn)
\\- [App Store](https://apps.apple.com/us/app/amneziavpn/id1600529900?l=ru)
\\- [Другие устройства](https://github.com/amnezia-vpn/amnezia-client/releases)

Или AmneziaWG
\\- [Play Market](https://play.google.com/store/apps/details?id=org.amnezia.awg)
\\- [App Store](https://apps.apple.com/us/app/amneziawg/id6478942365)
\\- [Другие устройства](https://github.com/amnezia-vpn/amneziawg-windows-client?tab=readme-ov-file)

2️⃣ Оплатите подписку
3️⃣ Получите ключ в разделе "*Мой аккаунт*"
4️⃣ Импортируйте ключ в Amnezia
5️⃣ Активируйте подключение

🆘 Если вам не подошла Amnezia или вы хотите использовать другое приложение/устройство, то напишите в поддержку"""

    SPEED = """🔧 *Как повысить скорость?*

1️⃣ Проверьте скорость без подключения
2️⃣ Скачайте конфигурационный файл ниже
3️⃣ Импортируйте конфигурацию в Amnezia в "*Раздельном туннелировании*"
4️⃣ Активируйте подключение"""

    REFERRAL = """🔧 *Реферальная программа*

1️⃣ Получите реферальную ссылку в главном меню
2️⃣ Пригласите друзей
3️⃣ Они оформят подписку
4️⃣ Вы получите скидку за каждого реферала по 10%
"""

    EXCLUDE = """🔧 *Как добавить сайт/приложение в исключения?*

1️⃣ Откройте настройки вашего устройства
2️⃣ Найдите раздел "*Раздельное туннелирование*"
3️⃣ Выберите "*Сайты или приложения*"
4️⃣ Добавьте нужный сайт/приложение"""

    UPDATE = """🔧 *Как помочь нам?*

1️⃣ Напишите в поддержку свои идеи и предложения :\\)"""


# Callback данные для кнопок
class CallbackData(StrEnum):
    ACCOUNT = "account"
    NOTIFICATIONS = "notifications"
    INSTRUCTIONS = "instructions"
    TEAM = "team"
    SUPPORT = "support"
    DONATE = "donate"
    SEND_CHECK = "send_check"
    INSTRUCTION_CONNECT = "instruction_connect"
    INSTRUCTION_SPEED = "instruction_speed"
    INSTRUCTION_REFERRAL = "instruction_referral"
    INSTRUCTION_EXCLUDE = "instruction_exclude"
    INSTRUCTION_UPDATE = "instruction_update"
    BROADCAST_CONFIRM = "broadcast_confirm"
    BROADCAST_CANCEL = "broadcast_cancel"


# Состояния FSM
class FSMStates(StrEnum):
    WAITING_FOR_SUPPORT_MESSAGE = "waiting_for_support_message"
    WAITING_FOR_CHECK_MESSAGE = "waiting_for_check_message"
    WAITING_FOR_BROADCAST_MESSAGE = "waiting_for_broadcast_message"


# Константы
class Constants(StrEnum):
    NO_TEXT_PLACEHOLDER = "Без текста"
    DAYS_TEXT = " дней"
    SUBSCRIPTION_SEPARATOR = " \\- Подписка "


# URL-адреса
class URLs(StrEnum):
    PAYMENT_URL = "https://www.tinkoff.ru/rm/r_ZkFAkdqUtA.OrtRNDgctR/B1KEL93183"
