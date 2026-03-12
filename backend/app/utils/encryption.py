"""
encryption.py
-------------
GSTIN aur sensitive data encryption — AES-256 via Fernet.
Key sirf .env mein — kabhi code mein nahi.
IT Act 2000 Section 43A compliance.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Cache cipher — settings load ek baar
_cipher: Fernet | None = None


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is None:
        settings = get_settings()
        try:
            _cipher = Fernet(settings.encryption_key.encode())
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_KEY: {e}") from e
    return _cipher


def encrypt_gstin(gstin: str) -> str:
    """
    GSTIN encrypt karo — store karne se pehle.
    Returns base64 encoded string (safe for DB storage).
    """
    try:
        cipher = _get_cipher()
        encrypted_bytes = cipher.encrypt(gstin.upper().encode())
        return encrypted_bytes.decode()          # str store karo DB mein
    except Exception as e:
        logger.error("GSTIN encryption failed")  # GSTIN log mein nahi
        raise RuntimeError("Encryption failed") from e


def decrypt_gstin(encrypted: str) -> str:
    """
    DB se encrypted GSTIN decrypt karo — read karte waqt.
    """
    try:
        cipher = _get_cipher()
        return cipher.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.error("GSTIN decryption failed — invalid token")
        raise RuntimeError("Decryption failed — key mismatch?")
    except Exception as e:
        logger.error("GSTIN decryption failed")
        raise RuntimeError("Decryption failed") from e


def generate_key() -> str:
    """
    New Fernet key generate karo.
    Sirf setup ke time use karo — scripts/generate_key.py se.
    """
    return Fernet.generate_key().decode()