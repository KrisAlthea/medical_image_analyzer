from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import (NavigationItemPosition, FluentIcon as FIF,
                            MSFluentWindow, SystemThemeListener, isDarkTheme, ScrollArea, SplashScreen)

from common.config import cfg
from common.signal_bus import signalBus
from common import resource_rc
from gui.history_interface import HistoryInterface
from gui.home_interface import HomeInterface
from gui.lens_interface import LensInterface
from gui.retina_interface import RetinaInterface
from gui.setting_interface import SettingInterface


class MainWindow(MSFluentWindow):
    def __init__(self, cur_user_id: int):
        super().__init__()
        self.cur_user_id = cur_user_id
        self.initWindow()

        # create system theme listener
        self.themeListener = SystemThemeListener(self)

        # create sub interface
        self.homeInterface = HomeInterface(self)
        self.lensInterface = LensInterface(self, current_user_id=self.cur_user_id)
        self.retinaInterface = RetinaInterface(self, current_user_id=self.cur_user_id)
        self.historyInterface = HistoryInterface(self, current_user_id=self.cur_user_id)
        self.settingInterface = SettingInterface(self)

        self.connectSignalToSlot()

        self.initNavigation()
        self.splashScreen.finish()

        # start theme listener
        self.themeListener.start()

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToModuleCard.connect(self.switchToModule)

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主页', FIF.HOME_FILL)
        self.addSubInterface(self.lensInterface, FIF.VIEW, '晶状体')
        self.addSubInterface(self.retinaInterface, FIF.VIEW, '视网膜')
        self.addSubInterface(self.historyInterface, FIF.HISTORY, '历史记录')
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', FIF.SETTING, NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1440, 720)
        self.setWindowIcon(QIcon(r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\resource\images\logo.png"))
        self.setWindowTitle("眼科图像处理系统")

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        self.show()
        QApplication.processEvents()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def closeEvent(self, e):
        self.themeListener.terminate()
        self.themeListener.deleteLater()
        super().closeEvent(e)

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()

        # retry
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def switchToModule(self, routeKey):
        """ switch to module """
        interfaces = self.findChildren(ScrollArea)
        for w in interfaces:
            if w.objectName() == routeKey:
                self.stackedWidget.setCurrentWidget(w, False)