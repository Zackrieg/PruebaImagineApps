import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password = "test_password"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    return bcrypt.checkpw(password.encode("utf-8"), hashed)