# ui/dialogs.py
"""Модуль диалоговых окон"""

import os
import base64

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFontComboBox, QSpinBox, QTextBrowser, QCheckBox,
    QComboBox, QFrame, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from app.i18n import tr
from app.resources import ICON_PATH, get_app_icon


# ==================== ЕДИНЫЙ СТИЛЬ HTML-ОКОН ====================
# Все окна с QTextBrowser (О программе, история, документация, шорткаты)
# строят CSS из шрифта приложения и текущей темы — поэтому выглядят
# одинаково со всем интерфейсом и реагируют на смену шрифта/темы.

def _doc_font():
    """(family, point_size) текущего шрифта приложения."""
    try:
        from PyQt5.QtWidgets import QApplication
        f = QApplication.instance().font()
        pt = f.pointSize()
        return f.family().replace("'", ""), pt if pt > 0 else 10
    except Exception:
        return "Segoe UI", 10


def _doc_palette(theme: str) -> dict:
    """Цвета HTML под тему (те же оттенки, что в ui/styles.py)."""
    if theme == "dark":
        return {"bg": "#1e1e1e", "text": "#f0f0f0", "muted": "#aaaaaa",
                "accent": "#4da6ff", "card": "#2a2a2a", "border": "#444444",
                "ok": "#7dd87d"}
    return {"bg": "#ffffff", "text": "#333333", "muted": "#666666",
            "accent": "#0066cc", "card": "#f8f9fa", "border": "#e0e0e0",
            "ok": "#4caf50"}


def _doc_base_css(theme: str) -> str:
    """Общий CSS: шрифт приложения + палитра темы."""
    fam, pt = _doc_font()
    pal = _doc_palette(theme)
    return (
        "body {{ font-family: '{fam}', sans-serif; font-size: {pt}pt;"
        " color: {text}; background: {bg}; margin: 0;"
        " padding: 12px 16px; line-height: 1.5; }}"
        "h1 {{ font-size: {h1}pt; font-weight: 600; margin: 0; color: {text}; }}"
        "h2 {{ font-size: {h2}pt; font-weight: 600; color: {text};"
        " border-bottom: 1px solid {border}; padding-bottom: 5px;"
        " margin-top: 22px; margin-bottom: 10px; }}"
        "h3 {{ font-size: {h3}pt; color: {accent}; }}"
        "a {{ color: {accent}; text-decoration: none; }}"
        "hr {{ border: none; border-top: 1px solid {border}; margin: 16px 0; }}"
        ".muted {{ color: {muted}; font-size: {small}pt; }}"
    ).format(fam=fam, pt=pt, h1=pt + 8, h2=pt + 3, h3=pt + 1, small=max(8, pt - 1),
             text=pal["text"], bg=pal["bg"], accent=pal["accent"],
             border=pal["border"], muted=pal["muted"])


def _style_browser(browser):
    """Применяет шрифт приложения к QTextBrowser."""
    fam, pt = _doc_font()
    browser.setFont(QFont(fam, pt))


def _theme_of(parent) -> str:
    return getattr(parent, "theme", "light") or "light"


