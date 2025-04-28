from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentIcon as FIF, MSFluentWindow
from qfluentwidgets import (NavigationItemPosition)

from gui.home_interface import HomeInterface
from gui.lens_interface import LensInterface
from gui.retina_interface import RetinaInterface
from gui.setting_interface import SettingInterface


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        self.homeInterface = HomeInterface(self)
        self.lensInterface = LensInterface(self)
        self.retinaInterface = RetinaInterface(self)
        self.settingInterface = SettingInterface(self)

        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        self.initNavigation()


    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '主页', FIF.HOME_FILL)
        self.navigationInterface.addSeparator()

        self.addSubInterface(self.lensInterface, FIF.VIEW, '晶状体')
        self.addSubInterface(self.retinaInterface, FIF.VIEW, '视网膜')
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置',FIF.SETTING, NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1080, 720)
        self.setWindowIcon(QIcon(r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\resource\images\logo.png"))
        self.setWindowTitle("眼科图像处理系统")

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        self.show()
        QApplication.processEvents()
