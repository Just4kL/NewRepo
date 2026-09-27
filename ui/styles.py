# ui/styles.py
"""Модуль стилей и тем"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor, QPalette


def apply_theme(app: QApplication, theme: str):
    """Применяет светлую или тёмную тему."""
    if theme == "dark":
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.Base, QColor(20, 20, 20))
        palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipText, QColor(20, 20, 20))
        palette.setColor(QPalette.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
        palette.setColor(QPalette.BrightText, QColor(255, 80, 80))
        palette.setColor(QPalette.Highlight, QColor(77, 166, 255))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        app.setPalette(palette)
    else:
        app.setPalette(app.style().standardPalette())


def get_app_styles(theme: str) -> str:
    """Возвращает CSS-строку со стилями."""
    if theme == "dark":
        return """
            /* Общий фон с градиентом */
            QMainWindow, QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #2b2b2b, stop:1 #1a1a1a);
            }
            QWidget {
                color: #f0f0f0;
            }
            QPushButton {
                border-radius: 8px;
            }
            QLineEdit {
                border-radius: 6px;
            }
            QComboBox {
                border-radius: 6px;
            }
            QGroupBox {
                border-radius: 10px;
            }
            QTableWidget {
                border-radius: 8px;
            }
            QListWidget {
                border-radius: 10px;
            }
            QPushButton {
                border-radius: 8px;
            }
            QLineEdit {
                border-radius: 6px;
            }
            QComboBox {
                border-radius: 6px;
            }
            QGroupBox {
                border-radius: 10px;
            }
            QTableWidget {
                border-radius: 8px;
            }
            QListWidget {
                border-radius: 10px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(30, 30, 30, 0.8);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4da6ff;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #777777;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #777777;
                border-color: #3a3a3a;
            }
            QPushButton#primary {
                background-color: #4da6ff;
                color: #1a1a1a;
                border-color: #3d96ef;
            }
            QPushButton#primary:hover {
                background-color: #3d96ef;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 10px;
                selection-background-color: #4da6ff;
            }
            QLineEdit:focus {
                border-color: #4da6ff;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: #f0f0f0;
                gridline-color: #444444;
                alternate-background-color: #252525;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #f0f0f0;
                padding: 6px;
                border: 1px solid #444444;
            }
            QComboBox {
                background-color: #2a2a2a;
                color: #f0f0f0;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox:hover {
                border-color: #777777;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #f0f0f0;
                selection-background-color: #4da6ff;
            }
            QLabel {
                color: #f0f0f0;
            }
            QToolTip {
                background-color: #333333;
                color: #f0f0f0;
                border: 1px solid #555555;
            }
            QStatusBar {
                background-color: #1a1a1a;
                color: #f0f0f0;
            }
            QProgressBar {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4da6ff;
            }
            /* ===== Свободная сетка (dashboard) ===== */
            QWidget#DashboardCard {
                background: transparent;
                border: none;
            }
            QWidget#DashboardCard[dropTarget="true"] {
                border: 1px dashed #4da6ff;
                border-radius: 10px;
            }
            QLabel#GripHandle {
                color: #888888;
                font-size: 12px;
                padding: 0 4px;
            }
            QLabel#GripHandle:hover {
                color: #4da6ff;
            }
            QToolButton#CollapseButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #888888;
                font-weight: bold;
            }
            QToolButton#CollapseButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #f0f0f0;
            }
            QLabel#FooterLabel {
                color: #aaaaaa;
                font-style: italic;
            }
        """
    else:
        return """
            QWidget {
                color: #333333;
            }
            QPushButton {
                border-radius: 8px;
            }
            QLineEdit {
                border-radius: 6px;
            }
            QComboBox {
                border-radius: 6px;
            }
            QGroupBox {
                border-radius: 10px;
            }
            QTableWidget {
                border-radius: 8px;
            }
            QListWidget {
                border-radius: 10px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #0066cc;
            }
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton#primary {
                background-color: #0066cc;
                color: white;
                border-color: #0055aa;
            }
            QPushButton#primary:hover {
                background-color: #0055aa;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QLineEdit:focus {
                border-color: #0066cc;
            }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #cccccc;
                alternate-background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                color: #333333;
                padding: 6px;
                border: 1px solid #cccccc;
            }
            QComboBox {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLabel {
                color: #333333;
            }
            /* ===== Свободная сетка (dashboard) ===== */
            QWidget#DashboardCard {
                background: transparent;
                border: none;
            }
            QWidget#DashboardCard[dropTarget="true"] {
                border: 1px dashed #0066cc;
                border-radius: 10px;
            }
            QLabel#GripHandle {
                color: #999999;
                font-size: 12px;
                padding: 0 4px;
            }
            QLabel#GripHandle:hover {
                color: #0066cc;
            }
            QToolButton#CollapseButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #999999;
                font-weight: bold;
            }
            QToolButton#CollapseButton:hover {
                background-color: rgba(0, 0, 0, 0.08);
                color: #333333;
            }
            QLabel#FooterLabel {
                color: #666666;
                font-style: italic;
            }
        """