def _icon_base64() -> str:
    try:
        if os.path.exists(ICON_PATH):
            with open(ICON_PATH, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        pass
    return ""


def show_font_dialog(parent) -> bool:
    """Диалог настройки шрифта с предпросмотром."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("dlg_font_title"))
    dialog.setMinimumSize(480, 420)
    dialog.setMaximumSize(600, 500)

    main_layout = QVBoxLayout(dialog)
    main_layout.setSpacing(16)
    main_layout.setContentsMargins(20, 20, 20, 20)

    # === ЗАГОЛОВОК ===
    header = QLabel("🔤 " + tr("dlg_font_title"))
    font = QFont()
    font.setPointSize(16)
    font.setBold(True)
    header.setFont(font)
    header.setAlignment(Qt.AlignCenter)
    main_layout.addWidget(header)

    # === РАЗДЕЛИТЕЛЬ ===
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    main_layout.addWidget(line)

    # === ФОРМА НАСТРОЕК ===
    from PyQt5.QtWidgets import QFormLayout
    form_layout = QFormLayout()
    form_layout.setSpacing(12)
    form_layout.setLabelAlignment(Qt.AlignRight)
    form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

    font_combo = QFontComboBox()
    font_combo.setCurrentFont(QFont(parent.font_family))
    font_combo.setMinimumHeight(32)
    form_layout.addRow(tr("dlg_font_family"), font_combo)

    size_spin = QSpinBox()
    size_spin.setRange(8, 72)
    size_spin.setValue(parent.font_size)
    size_spin.setSuffix(" pt")
    size_spin.setMinimumHeight(32)
    size_spin.setMinimumWidth(80)
    form_layout.addRow(tr("dlg_font_size"), size_spin)

    style_combo = QComboBox()
    style_combo.addItems([tr("dlg_font_style_normal"), tr("dlg_font_style_italic"),
                          tr("dlg_font_style_bold"), tr("dlg_font_style_bold_italic")])
    style_combo.setMinimumHeight(32)
    style_combo.setMinimumWidth(150)
    current_style_idx = 0
    if parent.font_bold and parent.font_italic:
        current_style_idx = 3
    elif parent.font_bold:
        current_style_idx = 2
    elif parent.font_italic:
        current_style_idx = 1
    style_combo.setCurrentIndex(current_style_idx)
    form_layout.addRow(tr("dlg_font_style"), style_combo)

    main_layout.addLayout(form_layout)

    # === ПРЕДПРОСМОТР ===
    preview_frame = QFrame()
    preview_frame.setMinimumHeight(80)
    preview_frame.setFrameShape(QFrame.StyledPanel)

    preview_label = QLabel(f"{tr('dlg_font_preview')}\n{tr('dlg_font_preview_ru')}")
    preview_label.setAlignment(Qt.AlignCenter)
    preview_label.setWordWrap(True)

    preview_layout = QVBoxLayout(preview_frame)
    preview_layout.setContentsMargins(12, 12, 12, 12)
    preview_layout.addWidget(preview_label)

    main_layout.addWidget(preview_frame)

    # === КНОПКИ ===
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(10)

    reset_btn = QPushButton(tr("dlg_reset_default"))
    reset_btn.setMinimumHeight(36)
    reset_btn.setMinimumWidth(120)
    btn_layout.addWidget(reset_btn)

    btn_layout.addStretch()

    cancel_btn = QPushButton(tr("dlg_cancel"))
    cancel_btn.setMinimumHeight(36)
    cancel_btn.setMinimumWidth(100)
    btn_layout.addWidget(cancel_btn)

    accept_btn = QPushButton(tr("dlg_accept"))
    accept_btn.setMinimumHeight(36)
    accept_btn.setMinimumWidth(100)
    accept_btn.setDefault(True)
    btn_layout.addWidget(accept_btn)

    main_layout.addLayout(btn_layout)

    # === СТИЛИ ПОД ТЕМУ ===
    is_dark = parent.theme == "dark"
    bg_color = "#1e1e1e" if is_dark else "#ffffff"
    text_color = "#f0f0f0" if is_dark else "#333333"
    border_color = "#444444" if is_dark else "#dddddd"
    preview_bg = "#2a2a2a" if is_dark else "#f8f9fa"
    preview_border = "#555555" if is_dark else "#cccccc"

    dialog.setStyleSheet(f"""
        QDialog {{
            background-color: {bg_color};
            color: {text_color};
        }}
        QLabel {{
            color: {text_color};
        }}
        QFrame {{
            border: 1px solid {border_color};
            border-radius: 10px;
        }}
        QPushButton {{
            background-color: #0066cc;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: #0055aa;
        }}
        QPushButton#secondary {{
            background-color: #6c757d;
        }}
        QPushButton#secondary:hover {{
            background-color: #5a6268;
        }}
        QComboBox, QFontComboBox, QSpinBox {{
            background-color: {preview_bg};
            color: {text_color};
            border: 1px solid {preview_border};
            border-radius: 6px;
            padding: 4px 8px;
        }}
    """)
    reset_btn.setObjectName("secondary")

    # === ЛОГИКА ===
    def update_preview():
        family = font_combo.currentFont().family()
        size = size_spin.value()
        f = QFont(family, size)

        style_idx = style_combo.currentIndex()
        if style_idx == 1:
            f.setItalic(True)
        elif style_idx == 2:
            f.setBold(True)
        elif style_idx == 3:
            f.setBold(True)
            f.setItalic(True)

        preview_label.setFont(f)

    font_combo.currentFontChanged.connect(lambda f: update_preview())
    size_spin.valueChanged.connect(lambda v: update_preview())
    style_combo.currentTextChanged.connect(lambda s: update_preview())
    update_preview()

    def reset_to_default():
        font_combo.setCurrentFont(QFont("Bahnschrift SemiBold"))
        size_spin.setValue(14)
        style_combo.setCurrentIndex(0)
        update_preview()

    reset_btn.clicked.connect(reset_to_default)
    cancel_btn.clicked.connect(dialog.reject)
    accept_btn.clicked.connect(dialog.accept)

    if dialog.exec_() == QDialog.Accepted:
        parent.font_family = font_combo.currentFont().family()
        parent.font_size = size_spin.value()

        style_idx = style_combo.currentIndex()
        parent.font_bold = False
        parent.font_italic = False

        if style_idx == 1:
            parent.font_italic = True
        elif style_idx == 2:
            parent.font_bold = True
        elif style_idx == 3:
            parent.font_bold = True
            parent.font_italic = True

        parent.apply_font_settings()
        return True
    return False

def about_html(parent) -> str:
    """HTML «О программе» в шрифте приложения и палитре темы."""
    theme = _theme_of(parent)
    pal = _doc_palette(theme)
    fam, pt = _doc_font()
    icon_base64 = _icon_base64()

    build_parts = parent.BUILD_VERSION.split(".")
    build_number = build_parts[-1] if build_parts else "1"

    shortcuts = [
        ("Ctrl+E", tr("shortcut_export")),
        ("Ctrl+O", tr("shortcut_open")),
        ("Ctrl+Q", tr("shortcut_exit")),
        ("Ctrl+T", tr("shortcut_theme")),
        ("Ctrl+↑", tr("shortcut_font_up")),
        ("Ctrl+↓", tr("shortcut_font_down")),
        ("F1", tr("shortcut_help")),
    ]

    shortcuts_html = ""
    for key, desc in shortcuts:
        shortcuts_html += f"""
        <tr>
            <td style="padding: 4px 10px; font-weight: bold; text-align: left;">{key}</td>
            <td style="padding: 4px 10px; text-align: left;">{desc}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <style>
            {_doc_base_css(theme)}
            body {{ text-align: center; padding: 20px; }}
            .icon-container {{ text-align: center; margin-bottom: 15px; }}
            .icon-container img {{ width: 100px; height: 100px; }}
            .title {{ font-size: {pt + 8}pt; font-weight: bold; margin-bottom: 5px; }}
            .year {{ font-size: {pt + 1}pt; color: {pal['muted']}; margin-bottom: 12px; }}
            .description {{ font-size: {pt + 1}pt; color: {pal['text']}; margin: 0 auto 16px auto; max-width: 420px; }}
            .info-table {{ margin: 0 auto; border-collapse: collapse; min-width: 300px; }}
            .info-table td {{ padding: 6px 10px; font-size: {pt + 1}pt; text-align: left; }}
            .label {{ font-weight: bold; }}
            .divider {{ margin: 20px auto; width: 80%; }}
            .shortcuts-title {{ font-size: {pt + 3}pt; font-weight: bold; margin-bottom: 10px; }}
            .shortcuts-table {{ margin: 0 auto; border-collapse: collapse; min-width: 300px; }}
            .shortcuts-table td {{ padding: 4px 10px; font-size: {pt}pt; text-align: left; }}
        </style>
    </head>
    <body>
        <div class="icon-container">
            <img src="data:image/png;base64,{icon_base64}" alt="Icon" />
        </div>
        <div class="title">{tr('app_title')}</div>
        <div class="year">© 2026</div>
        <div class="description">{tr('about_description')}</div>
        <table class="info-table">
            <tr><td class="label">{tr('author_label')}:</td><td><a href="https://goo.su/vTQAn">Kenig Theodor</a></td></tr>
            <tr><td class="label">{tr('build_date_label')}:</td><td>{parent.BUILD_DATE}</td></tr>
            <tr><td class="label">{tr('version_label')}:</td><td>{parent.VERSION} build {build_number}</td></tr>
        </table>
        <hr class="divider">
        <div class="shortcuts-title">{tr('menu_shortcuts')}</div>
        <table class="shortcuts-table">
            {shortcuts_html}
        </table>
    </body>
    </html>
    """


def show_about_dialog(parent):
    """Показ информации о программе с таблицей и горячими клавишами."""
    html = about_html(parent)

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("dlg_about_title"))
    dialog.setWindowIcon(get_app_icon())
    dialog.setMinimumSize(500, 600)

    layout = QVBoxLayout(dialog)

    browser = QTextBrowser()
    browser.setHtml(html)
    browser.setOpenExternalLinks(True)
    _style_browser(browser)
    layout.addWidget(browser)

    close_btn = QPushButton(tr("dlg_close"))
    close_btn.setFixedHeight(35)
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignCenter)

    dialog.exec_()


def changelog_html(theme: str = "light") -> str:
    """HTML истории изменений в палитре темы."""
    from app.changelog import CHANGELOG  # лениво: список большой, нужен редко
    pal = _doc_palette(theme)
    html = f"<h2>{tr('menu_changelog')}</h2>"

    for entry in CHANGELOG:
        html += f"<h3>{entry['version']} ({entry['date']})</h3><ul>"
        for change in entry['changes']:
            if change.startswith("+"):
                html += f"<li style='color: {pal['ok']};'>➕ {change[1:].strip()}</li>"
            elif change.startswith("*"):
                html += f"<li>🔧 {change[1:].strip()}</li>"
            else:
                html += f"<li>{change}</li>"
        html += "</ul><hr>"
    return (
        "<html><head><style>"
        + _doc_base_css(theme)
        + "li {{ margin-bottom: 4px; }}"
        + "</style></head><body>" + html + "</body></html>"
    )


def show_changelog_dialog(parent):
    """Показ истории изменений."""
    theme = _theme_of(parent)
    html = changelog_html(theme)

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("dlg_changelog_title"))
    dialog.setMinimumSize(600, 700)
    layout = QVBoxLayout(dialog)
    browser = QTextBrowser()
    browser.setHtml(html)
    _style_browser(browser)
    layout.addWidget(browser)
    close_btn = QPushButton(tr("dlg_close"))
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    dialog.exec_()


def documentation_html(parent) -> str:
    """HTML документации в шрифте приложения и палитре темы."""
    from app.i18n import tr

    theme = _theme_of(parent)
    pal = _doc_palette(theme)
    fam, pt = _doc_font()
    icon_base64 = _icon_base64()

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            {_doc_base_css(theme)}
            body {{
                font-family: '{fam}', sans-serif;
                padding: 16px 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 16px;
            }}
            .header img {{
                width: 48px;
                height: 48px;
                margin-bottom: 6px;
            }}
            .header .version {{
                font-size: {pt}pt;
                color: {pal['muted']};
                margin-top: 4px;
            }}
            .step {{
                margin-bottom: 8px;
                font-size: {pt}pt;
            }}
            .step-num {{
                font-weight: 600;
                color: {pal['accent']};
            }}
            .feature {{
                margin-bottom: 12px;
            }}
            .feature-header {{
                font-size: {pt + 1}pt;
                font-weight: 600;
                margin-bottom: 2px;
            }}
            .feature-desc {{
                font-size: {max(8, pt - 1)}pt;
                color: {pal['muted']};
                font-style: italic;
                margin-left: 2px;
            }}
            .faq-q {{
                font-weight: 600;
                color: {pal['accent']};
                font-size: {pt}pt;
                margin-top: 10px;
                margin-bottom: 3px;
            }}
            .faq-a {{
                font-size: {max(8, pt - 1)}pt;
                color: {pal['muted']};
                margin-left: 8px;
                margin-bottom: 8px;
            }}
            .legal {{
                margin-top: 14px;
                padding: 12px 14px;
                background: {pal['card']};
                border-radius: 8px;
                border: 1px solid {pal['border']};
            }}
            .legal-title {{
                font-weight: 600;
                font-size: {pt}pt;
                margin-bottom: 4px;
                color: {pal['text']};
            }}
            .legal-text {{
                font-size: {max(8, pt - 1)}pt;
                color: {pal['muted']};
                line-height: 1.4;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="data:image/png;base64,{icon_base64}" alt="Icon" />
            <h1>{tr('app_title')}</h1>
            <div class="version">v{parent.VERSION}</div>
        </div>

        <h2>🚀 {tr('doc_quick_start_title')}</h2>
        <div class="step"><span class="step-num">{tr('doc_step_label')} 1:</span> {tr('doc_step_1')}</div>
        <div class="step"><span class="step-num">{tr('doc_step_label')} 2:</span> {tr('doc_step_2')}</div>
        <div class="step"><span class="step-num">{tr('doc_step_label')} 3:</span> {tr('doc_step_3')}</div>

        <h2>✨ {tr('doc_features_title')}</h2>
        <div class="feature">
            <div class="feature-header">⏱️ {tr('doc_feature_1_title')}</div>
            <div class="feature-desc">{tr('doc_feature_1_desc')}</div>
        </div>
        <div class="feature">
            <div class="feature-header">📊 {tr('doc_feature_2_title')}</div>
            <div class="feature-desc">{tr('doc_feature_2_desc')}</div>
        </div>
        <div class="feature">
            <div class="feature-header">🎨 {tr('doc_feature_3_title')}</div>
            <div class="feature-desc">{tr('doc_feature_3_desc')}</div>
        </div>
        <div class="feature">
            <div class="feature-header">💾 {tr('doc_feature_4_title')}</div>
            <div class="feature-desc">{tr('doc_feature_4_desc')}</div>
        </div>
        <div class="feature">
            <div class="feature-header">🔍 {tr('doc_feature_5_title')}</div>
            <div class="feature-desc">{tr('doc_feature_5_desc')}</div>
        </div>
        <div class="feature">
            <div class="feature-header">🌐 {tr('doc_feature_6_title')}</div>
            <div class="feature-desc">{tr('doc_feature_6_desc')}</div>
        </div>

        <hr>

        <h2>❓ FAQ</h2>
        <div class="faq-q">{tr('faq_q1')}</div>
        <div class="faq-a">{tr('faq_a1')}</div>
        <div class="faq-q">{tr('faq_q2')}</div>
        <div class="faq-a">{tr('faq_a2')}</div>
        <div class="faq-q">{tr('faq_q3')}</div>
        <div class="faq-a">{tr('faq_a3')}</div>
        <div class="faq-q">{tr('faq_q4')}</div>
        <div class="faq-a">{tr('faq_a4')}</div>
        <div class="faq-q">{tr('faq_q5')}</div>
        <div class="faq-a">{tr('faq_a5')}</div>
        <div class="faq-q">{tr('faq_q6')}</div>
        <div class="faq-a">{tr('faq_a6')}</div>

        <hr>

        <h2>🛠 {tr('doc_troubleshooting_title')}</h2>
        <div class="faq-q">{tr('doc_trouble_1_q')}</div>
        <div class="faq-a">{tr('doc_trouble_1_a')}</div>
        <div class="faq-q">{tr('doc_trouble_2_q')}</div>
        <div class="faq-a">{tr('doc_trouble_2_a')}</div>
        <div class="faq-q">{tr('doc_trouble_3_q')}</div>
        <div class="faq-a">{tr('doc_trouble_3_a')}</div>

        <div class="legal">
            <div class="legal-title">© {tr('copyright_title')}</div>
            <div class="legal-text">{tr('copyright_text')}</div>
        </div>
        <div class="legal">
            <div class="legal-title">📋 {tr('terms_title')}</div>
            <div class="legal-text">{tr('terms_text')}</div>
        </div>
        <div class="legal">
            <div class="legal-title">📝 {tr('user_agreement_title')}</div>
            <div class="legal-text">{tr('user_agreement_text')}</div>
        </div>
    </body>
    </html>
    """


