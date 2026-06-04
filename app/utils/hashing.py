import bcrypt

def hash_password(password: str) -> str:
    """Перетворює чистий пароль (plain password) на хеш (hash)"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевіряє чи збігається пароль з хешем"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
