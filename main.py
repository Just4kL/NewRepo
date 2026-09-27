# main.py
"""Точка входа в приложение Steam Playtime Viewer"""

import os
import sys
import traceback

if "__compiled__" in globals():
    # Nuitka-onefile: зависимые DLL (OpenSSL, expat, …) лежат в
    # распаковочном каталоге рядом с __file__, а не рядом с exe.
    # Добавляем его в поиск ДО первого импорта ssl. Под CPython
    # и PyInstaller условие ложно — поведение не меняется.
    try:
        os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass

from PyQt5.QtWidgets import QMessageBox

from app.logger import setup_logging
from app.config import VERSION
from ui.gui import Gui
from ui.main_window import MainWindow


def excepthook(exc_type, exc_value, exc_tb):
    """Обработчик исключений для Qt."""
    import logging
    logger = logging.getLogger(__name__)
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Qt Exception:\n{error_msg}")

    QMessageBox.critical(
        None,
        "Ошибка",
        f"Произошла ошибка:\n{exc_value}\n\nПодробности в лог-файле."
    )

    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    logger = setup_logging()
    logger.info(f"Запуск Steam Playtime Viewer v{VERSION}")

    # Устанавливаем обработчик исключений Qt
    sys.excepthook = excepthook

    # Вся сборка интерфейса — через GUI-агрегатор
    app = Gui.create_application(sys.argv)

    language = Gui.ask_language()
    if language is None:
        sys.exit(0)

    # Язык — сразу, чтобы условия показались на выбранном языке
    from app.i18n import set_language
    set_language(language)

    # Условия использования: первый запуск и каждая новая сборка.
    # Отказ — выход без запуска программы.
    from ui.dialogs import is_legal_accepted, show_legal_dialog
    if not is_legal_accepted():
        logger.info("Показ условий использования")
        if not show_legal_dialog():
            logger.info("Условия отклонены — выход")
            sys.exit(0)

    try:
        window = MainWindow(language)
        window.setWindowOpacity(1.00)
        window.show()

        exit_code = app.exec_()
        logger.info("Программа завершена нормально")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
