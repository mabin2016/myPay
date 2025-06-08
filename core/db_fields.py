from django.db import models
from django.core.exceptions import ValidationError
from core.utils import encrypt_data, decrypt_data # Ensure core.utils is importable
import logging

logger = logging.getLogger(__name__)

class EncryptedField(models.TextField):
    """
    A custom Django model field that automatically encrypts data when saving to
    the database and decrypts it when fetching from the database.
    Uses Fernet encryption from core.utils.
    """
    description = "A field that stores data encrypted in the database."

    def __init__(self, *args, **kwargs):
        # TextField is a good base as encrypted data can be longer than original.
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        """
        Converts data from the database format (encrypted string) to Python object (decrypted string).
        """
        if value is None:
            return value
        try:
            decrypted_value = decrypt_data(value)
            if decrypted_value is None and value is not None:
                # This indicates a decryption failure with a non-null DB value.
                # It might be due to unencrypted data in DB or wrong key.
                logger.error(f"EncryptedField: Decryption failed for DB value (first 20 chars): '{value[:20]}...'. Returning None. Check encryption key and data integrity.")
                # Depending on policy, you might want to raise an error or return the raw value.
                # Returning None or a specific marker might be safer than returning potentially corrupted data.
                # For now, we'll return None as decrypt_data itself returns None on failure.
            return decrypted_value
        except Exception as e:
            logger.error(f"EncryptedField: Error during decryption from_db_value: {e}", exc_info=True)
            # Handle this case, perhaps by returning None or raising a specific error
            return None # Or the raw value, depending on how you want to handle decryption errors

    def to_python(self, value):
        """
        Converts the value from its database representation or user input into a Python object.
        This is called during deserialization and when the field is accessed.
        If the value is already a string (e.g. from user input before saving), we don't decrypt.
        If it's from the DB (already decrypted by from_db_value), it should be a string.
        """
        if isinstance(value, str) or value is None:
            # If it's already a string (decrypted) or None, return as is.
            # Or, if it's a string that is meant to be encrypted before saving,
            # this method should handle it. However, get_prep_value is more for DB saving.
            return value

        # This case should ideally not be hit if from_db_value handles DB reads.
        # If value is somehow still an encrypted string here, attempt decryption.
        # This might happen if data is loaded into the model instance from somewhere else
        # not via a direct DB query that invokes from_db_value.
        try:
            decrypted_value = decrypt_data(str(value)) # Assuming value might be non-string encrypted
            if decrypted_value is None and value is not None:
                 logger.warning(f"EncryptedField: to_python received a value that could not be decrypted: '{str(value)[:20]}...'")
            return decrypted_value
        except Exception: # Catch broader exceptions if str(value) fails or decrypt_data has issues
            logger.warning(f"EncryptedField: Could not convert/decrypt value in to_python: '{str(value)[:20]}...'. Returning as is.")
            return value # Fallback to returning the value as is if decryption fails here.

    def get_prep_value(self, value):
        """
        Converts Python object (string) to database format (encrypted string).
        This is called when saving data to the database.
        """
        if value is None:
            return value

        # We only encrypt if it's not already encrypted (heuristic: doesn't decrypt to itself)
        # This is tricky. A better approach is to rely on the field always receiving plain text.
        # If the data might already be encrypted, the application logic needs to be clear.
        # Forcing encryption on already encrypted data would double-encrypt.

        # Let's assume `value` is always plain text that needs encryption.
        try:
            encrypted_value = encrypt_data(str(value)) # Ensure value is a string
            if encrypted_value is None and value is not None :
                logger.error(f"EncryptedField: Encryption failed for value: '{str(value)[:20]}...'. Storing as NULL or raising error.")
                # Raise an error to prevent storing unencrypted or None for a non-nullable field if encryption fails
                raise ValidationError("Failed to encrypt data. Field cannot be saved.")
            return encrypted_value
        except Exception as e:
            logger.error(f"EncryptedField: Error during encryption in get_prep_value: {e}", exc_info=True)
            # Handle this based on policy: raise error, or return None if field is nullable
            if self.null:
                return None
            raise ValidationError(f"Failed to prepare value for database: {e}")

    # Optional: Add support for lookups if needed, though exact match on encrypted data is typical.
    # Range lookups or case-insensitive lookups won't work directly on encrypted data.
    # def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
    #     if lookup_type == 'exact':
    #         return [self.get_prep_value(value)]
    #     elif lookup_type == 'in':
    #         return [self.get_prep_value(v) for v in value]
    #     # Add other lookups if you can support them (e.g., isnull)
    #     elif lookup_type == 'isnull':
    #         return [] # Handled by SQL
    #     else:
    #         # For most lookups, direct operations on encrypted data are not meaningful
    #         raise NotImplementedError(f"Lookup type {lookup_type} is not supported for EncryptedField.")
    #     return super().get_db_prep_lookup(lookup_type, value, connection, prepared)

# Example of how to use it in a model:
# from core.db_fields import EncryptedField
# class MyModel(models.Model):
#     sensitive_info = EncryptedField(null=True, blank=True)
#     # If the field should not be nullable in Python but can be null in DB temporarily before encryption
#     # or if encryption fails for a nullable field:
#     # sensitive_info = EncryptedField(db_nullable=True, null=True, blank=True)

# Note: If FIELD_ENCRYPTION_KEY is not set, encrypt_data and decrypt_data will return None
# or raise errors, which this field will then propagate or handle based on its nullability.
# It's crucial that the key is correctly configured for this field to work.
