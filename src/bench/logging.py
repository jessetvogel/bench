import logging

GRAY = "\033[90m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
WHITE = "\033[37m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Formatter(logging.Formatter):
    fmt_prefix = "[" + GRAY + "%(asctime)s" + RESET + "]"
    fmt_date = "%H:%M:%S"

    FORMATS = {
        logging.INFO: fmt_prefix + " " + WHITE + "INFO" + RESET + ": %(message)s",
        logging.DEBUG: fmt_prefix + " " + BLUE + "DEBUG" + RESET + ": %(message)s",
        logging.WARNING: fmt_prefix + " " + YELLOW + "WARNING" + RESET + ": %(message)s",
        logging.ERROR: fmt_prefix + " " + RED + "ERROR" + RESET + ": %(message)s",
        logging.CRITICAL: fmt_prefix + " " + RED + "CRITICAL" + RESET + ": %(message)s",
    }

    def format(self, record):
        formatter = logging.Formatter(self.FORMATS.get(record.levelno), self.fmt_date)
        return formatter.format(record)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(Formatter())
        logger.addHandler(ch)
    return logger
