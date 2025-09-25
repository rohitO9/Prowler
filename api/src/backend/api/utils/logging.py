import logging
from django.conf import settings

def get_logger(name):
    """
    Returns a logger instance configured according to the application settings.
    
    Args:
        name (str): The name of the logger, typically __name__ from the calling module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Set the logging level from Django settings or default to INFO
        logger.setLevel(getattr(settings, 'LOGGING_LEVEL', logging.INFO))
        
        # Create console handler
        handler = logging.StreamHandler()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add formatter to handler
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    return logger