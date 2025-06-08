import logging
from .base_notification import BaseNotificationService
# from core.models import DingtalkRecord

logger = logging.getLogger(__name__)

class DingtalkService(BaseNotificationService):
    """
    Mock implementation of a Dingtalk notification service.
    """
    def send(self, recipient, message, message_type='text', **kwargs):
        # Recipient could be user ID, chat ID. Message is often a structured JSON.
        if not recipient or not message:
            logger.error(f"Dingtalk Service: Missing recipient or message. Recipient: {recipient}")
            return False, {"error": "Recipient and message are required."}

        log_message = f"Simulating Dingtalk message (type: {message_type}) sent to {recipient}. Content: {message}. Options: {kwargs}"
        logger.info(log_message)

        # Example of how one might log to the database:
        # try:
        #     DingtalkRecord.objects.create(
        #         target_user=str(recipient)[:255],
        #         message_type=str(message_type)[:50],
        #         content=message if isinstance(message, dict) else {"text": message},
        #         status=1, # 1 for mock success
        #         response_message=f'{{"status": "mock_success", "message_id": "mock_dingtalk_{recipient}"}}'
        #     )
        # except Exception as e:
        #     logger.error(f"Failed to create DingtalkRecord for recipient {recipient}: {e}")

        return True, {"status": "mock_success", "message_id": f"mock_dingtalk_{recipient}"}
