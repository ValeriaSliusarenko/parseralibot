'''
    Основні стилі програми для графічного інтерфейсу.
'''

BRIGHT_QSS = '''
            QWidget {
                background-color: #1C1C1E;
                color: #F2F2F7;
                font-family: "San Francisco", "Helvetica Neue", Roboto, sans-serif;
                font-size: 11pt;
            }
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #1C1C1E, stop:1 #2C2C2E);
            }
            QGroupBox {
                border: 2px solid #0A84FF;
                border-radius: 10px;
                margin-top: 12px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #0A84FF;
                font-weight: bold;
            }
            QLabel {
                color: #F2F2F7;
            }
            QLineEdit {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                padding: 8px;
                color: #F2F2F7;
            }
            QLineEdit:focus {
                border: 1px solid #0A84FF;
                background-color: #3A3A3C;
            }
            QPlainTextEdit, QTextEdit {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                padding: 8px;
                color: #F2F2F7;
            }
            QPlainTextEdit:focus, QTextEdit:focus {
                border: 1px solid #0A84FF;
                background-color: #3A3A3C;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #0A84FF, stop:1 #64D2FF);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: #F2F2F7;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #64D2FF, stop:1 #0A84FF);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #0A84FF, stop:1 #0A84FF);
            }
            QPushButton:disabled {
                background-color: #3A3A3C;
                color: #8E8E93;
            }
            QProgressBar {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 10px;
                text-align: center;
                color: #F2F2F7;
                height: 22px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #0A84FF, stop:1 #64D2FF);
                border-radius: 10px;
            }
            QScrollBar:vertical {
                background-color: #1C1C1E;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3A3A3C;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0A84FF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #1C1C1E;
                height: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #3A3A3C;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #0A84FF;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
            }
            QComboBox {
                background-color: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                padding: 8px 10px;
                color: #F2F2F7;
            }
            QComboBox:focus {
                border: 1px solid #0A84FF;
                background-color: #3A3A3C;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #3A3A3C;
            }
            QToolTip {
                background-color: #0A84FF;
                color: #F2F2F7;
                border: none;
                padding: 6px;
                border-radius: 8px;
                font-size: 9pt;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3A3A3C;
                height: 8px;
                background: #2C2C2E;
                border-radius: 4px;
                margin: 0px;
            }
            QSlider::handle:horizontal {
                background-color: #0A84FF;
                border: none;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #64D2FF;
            }
            QSlider::groove:vertical {
                border: 1px solid #3A3A3C;
                width: 8px;
                background: #2C2C2E;
                border-radius: 4px;
                margin: 0px;
            }
            QSlider::handle:vertical {
                background-color: #0A84FF;
                border: none;
                width: 16px;
                height: 16px;
                margin: 0 -4px;
                border-radius: 8px;
            }
            QSlider::handle:vertical:hover {
                background-color: #64D2FF;
            }
            QTabWidget::pane {
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                background-color: #2C2C2E;
            }
            QTabBar::tab {
                background-color: #1C1C1E;
                border: 1px solid #3A3A3C;
                border-radius: 8px;
                padding: 8px 16px;
                margin: 4px;
                color: #F2F2F7;
                font-weight: bold;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
            QTabBar::tab:!selected {
                background-color: #1C1C1E;
                color: #8E8E93;
            }
'''
