from PyQt5.QtCore import QObject, pyqtSignal

class Worker(QObject):
    finished = pyqtSignal(bool)

    def __init__(self, start_work, func):
        super(Worker, self).__init__()
        self.work = start_work
        self.func = func

    def start_working(self):
        while self.work:
            self.func()
        self.finished.emit(True)

    def stop_working(self):
        self.work = False
