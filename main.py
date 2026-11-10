import sys
import time

from ui_lesson_time import Ui_Form
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QTimer


class LessonTimeApp(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self._setup_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.relax_time = 5
        self.work_time = 20
        self.remaining_time = 20
        self.end_time = None
        self.is_running = False
        self.ui.progressZone.setMaximum(self.work_time + self.relax_time)

        self._setup_logic()

    def _setup_ui(self):
        self.ui = Ui_Form()
        self.ui.setupUi(self)

    def _setup_logic(self):
        self.ui.startBtn.clicked.connect(self.startBtn)
        self.ui.pauseBtn.clicked.connect(self.pauseBtn)
        self.ui.resetBtn.clicked.connect(self.resetBtn)

    def update_timer(self):
        self.remaining_time = int(self.end_time) - int(time.time())

        if int(self.remaining_time) <= 0:
            self.timer.stop()
            self.remaining_time = 0
            self.is_running = False
            self.ui.timerZone.setText(f"00:00")
            self.ui.focusZone.setText("Сессия окончена")

        else:
            minutes = int(self.remaining_time) // 60
            seconds = int(self.remaining_time) % 60
            self.ui.timerZone.setText(f"{minutes:02d}:{seconds:02d}")
            self.ui.progressZone.setValue(abs(self.work_time - self.remaining_time))

    def startBtn(self):
        if not self.is_running:
            self.end_time = time.time() + self.remaining_time
            self.timer.start(1000)
            self.is_running = True

    def pauseBtn(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.ui.focusZone.setText(f"Пауза: {self.ui.focusZone.text()}")

    def resetBtn(self):
        self.timer.stop()
        self.is_running = False
        self.remaining_time = self.work_time
        self.ui.progressZone.setValue(0)

        # Оптимизировать этот костыль
        minutes = int(self.remaining_time) // 60
        seconds = int(self.remaining_time) % 60
        self.ui.timerZone.setText(f"{minutes:02d}:{seconds:02d}")

        if "Пауза: " in self.ui.focusZone.text():
            self.ui.focusZone.setText(f"{self.ui.focusZone.text()[6:]}")

        elif self.ui.focusZone.text() == "Сессия окончена":
            self.ui.focusZone.setText("")  # Потом поменять на изначальный выбор фокуса

        self.update()


def main():
    app = QApplication(sys.argv)
    window = LessonTimeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
