from apps.shared.src.infra.logging.i_logger import ILogger
from apps.shared.src.infra.logging.logger_config import setup_logger
from apps.shared.src.infra.logging.structlog_logger import StructlogLogger

__all__ = ["ILogger", "StructlogLogger", "setup_logger"]