def show_documentation_dialog(parent):
    """Показ документации в едином стиле с отступами и логотипом."""
    from app.i18n import tr

    html = documentation_html(parent)

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("dlg_docs_title"))
    dialog.setMinimumSize(560, 640)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(12)

    browser = QTextBrowser()
    browser.setHtml(html)
    browser.setOpenExternalLinks(True)
    # Шрифт приложения (семейство и размер — из CSS выше)
    _style_browser(browser)
    layout.addWidget(browser)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    close_btn = QPushButton(tr("dlg_close"))
    close_btn.setMinimumHeight(36)
    close_btn.setMinimumWidth(100)
    close_btn.clicked.connect(dialog.accept)
    btn_layout.addWidget(close_btn)
    btn_layout.addStretch()

    layout.addLayout(btn_layout)
    dialog.exec_()

def shortcuts_html(theme: str = "light") -> str:
    """HTML горячих клавиш в шрифте приложения."""
    shortcuts = [
        ("Ctrl+E", tr("shortcut_export")),
        ("Ctrl+O", tr("shortcut_open")),
        ("Ctrl+Q", tr("shortcut_exit")),
        ("Ctrl+T", tr("shortcut_theme")),
        ("Ctrl+↑", tr("shortcut_font_up")),
        ("Ctrl+↓", tr("shortcut_font_down")),
        ("F1", tr("shortcut_help")),
    ]

    rows = ""
    for key, desc in shortcuts:
        rows += f"<tr><td style='font-weight:bold;'>{key}</td><td>{desc}</td></tr>"
    return (
        "<html><head><style>" + _doc_base_css(theme)
        + "td {{ padding: 4px 10px; }}"
        + "</style></head><body>"
        + f"<h2>{tr('menu_shortcuts')}</h2><table>{rows}</table>"
        + "</body></html>"
    )


