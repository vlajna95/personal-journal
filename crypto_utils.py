"""Encryption utilities for the Personal Journal app."""

import base64
import hashlib
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken

PBKDF2_ITERATIONS = 480_000


def generate_salt() -> bytes:
    return secrets.token_bytes(32)


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    raw = kdf.derive(password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def make_fernet(password: str, salt: bytes) -> Fernet:
    return Fernet(_derive_key(password, salt))


def hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return base64.b64encode(dk).decode("ascii")


def verify_password(password: str, salt_b64: str, stored_hash: str) -> bool:
    salt = base64.b64decode(salt_b64)
    return hash_password(password, salt) == stored_hash


def encrypt(fernet: Fernet, plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(fernet: Fernet, ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
