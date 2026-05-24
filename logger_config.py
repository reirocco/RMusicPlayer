import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
import os
from collections import deque

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'

# Memory Buffer Handler for Frontend API
class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity=500):
        super().__init__()
        self.buffer = deque(maxlen=capacity)
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self):
        return list(self.buffer)

memory_handler = MemoryLogHandler()

def setup_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Memory Handler for UI
    memory_handler.setFormatter(formatter)
    logger.addHandler(memory_handler)

    # File Handler
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Failsafe assoluto se la directory non è scrivibile per motivi oscuri
        logger.warning(f"Impossibile scrivere in {LOG_FILE}: {e}")

    return logger

# Get primary loggers
core_logger = setup_logger('CORE', logging.DEBUG)
flask_logger = setup_logger('FLASK', logging.INFO)

# Global Exception Hook to catch unhandled exceptions
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    core_logger.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = global_exception_handler
