import secrets


def generate_random_password(length: int = 12) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
    return "".join(secrets.choice(chars) for _ in range(length))
