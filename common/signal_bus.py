from PyQt5.QtCore import QObject, pyqtSignal

class SignalBus(QObject):
    """ Signal bus """

    switchToModuleCard = pyqtSignal(str)
    micaEnableChanged = pyqtSignal(bool)

signalBus = SignalBus()