def show_shortcuts_dialog(parent):
    """Показ горячих клавиш."""
    html = shortcuts_html(_theme_of(parent))

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("dlg_shortcuts_title"))
    dialog.setMinimumSize(350, 400)
    layout = QVBoxLayout(dialog)
    browser = QTextBrowser()
    browser.setHtml(html)
    _style_browser(browser)
    layout.addWidget(browser)
    close_btn = QPushButton(tr("dlg_close"))
    close_btn.clicked.connect(dialog.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    dialog.exec_()


# ==================== УСЛОВИЯ ИСПОЛЬЗОВАНИЯ (первый запуск) ====================

LEGAL_KEY = "legal/accepted"


def is_legal_accepted() -> bool:
    """Приняты ли условия текущей сборки (QSettings, привязка к версии)."""
    from PyQt5.QtCore import QSettings
    from app.config import BUILD_VERSION
    from ui.gui import SETTINGS_ORG, SETTINGS_APP
    return QSettings(SETTINGS_ORG, SETTINGS_APP).value(LEGAL_KEY, "") == BUILD_VERSION


def mark_legal_accepted():
    """Запоминает принятие условий текущей сборки."""
    from PyQt5.QtCore import QSettings
    from app.config import BUILD_VERSION
    from ui.gui import SETTINGS_ORG, SETTINGS_APP
    QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(LEGAL_KEY, BUILD_VERSION)


def legal_html(parent=None) -> str:
    """HTML условий: копирайт + terms + соглашение + MIT, в теме и шрифте."""
    theme = _theme_of(parent)
    pal = _doc_palette(theme)
    fam, pt = _doc_font()
    css = _doc_base_css(theme) + (
        ".legal {{ margin-top: 0; margin-bottom: 14px; padding: 12px 14px;"
        " background: {card}; border-radius: 8px;"
        " border: 1px solid {border}; }}"
        ".legal-title {{ font-weight: 600; font-size: {pt}pt;"
        " margin-bottom: 4px; color: {text}; }}"
        ".legal-text {{ font-size: {small}pt; color: {muted};"
        " line-height: 1.4; }}"
    ).format(card=pal["card"], border=pal["border"], pt=pt,
             small=max(8, pt - 1), text=pal["text"], muted=pal["muted"])
    body = (
        "<h2>{t_copy} — {app}</h2>"
        "<div class='legal'><div class='legal-title'>© {t_copy}</div>"
        "<div class='legal-text'>{t_copy_text}</div></div>"
        "<div class='legal'><div class='legal-title'>📋 {t_terms}</div>"
        "<div class='legal-text'>{t_terms_text}</div></div>"
        "<div class='legal'><div class='legal-title'>📝 {t_agree}</div>"
        "<div class='legal-text'>{t_agree_text}</div></div>"
        "<div class='legal'><div class='legal-title'>MIT License</div>"
        "<div class='legal-text'>Copyright (c) 2026 Kenig Theodor<br><br>"
        "Permission is hereby granted, free of charge, to any person obtaining "
        "a copy of this software and associated documentation files (the "
        "“Software”), to deal in the Software without restriction, including "
        "without limitation the rights to use, copy, modify, merge, publish, "
        "distribute, sublicense, and/or sell copies of the Software, and to "
        "permit persons to whom the Software is furnished to do so, subject "
        "to the following conditions:<br><br>"
        "The above copyright notice and this permission notice shall be "
        "included in all copies or substantial portions of the "
        "Software.<br><br>"
        "THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, "
        "EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF "
        "MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND "
        "NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS "
        "BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN "
        "ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN "
        "CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE "
        "SOFTWARE.</div></div>"
    ).format(
        t_copy=tr("copyright_title"), app=tr("app_title"),
        t_copy_text=tr("copyright_text"),
        t_terms=tr("terms_title"), t_terms_text=tr("terms_text"),
        t_agree=tr("user_agreement_title"),
        t_agree_text=tr("user_agreement_text"),
    )
    return ("<html><head><style>" + css + "</style></head><body>"
            + body + "</body></html>")


def _build_legal_dialog(parent=None):
    """Строит диалог условий БЕЗ exec (для тестов и показа).

    Возвращает (dialog, browser, checkbox, accept_btn, hint).
    Галочка включается только после прокрутки текста до конца.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr("legal_title"))
    dialog.setMinimumSize(520, 560)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(10)

    browser = QTextBrowser()
    browser.setHtml(legal_html(parent))
    browser.setOpenExternalLinks(True)
    _style_browser(browser)
    layout.addWidget(browser, 1)

    hint = QLabel(tr("legal_hint"))
    hint.setWordWrap(True)
    layout.addWidget(hint)

    checkbox = QCheckBox(tr("legal_checkbox"))
    checkbox.setEnabled(False)
    layout.addWidget(checkbox)

    btn_layout = QHBoxLayout()
    decline_btn = QPushButton(tr("dlg_cancel"))
    decline_btn.setMinimumHeight(36)
    decline_btn.setMinimumWidth(120)
    decline_btn.clicked.connect(dialog.reject)
    btn_layout.addWidget(decline_btn)
    btn_layout.addStretch()
    accept_btn = QPushButton(tr("dlg_accept"))
    accept_btn.setMinimumHeight(36)
    accept_btn.setMinimumWidth(120)
    accept_btn.setDefault(True)
    accept_btn.setEnabled(False)
    accept_btn.clicked.connect(dialog.accept)
    btn_layout.addWidget(accept_btn)
    layout.addLayout(btn_layout)

    bar = browser.verticalScrollBar()

    def _on_scroll(_value=None):
        # До раскладки maximum()==0 — тогда ещё не решаем
        if bar.maximum() <= 0:
            return
        if bar.value() >= bar.maximum() and not checkbox.isEnabled():
            checkbox.setEnabled(True)
            hint.setText("")

    bar.valueChanged.connect(_on_scroll)
    bar.rangeChanged.connect(_on_scroll)
    # Если текст влез без прокрутки — разрешаем сразу (после раскладки)
    QTimer.singleShot(500, _on_scroll)
    checkbox.toggled.connect(lambda checked: accept_btn.setEnabled(checked))

    return dialog, browser, checkbox, accept_btn, hint


def show_legal_dialog(parent=None) -> bool:
    """Показывает условия. True = принято (и запомнено), False = отказ."""
    dialog, _browser, _checkbox, _accept, _hint = _build_legal_dialog(parent)
    if dialog.exec_() == QDialog.Accepted:
        mark_legal_accepted()
        return True
    return False