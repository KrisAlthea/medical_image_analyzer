import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QFileDialog, QSplitter, QMessageBox, QLabel
)
from PyQt5.QtCore import QUrl, QSize, QTimer
from PyQt5.QtGui import QIcon, QDesktopServices, QColor
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, SystemThemeListener, isDarkTheme)
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from qfluentwidgets import PushButton, BodyLabel, setTheme, Theme, FluentWindow
from core.lens_process import LensProcess
from core.retina_process import RetinaProcess
from gui.home_interface import HomeInterface
from gui.lens_interface import LensInterface
from gui.retina_interface import RetinaInterface
from gui.setting_interface import SettingInterface


class ImageProcessorPage(QWidget):
    def __init__(self, name, processor, save_dir):
        super().__init__()
        self.name = name
        self.processor = processor
        self.save_dir = save_dir
        self.image_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 选择图片按钮（使用 QFluentWidgets PushButton）
        btn_select_image = PushButton("选择图片", icon=FIF.PHOTO)
        btn_select_image.clicked.connect(self.select_image)
        layout.addWidget(btn_select_image)

        # 图片展示区域
        self.image_layout = QHBoxLayout()
        self.image_layout.setSpacing(10)
        self.original_image_label = QLabel("原图")
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setStyleSheet("border: 1px solid #d0d0d0;")
        self.processed_image_label = QLabel("识别图")
        self.processed_image_label.setAlignment(Qt.AlignCenter)
        self.processed_image_label.setStyleSheet("border: 1px solid #d0d0d0;")
        self.image_layout.addWidget(self.original_image_label)
        self.image_layout.addWidget(self.processed_image_label)
        layout.addLayout(self.image_layout)

        # 处理按钮（使用 QFluentWidgets PushButton）
        btn_process = PushButton("处理", icon=FIF.BOOK_SHELF)
        btn_process.clicked.connect(self.process_image)
        layout.addWidget(btn_process)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.original_image_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.processed_image_label.clear()

    def process_image(self):
        if not self.image_path:
            QMessageBox.warning(self, "警告", "请先选择图片")
            return

        if self.name == "Lens":
            # 调用 LensProcess 的 process_and_save 方法
            self.processor.process_and_save(self.image_path, self.save_dir)
            filename = os.path.basename(self.image_path)
            name, ext = os.path.splitext(filename)
            processed_image_path = os.path.join(self.save_dir, f"{name}-output{ext}")
        elif self.name == "Retina":
            # Retina 处理需要指定圆的参数
            circle_params = {
                "radius_range": range(200, 350, 5),
                "center_x_range": (0, 400),
                "center_y_range": (0, 640),
                "step": 20
            }
            # 这里仍使用硬编码的保存目录
            save_dir = r"D:\Code\PyCharm_ws\medical_image_analyzer\output\retina"
            processed_image_path = self.processor.process_image(self.image_path, circle_params, save_dir)

        if os.path.exists(processed_image_path):
            pixmap = QPixmap(processed_image_path)
            self.processed_image_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            QMessageBox.warning(self, "错误", "处理结果文件未生成")


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.initWindow()

        self.homeInterface = HomeInterface(self)
        self.lensInterface = LensInterface(self)
        self.retinaInterface = RetinaInterface(self)
        self.settingInterface = SettingInterface(self)

        self.initNavigation()

        # self.init_ui()


    def init_ui(self):
        # 主分割器布局
        splitter = QSplitter(Qt.Horizontal)
        # self.setCentralWidget(splitter)

        # 左侧边栏（使用 QFluentWidgets 风格）
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        # 导航按钮
        btn_intro = PushButton("首页", icon=FIF.HOME)
        btn_intro.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        sidebar_layout.addWidget(btn_intro)

        btn_lens = PushButton("Lens", icon=FIF.PHOTO)
        btn_lens.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        sidebar_layout.addWidget(btn_lens)

        btn_retina = PushButton("Retina", icon=FIF.PHOTO)
        btn_retina.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        sidebar_layout.addWidget(btn_retina)

        btn_settings = PushButton("设置", icon=FIF.SETTING)
        btn_settings.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        sidebar_layout.addWidget(btn_settings)

        splitter.addWidget(sidebar)

        # 主内容区域
        self.stacked_widget = QStackedWidget()
        splitter.addWidget(self.stacked_widget)

        # 主页：程序介绍（使用 QFluentWidgets BodyLabel）
        intro_page = QWidget()
        intro_layout = QVBoxLayout(intro_page)
        intro_layout.setContentsMargins(30, 30, 30, 30)
        intro_text = BodyLabel(
            "欢迎使用医学图像识别系统\n\n"
            "本程序用于处理晶状体（Lens）和视网膜（Retina）的医学图像。\n"
            "使用方法：\n"
            "1. 在左侧边栏选择 'Lens' 或 'Retina'。\n"
            "2. 点击 '选择图片' 按钮加载本地图像。\n"
            "3. 点击 '处理' 按钮运行识别算法。\n"
            "4. 查看原图和识别结果（左右排列）。"
        )
        intro_text.setAlignment(Qt.AlignCenter)
        intro_layout.addWidget(intro_text)
        self.stacked_widget.addWidget(intro_page)

        # 初始化处理器
        lens_processor = LensProcess(best_model_path="models/lens.pth")
        retina_processor = RetinaProcess(model_path="models/retina.pth")

        # 添加 Lens 页面
        lens_page = ImageProcessorPage("Lens", lens_processor, "output/lens")
        self.stacked_widget.addWidget(lens_page)

        # 添加 Retina 页面
        retina_page = ImageProcessorPage("Retina", retina_processor, "output/retina")
        self.stacked_widget.addWidget(retina_page)

        # 设置页面（暂留空）
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(30, 30, 30, 30)
        settings_label = BodyLabel("设置页面（待实现）")
        settings_label.setAlignment(Qt.AlignCenter)
        settings_layout.addWidget(settings_label)
        self.stacked_widget.addWidget(settings_page)

        splitter.setSizes([250, 950])

    def initNavigation(self):

        self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('Home'))
        self.addSubInterface(self.lensInterface, FIF.PHOTO, self.tr('Lens'))
        self.addSubInterface(self.retinaInterface, FIF.PHOTO, self.tr('Retina'))
        self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1200, 800)
        self.setWindowIcon(QIcon(r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\resource\images\logo.png"))
        self.setWindowTitle("眼科图像处理系统")

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
        self.show()
        QApplication.processEvents()
