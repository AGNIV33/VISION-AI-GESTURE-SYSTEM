"""Dark theme for every window (Qt style sheet)."""

BG = "#12141a"
PANEL = "#1a1d26"
PANEL_2 = "#222633"
BORDER = "#2c3242"
TEXT = "#e8ebf2"
MUTED = "#8b92a6"
ACCENT = "#5b8cff"
GOOD = "#3ecf8e"
WARN = "#f5a524"
BAD = "#ef5b5b"

STYLE = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: {TEXT}; }}
QWidget {{ background: {BG}; }}
QDialog, QWizard, QWizardPage, QMainWindow {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QFrame {{ background: transparent; }}
QLabel#title {{ font-size: 22px; font-weight: 600; }}
QLabel#heading {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#badge {{ color: {ACCENT}; border: 1px solid {ACCENT}; border-radius: 8px; padding: 1px 7px;
                font-size: 11px; font-weight: 600; }}
QLabel#good {{ color: {GOOD}; }}
QLabel#warn {{ color: {WARN}; }}
QLabel#bad {{ color: {BAD}; }}
QLabel#big {{ font-size: 20px; font-weight: 600; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; background: {PANEL}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 9px 16px; margin-right: 2px;
                border-top-left-radius: 8px; border-top-right-radius: 8px; }}
QTabBar::tab:selected {{ background: {PANEL}; color: {TEXT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QWidget#page {{ background: {PANEL}; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
               padding: 7px 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {MUTED}; border-color: {PANEL_2}; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #7aa2ff; }}
QPushButton#primary:disabled {{ background: {PANEL_2}; color: {MUTED}; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {BORDER};
                        background: {PANEL_2}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox::indicator:disabled {{ background: {BG}; }}
QCheckBox::indicator:checked:disabled {{ background: #3b4f86; border-color: #3b4f86; }}
QSlider::groove:horizontal {{ height: 6px; background: {PANEL_2}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
                              background: {TEXT}; }}
QComboBox, QSpinBox, QPlainTextEdit, QLineEdit {{ background: {PANEL_2}; border: 1px solid {BORDER};
                              border-radius: 8px; padding: 6px 8px; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; selection-background-color: {ACCENT}; }}
QProgressBar {{ background: {PANEL_2}; border: none; border-radius: 5px; height: 10px;
                text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QScrollArea {{ border: none; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 6px; }}
QMenu::item {{ padding: 7px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {PANEL_2}; }}
QMenu::item:disabled {{ color: {MUTED}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 4px; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
