import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class PhoneNumberValidator:
    """
    Validates that the input looks like a plausible phone number.
    This is a basic validator and might need to be adjusted for international numbers
    or more specific formats.
    """
    requires_context = False
    PHONE_REGEX = r"^(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}$"
    # This regex is for Chinese mobile numbers. Adjust as needed.

    def __call__(self, value):
        if not re.match(self.PHONE_REGEX, value):
            raise ValidationError(
                _("Invalid phone number format. Expected Chinese mobile format like 13800138000."),
                code='invalid_phone_number'
            )

    def __eq__(self, other):
        return isinstance(other, PhoneNumberValidator)

# Example usage in a model:
# from .validators import PhoneNumberValidator
# phone_field = models.CharField(max_length=20, validators=[PhoneNumberValidator()])

def validate_phone_number(value):
    """
    Functional version of the PhoneNumberValidator, can be used directly in serializers or forms.
    """
    validator = PhoneNumberValidator()
    validator(value)

# You can add other general-purpose validators here, for example:
# - Postal Code Validator
# - ID Card Validator (country-specific)
# - NonNegativeValidator

class NonNegativeIntegerValidator:
    """
    Validates that the input is a non-negative integer.
    """
    def __call__(self, value):
        if not isinstance(value, int) or value < 0:
            raise ValidationError(
                _("This field must be a non-negative integer."),
                code='invalid_non_negative_integer'
            )

    def __eq__(self, other):
        return isinstance(other, NonNegativeIntegerValidator)

def validate_non_negative_integer(value):
    validator = NonNegativeIntegerValidator()
    validator(value)
