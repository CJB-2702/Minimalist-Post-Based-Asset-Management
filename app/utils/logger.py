import logging
import logging.config
import json
from pathlib import Path
from datetime import datetime
import threading


class SingletonLogger:
    """
    Singleton logger that ensures only one logger instance is created per application run.
    """
    _instance = None
    _lock = threading.Lock()
    _logger = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SingletonLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._logger = None
                    self._initialized = True
    
    def get_logger(self, name: str = "asset_management") -> logging.Logger:
        """
        Get the singleton logger instance.
        
        Args:
            name (str): Logger name (ignored in singleton pattern)
            
        Returns:
            logging.Logger: The singleton logger instance
        """
        if self._logger is None:
            with self._lock:
                if self._logger is None:
                    self._logger = self._create_logger()
        return self._logger
    
    def _create_logger(self) -> logging.Logger:
        """
        Create the singleton logger with file and console handlers.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logger
        logger = logging.getLogger("asset_management")
        logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = JsonFormatter({
            "level": "levelname",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "message": "message"
        })
        
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create file handler with fixed filename (clears on each run)
        log_filename = "logs/asset_management.log"
        file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Create error file handler with fixed filename (clears on each run)
        error_log_filename = "logs/errors.log"
        error_file_handler = logging.FileHandler(error_log_filename, mode='w', encoding='utf-8')
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        logger.addHandler(error_file_handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger





class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.

    @param dict fmt_dict: Key: logging format attribute pairs. Defaults to {"message": "message"}.
    @param str time_format: time.strftime() format string. Default: "%Y-%m-%dT%H:%M:%S"
    @param str msec_format: Microsecond formatting. Appended at the end. Default: "%s.%03dZ"
    """
    def __init__(self, fmt_dict: dict = None, time_format: str = "%Y-%m-%dT%H:%M:%S", msec_format: str = "%s.%03dZ"):
        self.fmt_dict = fmt_dict if fmt_dict is not None else {"message": "message"}
        self.default_time_format = time_format
        self.default_msec_format = msec_format
        self.datefmt = None

    def usesTime(self) -> bool:
        """
        Overwritten to look for the attribute in the format dict values instead of the fmt string.
        """
        return "asctime" in self.fmt_dict.values()

    def formatMessage(self, record) -> dict:
        """
        Overwritten to return a dictionary of the relevant LogRecord attributes instead of a string. 
        KeyError is raised if an unknown attribute is provided in the fmt_dict. 
        """
        return {fmt_key: record.__dict__[fmt_val] for fmt_key, fmt_val in self.fmt_dict.items()}

    def format(self, record) -> str:
        """
        Mostly the same as the parent's class method, the difference being that a dict is manipulated and dumped as JSON
        instead of a string.
        """
        record.message = record.getMessage()
        
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        message_dict = self.formatMessage(record)

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(message_dict, default=str)


def setup_logging_from_config(config_file: str = "app/utils/logging_config.json") -> None:
    """
    Setup logging configuration from a JSON config file.
    This function is deprecated in favor of the singleton logger pattern.
    
    Args:
        config_file (str): Path to the logging configuration JSON file.
    """
    # This function is kept for backward compatibility but does nothing
    # The singleton logger handles all logging configuration
    pass


def create_logger(name: str = "asset_management", level: str = "INFO", 
                 log_file: str = None, console_output: bool = True) -> logging.Logger:
    """
    Create and configure a logger using the JsonFormatter.
    
    Args:
        name (str): Name of the logger. Defaults to "asset_management".
        level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to "INFO".
        log_file (str): Path to log file. If None, no file handler is added.
        console_output (bool): Whether to add console output. Defaults to True.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter with comprehensive log information
    formatter = JsonFormatter({
        "timestamp": "asctime",
        "level": "levelname",
        "logger": "name",
        "module": "module",
        "function": "funcName",
        "line": "lineno",
        "message": "message"
    })
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "asset_management") -> logging.Logger:
    """
    Get the singleton logger instance.
    
    Args:
        name (str): Logger name (ignored in singleton pattern)
    
    Returns:
        logging.Logger: The singleton logger instance
    """
    return SingletonLogger().get_logger(name)