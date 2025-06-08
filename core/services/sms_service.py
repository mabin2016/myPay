import logging
from .base_notification import BaseNotificationService
# from core.models import SmsRecord # Avoid direct model import here if possible to prevent circular dependencies or manage via tasks

logger = logging.getLogger(__name__)

class SmsService(BaseNotificationService):
    """
    Mock implementation of an SMS notification service.
    """
    def send(self, recipient, message, **kwargs):
        # In a real implementation, this would interact with an SMS gateway API.
        # It would also likely use the 'core.models.SmsRecord' to log the attempt.
        if not recipient or not message:
            logger.error(f"SMS Service: Missing recipient or message. Recipient: {recipient}")
            return False, {"error": "Recipient and message are required."}

        log_message = f"Simulating SMS sent to {recipient}: \"{message}\" with options: {kwargs}"
        logger.info(log_message)

        # Example of how one might log to the database (e.g., via a signal or a separate logging task):
        # try:
        #     SmsRecord.objects.create(
        #         phone_number=str(recipient)[:20], # Ensure length fits model field
        #         content=message,
        #         status=1, # 1 for mock success
        #         response_message=f'{{"status": "mock_success", "message_id": "mock_sms_{recipient}"}}'
        #     )
        # except Exception as e:
        #     logger.error(f"Failed to create SmsRecord for recipient {recipient}: {e}")

        return True, {"status": "mock_success", "message_id": f"mock_sms_{recipient}"}
