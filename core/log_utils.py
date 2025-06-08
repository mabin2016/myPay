import logging

def get_logger(name, level=logging.INFO, handler_class=logging.StreamHandler, formatter=None):
    """
    A simple helper to get and configure a logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent adding multiple handlers if logger already has them (e.g., during reloads)
    if not logger.handlers:
        handler = handler_class() # Default to StreamHandler (console)
        if formatter is None:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Example:
# my_logger = get_logger(__name__)
# my_file_logger = get_logger("my_app_file_logger", handler_class=logging.FileHandler, filename="app.log")
