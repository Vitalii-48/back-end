# app/models/enums.py
import enum

class RequestType(str, enum.Enum):
    INVITE = "INVITE"       # Коли Власник запрошує користувача
    REQUEST = "REQUEST"     # Коли користувач сам проситься в компанію


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"     # Очікує розгляду
    ACCEPTED = "ACCEPTED"   # Прийнято
    DECLINED = "DECLINED"   # Відхилено
    CANCELED = "CANCELED"   # Скасовано


class CompanyRole(str, enum.Enum):
    OWNER = "OWNER"          # Власник компанії
    MEMBER = "MEMBER"        # Звичайний учасник
    ADMIN = "ADMIN"          #Адміністратор


class NotificationStatus(str, enum.Enum):
    UNREAD = "unread"       # Нове, не прочитане користувачем сповіщення
    READ = "read"           # Сповіщення, яке користувач уже переглянув