import logging


class CustomLogger:
    def __init__(self, name="logger", level=logging.DEBUG, log_file=None) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if log_file:
            handler = logging.FileHandler(log_file)
        else:
            handler = logging.StreamHandler()

        handler.setLevel(level)

        # Create a formatter and set it for the handler
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def debug(self, message) -> None:
        self.logger.debug(message)

    def info(self, message) -> None:
        self.logger.info(message)

    def warning(self, message) -> None:
        self.logger.warning(message)

    def error(self, message) -> None:
        self.logger.error(message)

    def critical(self, message) -> None:
        self.logger.critical(message)

    def exception(self, message) -> None:
        self.logger.exception(message)
