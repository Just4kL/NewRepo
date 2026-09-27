# app/logger.py
"""Модуль настройки логирования"""

import logging
import sys
import traceback
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")


def setup_logging():
    """Настраивает логирование: создаёт папку logs и файл с датой."""
    LOG_DIR.mkdir(exist_ok=True)
    log_filename = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Устанавливаем глобальный обработчик исключений
    def global_exception_hook(exc_type, exc_value, exc_tb):
        """Глобальный обработчик необработанных исключений."""
        logger = logging.getLogger(__name__)

        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Необработанное исключение:\n{error_msg}")

        # Записываем в отдельный файл ошибок
        error_file = LOG_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Ошибка: {exc_type.__name__}: {exc_value}\n\n")
            f.write(error_msg)

        logger.critical(f"Ошибка сохранена в: {error_file}")

        # Вызываем стандартный обработчик
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    # sys.excepthook устанавливается в main.py (Qt-совместимый обработчик)
    # sys.excepthook = global_exception_hook

    logger = logging.getLogger(__name__)
    logger.info(f"Логирование настроено. Файл: {log_filename}")

    return logger
