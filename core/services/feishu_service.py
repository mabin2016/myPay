import logging
from .base_notification import BaseNotificationService
# from core.models import FeishuRecord

logger = logging.getLogger(__name__)

class FeishuService(BaseNotificationService):
    """
    Mock implementation of a Feishu notification service.
    """
    def send(self, recipient, message, message_type='text', **kwargs):
        # Recipient could be user ID, open ID, chat ID. Message is often a structured JSON.
        if not recipient or not message:
            logger.error(f"Feishu Service: Missing recipient or message. Recipient: {recipient}")
            return False, {"error": "Recipient and message are required."}

        log_message = f"Simulating Feishu message (type: {message_type}) sent to {recipient}. Content: {message}. Options: {kwargs}"
        logger.info(log_message)

        # Example of how one might log to the database:
        # try:
        #     FeishuRecord.objects.create(
        #         target_user=str(recipient)[:100],
        #         message_type=str(message_type)[:50],
        #         content=message if isinstance(message, dict) else {"text": message},
        #         status=1, # 1 for mock success
        #         response_message=f'{{"status": "mock_success", "message_id": "mock_feishu_{recipient}"}}'
        #     )
        # except Exception as e:
        #     logger.error(f"Failed to create FeishuRecord for recipient {recipient}: {e}")

        return True, {"status": "mock_success", "message_id": f"mock_feishu_{recipient}"}
