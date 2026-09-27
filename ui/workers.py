# ui/workers.py
"""Модуль для асинхронных операций"""

import asyncio
import logging
from PyQt5.QtCore import pyqtSignal, QObject

logger = logging.getLogger(__name__)


class AsyncWorker(QObject):
    """Класс для выполнения асинхронных операций в отдельном потоке."""
    finished = pyqtSignal(object)
    error = pyqtSignal(object)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                coro = self.coro_func(*self.args, **self.kwargs)
                result = loop.run_until_complete(coro)
                
                if not self._is_cancelled:
                    self.finished.emit(result)
            finally:
                loop.close()
                
        except Exception as e:
            logger.exception("Ошибка в асинхронном воркере")
            if not self._is_cancelled:
                self.error.emit(e)


class ProgressBridge(QObject):
    """Мост прогресса из рабочего потока в GUI-поток.

    Создаётся в GUI-потоке (родитель — окно), метод report() дёргается
    из асинхронного кода в воркере. Сигнал tick автоматически идёт
    через queued-соединение, поэтому слот выполняется в GUI-потоке
    и может трогать виджеты напрямую.
    """
    tick = pyqtSignal(int, int)  # done, total; total<=0 — неопределённый режим

    def report(self, done: int, total: int):
        try:
            self.tick.emit(int(done), int(total))
        except Exception:
            pass  # окно уже может закрываться — прогресс не критичен