import logging

logger = logging.getLogger(__name__)

class BaseNotificationService:
    """
    Abstract base class for notification services.
    """
    def __init__(self, config=None):
        self.config = config or {}

    def send(self, recipient, message, **kwargs):
        """
        Sends a notification.

        :param recipient: The recipient of the notification (e.g., phone number, email address, user ID).
        :param message: The content of the message to be sent.
        :param kwargs: Additional parameters specific to the notification service.
        :return: Boolean indicating success or failure, and a response message/data.
        :raises NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("Subclasses must implement the send() method.")

    def send_batch(self, recipients, message, **kwargs):
        """
        Sends a notification to multiple recipients.
        Default implementation iterates `send` method. Subclasses can override for efficiency.
        """
        results = []
        for recipient in recipients:
            try:
                success, response = self.send(recipient, message, **kwargs)
                results.append({'recipient': recipient, 'success': success, 'response': response})
            except Exception as e:
                logger.error(f"Error sending to {recipient} in batch: {e}", exc_info=True)
                results.append({'recipient': recipient, 'success': False, 'response': str(e)})
        return results
