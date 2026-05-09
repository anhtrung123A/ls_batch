import base64
import hashlib
import os


class PasswordHasher:
    ITERATIONS = 100_000
    SALT_SIZE = 16
    KEY_SIZE = 32

    def hash_password(self, password: str) -> str:
        salt = os.urandom(self.SALT_SIZE)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.ITERATIONS,
            dklen=self.KEY_SIZE,
        )
        return f"{self.ITERATIONS}.{base64.b64encode(salt).decode()}.{base64.b64encode(key).decode()}"
