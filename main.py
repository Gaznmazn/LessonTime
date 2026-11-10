import sys
import time

from ui_lesson_time import Ui_Form
from PyQt6.QtWidgets import QWidget, QApplication, QButtonGroup, QMessageBox
from PyQt6.QtCore import QTimer


class LessonTimeApp(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self._setup_ui()

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)  # Запрещает снимать выделение со всех кнопок
        self.mode_group.addButton(self.ui.fiveOneMode)
        self.mode_group.addButton(self.ui.fourOneMode)

        self.ui.fourOneMode.setChecked(True)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.relax_time = 300
        self.is_resting = False
        self.work_time = 1200
        self.remaining_time = 1200
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

        self.ui.fourOneMode.clicked.connect(lambda: self.set_mode(1200, 300))
        self.ui.fiveOneMode.clicked.connect(lambda: self.set_mode(3000, 600))

    def timerRest(self):
        self.timer.start(1000)
        self.ui.focusZone.setText("Время отдыха")

        minutes = int(self.relax_time) // 60
        seconds = int(self.relax_time) % 60
        self.ui.timerZone.setText(f"{minutes:02d}:{seconds:02d}")

        self.end_time += self.relax_time
        self.remaining_time = self.relax_time
        self.is_resting = True

    def update_timer(self):
        self.remaining_time = int(self.end_time) - int(time.time())

        if int(self.remaining_time) <= 0:
            self.timer.stop()
            self.remaining_time = 0
            self.is_running = False
            self.ui.timerZone.setText(f"00:00")

            if not self.is_resting:
                self.timerRest()
            else:
                self.ui.focusZone.setText("Сессия окончена")
                self.ui.progressZone.setValue(self.relax_time + self.work_time)

        else:
            minutes = int(self.remaining_time) // 60
            seconds = int(self.remaining_time) % 60
            self.ui.timerZone.setText(f"{minutes:02d}:{seconds:02d}")
            if self.is_resting:
                self.ui.progressZone.setValue(abs((self.relax_time + self.work_time) - self.remaining_time))
            else:
                self.ui.progressZone.setValue(abs(self.work_time - self.remaining_time))

    def startBtn(self):
        if not self.is_running:
            self.end_time = time.time() + self.remaining_time
            self.timer.start(1000)
            self.is_running = True
            if "Пауза: " in self.ui.focusZone.text():
                self.ui.focusZone.setText(f"{self.ui.focusZone.text()[6:]}")

    def pauseBtn(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.ui.focusZone.setText(f"Пауза: {self.ui.focusZone.text()}")

    def resetBtn(self):
        self.timer.stop()
        self.is_running = False
        self.is_resting = False
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

    def set_mode(self, work_time, relax_time):
        if not self.is_running:
            self.work_time = work_time
            self.relax_time = relax_time
            self.remaining_time = work_time

            self.timer.stop()
            self.is_running = False

        else:
            self.show_error("Таймер запущен, пока что нельзя поменять время")

        self.update()

    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)


def main():
    app = QApplication(sys.argv)
    window = LessonTimeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
