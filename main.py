import datetime
import calendar
import sys
import os
import time

from ui_lesson_time import Ui_Form
from PyQt6.QtWidgets import (QWidget, QApplication, QButtonGroup, QMessageBox, QMenu, QDialog,
                             QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QPushButton, QSystemTrayIcon)
from PyQt6.QtCore import QTimer, QSettings, QStringListModel, QUrl
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtMultimedia import QSoundEffect


def rpath(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, rel)


class LessonTimeApp(QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.week_key = None
        self._setup_ui()

        self.settings = QSettings("LessonTime", "LessonSettings")

        self.ui.focusZone.setText("Задача не выбрана")
        self.activeTask = None
        self.ui.taskList.setContextMenuPolicy(
            self.ui.taskList.contextMenuPolicy().CustomContextMenu
        )
        self.ui.taskList.customContextMenuRequested.connect(self.showTaskMenu)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.ui.fiveOneMode)
        self.mode_group.addButton(self.ui.fourOneMode)
        self.mode_group.addButton(self.ui.Custom)
        self.ui.fourOneMode.setChecked(True)

        self.todayTime = 0
        self.streakTime = 0
        self.sessionCount = 0
        self.weekTime = 0
        self.weekLog = []
        self.weekStreak = []
        self.last_day = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.relax_time = 300
        self.work_time = 1200
        self.remaining_time = self.work_time
        self.end_time = None
        self.is_running = False
        self.is_resting = False
        self.ui.progressZone.setMaximum(self.work_time + self.relax_time)

        self.sound = QSoundEffect()

        self.load_data()
        self.upload_analyze()
        self._setup_logic()
        self._setup_tray()
        self.refresh_analytics()

    def upload_analyze(self):
        self.todayTime = self.settings.value("todayTime", 0, type=int)
        self.streakTime = self.settings.value("streakTime", 0, type=int)
        self.last_day = self.settings.value("last_day", "", type=str)
        self.sessionCount = self.settings.value("sessionCount", 0, type=int)
        self.weekLog = self.settings.value("weekLog", [], type=list)
        self.week_key = self.settings.value("week_key", "", type=str)

        today = datetime.date.today()
        iso = today.isocalendar()
        cur_key = f"{iso[0]}-W{iso[1]:02d}"

        if self.week_key != cur_key:
            self.weekLog = []
            self.week_key = cur_key

        if self.last_day != today.isoformat():
            if self.last_day and self.todayTime > 0:
                y = datetime.date.fromisoformat(self.last_day).isocalendar()
                if y[0] == iso[0] and y[1] == iso[1]:
                    self.weekLog.append((self.last_day, self.todayTime))
            self.todayTime = 0
            self.sessionCount = 0

    def refresh_analytics(self):
        self.ui.todayStat.setText(f"{self.todayTime // 3600}h {(self.todayTime % 3600) // 60}m")
        self.ui.streakStat.setText(f"{self.streakTime} days 🔥")
        self.ui.sessionStat.setText(f"{self.sessionCount}")

        self.weekTime = sum(s for _, s in self.weekLog) + self.todayTime
        self.ui.weekStat.setText(f"{self.weekTime // 3600}h {(self.weekTime % 3600) // 60}m")

        days = [datetime.date.fromisoformat(d) for d, _ in self.weekLog]
        if self.todayTime > 0:
            days.append(datetime.date.today())
        self.weekStreak = sorted({d.weekday() for d in days})
        self._paint_week_bars()

    def _paint_week_bars(self):
        bars = [self.ui.dayOne, self.ui.dayTwo, self.ui.dayThree,
                self.ui.dayFour, self.ui.dayFive, self.ui.daySix,
                self.ui.daySeven]
        for i, bar in enumerate(bars):
            active = i in self.weekStreak
            bar.setStyleSheet(
                "background-color:#4CAF50; border-radius:4px;"
                if active else "background-color:#3E3E42; border-radius:4px;")

    def _on_new_focus_day(self):
        today = datetime.date.today()
        if self.last_day:
            last = datetime.date.fromisoformat(self.last_day)
            gap = (today - last).days
            if gap == 1:
                self.streakTime += 1
            elif gap > 1:
                self.streakTime = 1
        else:
            self.streakTime = 1
        self.last_day = today.isoformat()
        self.save_data()
        self.refresh_analytics()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.main_menu = QMenu(self)

        self.action_for_exit = QAction('Выход')
        self.action_for_exit.triggered.connect(self._exit_from_tray)
        self.main_menu.addAction(self.action_for_exit)

        self.tray.setIcon(QIcon(rpath("Images/LessonTimeIcon.png")))
        self.tray.setContextMenu(self.main_menu)
        self.tray.activated.connect(self._on_tray_triggered)
        self.tray.show()

    def _setup_ui(self):
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(rpath("Images/LessonTimeIcon.png")))

    def _setup_logic(self):
        self.ui.startBtn.clicked.connect(self.startBtn)
        self.ui.pauseBtn.clicked.connect(self.pauseBtn)
        self.ui.resetBtn.clicked.connect(self.resetBtn)

        self.ui.fourOneMode.clicked.connect(lambda: self.set_mode(1200, 300))
        self.ui.fiveOneMode.clicked.connect(lambda: self.set_mode(3000, 600))
        self.ui.Custom.clicked.connect(self.on_custom_clicked)

        self.ui.addBtnTask.clicked.connect(self.addTask)
        self.ui.addBtnTask.setShortcut("Return")
        self.ui.taskList.itemClicked.connect(self.selectTask)

    def setModeButton(self, enable: bool):
        self.ui.fourOneMode.setEnabled(enable)
        self.ui.fiveOneMode.setEnabled(enable)
        self.ui.Custom.setEnabled(enable)

    def timerView(self):
        minutes = int(self.remaining_time) // 60
        seconds = int(self.remaining_time) % 60
        self.ui.timerZone.setText(f"{minutes:02d}:{seconds:02d}")

    def timerRest(self):
        self.timer.start(1000)
        self.sound.setSource(QUrl.fromLocalFile(rpath("sounds/WorkIsDone.wav")))
        self.sound.setVolume(0.8)
        self.sound.play()

        self.ui.focusZone.setText("Время отдыха")
        self.todayTime += 1
        self.refresh_analytics()

        self.end_time += self.relax_time
        self.remaining_time = self.relax_time
        self.timerView()
        self.is_resting = True

    def update_timer(self):
        self.remaining_time = int(self.end_time) - int(time.time())

        if int(self.remaining_time) <= 0:
            self.timer.stop()
            self.remaining_time = 0
            self.is_running = False
            self.setModeButton(True)
            self.ui.timerZone.setText(f"00:00")

            if not self.is_resting:
                self.timerRest()

            else:
                self.sound.setSource(QUrl.fromLocalFile(rpath("sounds/RestIsDone.wav")))
                self.sound.setVolume(0.8)
                self.sound.play()

                self.ui.focusZone.setText("Сессия окончена")
                self.ui.progressZone.setValue(self.relax_time + self.work_time)
                self.ui.startBtn.setEnabled(False)

        else:
            if not self.is_resting:
                self.todayTime += 1
                if self.todayTime == 1:
                    self._on_new_focus_day()
                self.refresh_analytics()

            self.timerView()
            if self.is_resting:
                self.ui.progressZone.setValue(abs((self.relax_time + self.work_time) - self.remaining_time))
            else:
                self.ui.progressZone.setValue(abs(self.work_time - self.remaining_time))

            self.refresh_analytics()

    def startBtn(self):
        if not self.is_running and self.activeTask:
            self.end_time = time.time() + self.remaining_time
            self.timer.start(1000)
            self.is_running = True
            self.setModeButton(False)

            self.sessionCount += 1
            self.refresh_analytics()

            if "Пауза: " in self.ui.focusZone.text():
                self.ui.focusZone.setText(f"{self.ui.focusZone.text()[6:]}")
                self.sessionCount -= 1
                self.refresh_analytics()

    def pauseBtn(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.setModeButton(True)
            self.ui.focusZone.setText(f"Пауза: {self.ui.focusZone.text()}")

    def resetBtn(self):
        self.timer.stop()
        self.is_running = False
        self.setModeButton(True)
        self.is_resting = False
        self.remaining_time = self.work_time
        self.ui.progressZone.setValue(0)

        self.timerView()

        if "Пауза: " in self.ui.focusZone.text():
            self.ui.focusZone.setText(f"{self.ui.focusZone.text()[6:]}")

        elif self.ui.focusZone.text() == "Сессия окончена":
            self.ui.focusZone.setText(self.activeTask)
            self.ui.startBtn.setEnabled(True)

        self.update()

    def set_mode(self, work_time, relax_time):
        if not self.is_running:
            self.work_time = work_time
            self.relax_time = relax_time
            self.remaining_time = work_time

            self.timer.stop()
            self.is_running = False

            self.timerView()
            self.update()

    def on_custom_clicked(self):
        dlg = CustomTimerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.work_time = dlg.work_spin.value() * 60
            self.relax_time = dlg.relax_spin.value() * 60
            self.remaining_time = self.work_time
            self.ui.progressZone.setMaximum(self.work_time + self.relax_time)

            self.timerView()
            self.ui.progressZone.setValue(0)

    def addTask(self):
        if self.ui.textTask.text().strip():
            self.ui.taskList.addItem(self.ui.textTask.text().strip())
            self.ui.textTask.setText("")

    def selectTask(self, current):
        if current:
            self.ui.focusZone.setText(current.text())
            self.activeTask = current.text()

    def showTaskMenu(self, pos):
        item = self.ui.taskList.itemAt(pos)
        if item is None:
            return

        menu = QMenu(self)
        deleteAction = menu.addAction("Удвлить")
        action = menu.exec(self.ui.taskList.viewport().mapToGlobal(pos))

        if action == deleteAction:
            self.deleteTask()

    def deleteTask(self):
        current = self.ui.taskList.currentItem()
        if current is None:
            return

        taskName = current.text()
        row = self.ui.taskList.currentRow()
        self.ui.taskList.takeItem(row)

        if taskName == self.ui.focusZone.text():
            self.ui.focusZone.setText("Задача не выбрана")
            self.resetBtn()

    def load_data(self):
        if self.settings.contains("TaskListMemory"):
            for t in self.settings.value("TaskListMemory", [], type=list):
                self.ui.taskList.addItem(t)
        self.ui.taskList.clearSelection()
        self.ui.taskList.setCurrentRow(-1)

        if self.settings.contains("work_time"):
            self.work_time = self.settings.value("work_time")
            self.remaining_time = self.work_time
        if self.settings.contains("relax_time"):
            self.relax_time = self.settings.value("relax_time")

        self.ui.progressZone.setMaximum(self.work_time + self.relax_time)
        self.syncBtn()
        self.timerView()

    def syncBtn(self):
        if (self.work_time, self.relax_time) == (20 * 60, 5 * 60):
            self.ui.fourOneMode.setChecked(True)
        elif (self.work_time, self.relax_time) == (50 * 60, 10 * 60):
            self.ui.fiveOneMode.setChecked(True)
        else:
            self.ui.Custom.setChecked(True)
        self.timerView()

    def _on_tray_triggered(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden() or self.isMinimized():
                self.show()
                self.showNormal()
                self.activateWindow()

    def save_data(self):
        tasks = [self.ui.taskList.item(i).text()
                 for i in range(self.ui.taskList.count())]
        self.settings.setValue("TaskListMemory", tasks)
        self.settings.setValue("work_time", self.work_time)
        self.settings.setValue("relax_time", self.relax_time)
        self.settings.setValue("todayTime", self.todayTime)
        self.settings.setValue("streakTime", self.streakTime)
        self.settings.setValue("last_day", self.last_day or "")
        self.settings.setValue("sessionCount", self.sessionCount)
        self.settings.setValue("week_key", self.week_key)
        self.settings.setValue("weekLog", self.weekLog)

    def _exit_from_tray(self):
        self.save_data()
        QApplication.instance().quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class CustomTimerDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Настроить время")
        self.setModal(True)
        lay = QVBoxLayout(self)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Работа (мин):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 60)
        r1.addWidget(self.work_spin)
        lay.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Отдых (мин):"))
        self.relax_spin = QSpinBox()
        self.relax_spin.setRange(1, 60)
        r2.addWidget(self.relax_spin)
        lay.addLayout(r2)

        btns = QHBoxLayout()
        ok = QPushButton("Применить")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        lay.addLayout(btns)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = LessonTimeApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
