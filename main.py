import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIcon, QIntValidator
from funcionality import start_parsing, run_in_thread
from qss import BRIGHT_QSS
import resources_rc

class ParserApp(QtWidgets.QWidget):
    """Основний клас додатку для парсингу."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AliExpress Parser")
        self.setWindowIcon(QIcon(":/ico.png"))
        self.resize(700, 500)

        self.selected_mode = "single"
        self.link_or_links = ""
        self.limit = 1

        self._init_ui()
        self.setStyleSheet(BRIGHT_QSS)

    def _init_ui(self):
        """Ініціалізація елементів інтерфейсу."""
        layout = QtWidgets.QVBoxLayout(self)

        # Поле для URL/запиту
        url_layout = QtWidgets.QHBoxLayout()
        lbl_url = QtWidgets.QLabel("Enter link / query:")
        self.edit_url = QtWidgets.QLineEdit()
        self.edit_url.setPlaceholderText("Введіть посилання / запит або список (через кому)...")
        url_layout.addWidget(lbl_url)
        url_layout.addWidget(self.edit_url)
        layout.addLayout(url_layout)

        # Режими парсингу
        mode_layout = QtWidgets.QHBoxLayout()
        lbl_mode = QtWidgets.QLabel("Select Mode:")
        mode_layout.addWidget(lbl_mode)

        self.rb_single = QtWidgets.QRadioButton("Single")
        self.rb_single.setChecked(True)
        self.rb_query = QtWidgets.QRadioButton("Query")
        self.rb_multiple = QtWidgets.QRadioButton("Multiple")

        self.rb_single.toggled.connect(lambda: self.on_mode_changed("single"))
        self.rb_query.toggled.connect(lambda: self.on_mode_changed("query"))
        self.rb_multiple.toggled.connect(lambda: self.on_mode_changed("multiple"))

        mode_layout.addWidget(self.rb_single)
        mode_layout.addWidget(self.rb_query)
        mode_layout.addWidget(self.rb_multiple)
        layout.addLayout(mode_layout)

        # Поле для ліміту (тільки для режиму Query)
        limit_layout = QtWidgets.QHBoxLayout()
        self.lbl_limit = QtWidgets.QLabel("Limit (for query):")
        self.edit_limit = QtWidgets.QLineEdit("1")
        self.edit_limit.setValidator(QIntValidator(1, 1000))
        limit_layout.addWidget(self.lbl_limit)
        limit_layout.addWidget(self.edit_limit)
        layout.addLayout(limit_layout)
        self.lbl_limit.setEnabled(False)
        self.edit_limit.setEnabled(False)

        # Текстове поле для логів
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Логи виконання з'являться тут...")
        layout.addWidget(self.log_text)

        # Прогрес-бар та кнопка старту
        bottom_layout = QtWidgets.QHBoxLayout()
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        bottom_layout.addWidget(self.progress_bar)
        self.btn_start = QtWidgets.QPushButton("Start Parsing")
        self.btn_start.clicked.connect(self.start_parsing)
        bottom_layout.addWidget(self.btn_start)
        layout.addLayout(bottom_layout)

    def on_mode_changed(self, mode: str):
        """Обробка зміни режиму парсингу."""
        self.selected_mode = mode
        if mode == "query":
            self.lbl_limit.setEnabled(True)
            self.edit_limit.setEnabled(True)
        else:
            self.lbl_limit.setEnabled(False)
            self.edit_limit.setEnabled(False)

    def start_parsing(self):
        """Запуск процесу парсингу."""
        self.link_or_links = self.edit_url.text().strip()
        self.limit = int(self.edit_limit.text()) if self.edit_limit.text().isdigit() else 1
        if not self.link_or_links:
            QtWidgets.QMessageBox.warning(self, "Warning", "Будь ласка, введіть посилання або запит.")
            return
        self.btn_start.setEnabled(True)
        self.log_text.appendPlainText("==== Запуск процесу парсингу ====")
        self.progress_bar.setValue(0)
        run_in_thread(
            target=start_parsing,
            mode=self.selected_mode,
            link_or_links=self.link_or_links,
            limit=self.limit,
            log_callback=self.add_log,
            progress_callback=self.update_progress,
        )

    def add_log(self, message: str):
        """Callback для виводу логів."""
        QtCore.QMetaObject.invokeMethod(
            self,
            "append_log_text",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, message)
        )

    @QtCore.pyqtSlot(str)
    def append_log_text(self, message: str):
        """Додавання повідомлення у текстове поле логів."""
        self.log_text.appendPlainText(message)
        if "завершено успішно" in message.lower() or "помилка" in message.lower():
            self.btn_start.setEnabled(True)

    def update_progress(self, value: int):
        """Callback для оновлення прогрес-бару."""
        QtCore.QMetaObject.invokeMethod(
            self,
            "set_progress_val",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(int, value)
        )

    @QtCore.pyqtSlot(int)
    def set_progress_val(self, value: int):
        """Встановлення значення прогрес-бару."""
        self.progress_bar.setValue(value)
        if value >= 100:
            self.btn_start.setEnabled(True)

def main():
    """Точка входу в додаток."""
    app = QtWidgets.QApplication(sys.argv)
    window = ParserApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
