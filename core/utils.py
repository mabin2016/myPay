import datetime
import os
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# --- Time Handling ---

def get_current_timestamp_str(format="%Y-%m-%d %H:%M:%S"):
    """Returns the current timestamp as a formatted string."""
    return timezone.now().strftime(format)

def parse_datetime_str(datetime_str, format="%Y-%m-%d %H:%M:%S"):
    """Parses a datetime string into a datetime object."""
    if not datetime_str:
        return None
    try:
        return timezone.datetime.strptime(datetime_str, format)
    except ValueError:
        logger.warning(f"Invalid datetime string format: {datetime_str} for format {format}")
        return None

def datetime_to_str(dt_obj, format="%Y-%m-%d %H:%M:%S"):
    """Converts a datetime object to a formatted string."""
    if not dt_obj:
        return None
    return dt_obj.strftime(format)

# --- Encryption/Decryption ---

# Load the encryption key from settings.
# Ensure FIELD_ENCRYPTION_KEY is set in your .env and loaded in settings.py
# Example: FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode() in .env
# and in settings.py: FIELD_ENCRYPTION_KEY = os.getenv('FIELD_ENCRYPTION_KEY')

_ENCRYPTION_KEY = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
if _ENCRYPTION_KEY:
    try:
        _FERNET_INSTANCE = Fernet(_ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.error(f"Failed to initialize Fernet with FIELD_ENCRYPTION_KEY: {e}. "
                     "Ensure it's a valid Fernet key (bytes or string). "
                     "Data encryption/decryption will not work.")
        _FERNET_INSTANCE = None
else:
    logger.warning("FIELD_ENCRYPTION_KEY is not set in Django settings. "
                   "Data encryption/decryption will not be available. "
                   "Please generate a key (e.g., Fernet.generate_key().decode()) "
                   "and set it in your .env file as FIELD_ENCRYPTION_KEY.")
    _FERNET_INSTANCE = None


def encrypt_data(data: str) -> str | None:
    """Encrypts a string using Fernet symmetric encryption."""
    if _FERNET_INSTANCE is None:
        logger.error("Encryption service not available: Fernet key not configured.")
        # Depending on policy, either raise an error or return original data / handle gracefully
        # For now, returning None or raising an error might be safer than returning unencrypted data.
        # raise ValueError("Encryption key not configured.")
        return None # Or handle as per application's error policy

    if not isinstance(data, str):
        # Fernet expects bytes. If you pass non-string, ensure it's properly encoded to bytes.
        # For simplicity, this example expects string data.
        logger.warning(f"encrypt_data expects a string, got {type(data)}. Will attempt to convert.")
        try:
            data = str(data)
        except Exception:
            logger.error(f"Could not convert data of type {type(data)} to string for encryption.")
            return None

    try:
        encrypted_bytes = _FERNET_INSTANCE.encrypt(data.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Error during data encryption: {e}", exc_info=True)
        return None

def decrypt_data(encrypted_data: str) -> str | None:
    """Decrypts a string that was encrypted with Fernet."""
    if _FERNET_INSTANCE is None:
        logger.error("Decryption service not available: Fernet key not configured.")
        # raise ValueError("Decryption key not configured.")
        return None

    if not isinstance(encrypted_data, str):
        logger.error(f"decrypt_data expects a string, got {type(encrypted_data)}.")
        return None # Encrypted data should be a string (base64 encoded)

    try:
        decrypted_bytes = _FERNET_INSTANCE.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except InvalidToken:
        logger.error("Invalid token or key for decryption. Data may be corrupted or wrong key used.")
        return None
    except Exception as e:
        logger.error(f"Error during data decryption: {e}", exc_info=True)
        return None

# --- Other Utilities ---

def generate_random_string(length=10, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """Generates a random string of specified length."""
    import random
    return ''.join(random.choice(allowed_chars) for i in range(length))

# Placeholder for unique ID generation if needed beyond model PKs
# import uuid
# def generate_unique_identifier(prefix=''):
#     return f"{prefix}{uuid.uuid4().hex}"

# You can add more utilities as the project grows.
# For example, functions for:
# - Slug generation
# - Data cleaning or sanitization (though often better in forms/serializers)
# - Complex calculations specific to the core domain but not fitting elsewhere.
