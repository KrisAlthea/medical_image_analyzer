import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QSplitter, QStackedWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from qfluentwidgets import PushButton, FluentIcon, BodyLabel
from core.lens_process import LensProcess
from core.retina_process import RetinaProcess

class ImageProcessorPage(QWidget):
    def __init__(self, name, processor, save_dir):
        super().__init__()
        self.name = name
        self.processor = processor
        self.save_dir = save_dir
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 选择图片按钮
        btn_select_image = QPushButton("选择图片")
        btn_select_image.clicked.connect(self.select_image)
        layout.addWidget(btn_select_image)

        # 图片展示区域
        self.image_layout = QHBoxLayout()
        self.original_image_label = QLabel("原图")
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.processed_image_label = QLabel("识别图")
        self.processed_image_label.setAlignment(Qt.AlignCenter)
        self.image_layout.addWidget(self.original_image_label)
        self.image_layout.addWidget(self.processed_image_label)
        layout.addLayout(self.image_layout)

        # 处理按钮
        btn_process = QPushButton("处理")
        btn_process.clicked.connect(self.process_image)
        layout.addWidget(btn_process)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.original_image_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio))
            self.processed_image_label.clear()

    def process_image(self):
        if not hasattr(self, 'image_path'):
            QMessageBox.warning(self, "警告", "请先选择图片")
            return

        if self.name == "Lens":
            # 调用 LensProcess 的 process_and_save 方法
            self.processor.process_and_save(self.image_path, self.save_dir)
            # 获取保存的处理结果路径
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
            save_dir = r"D:\Code\PyCharm_ws\medical_image_analyzer\output\retina"
            path = self.processor.process_image(self.image_path, circle_params, save_dir)
            # 获取保存的处理结果路径
            processed_image_path = path

        # 显示处理后的图片
        if os.path.exists(processed_image_path):
            pixmap = QPixmap(processed_image_path)
            self.processed_image_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio))
        else:
            QMessageBox.warning(self, "错误", "处理结果文件未生成")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("医学图像识别系统")
        self.resize(1200, 800)
        self.init_ui()

    def init_ui(self):
        # 创建主分割器
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # 左侧边栏
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignTop)

        # Lens 按钮
        btn_lens = PushButton("Lens", icon=FluentIcon.PHOTO)
        btn_lens.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        sidebar_layout.addWidget(btn_lens)

        # Retina 按钮
        btn_retina = PushButton("Retina", icon=FluentIcon.PHOTO)
        btn_retina.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        sidebar_layout.addWidget(btn_retina)

        # 设置按钮
        btn_settings = PushButton("设置", icon=FluentIcon.SETTING)
        btn_settings.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        sidebar_layout.addWidget(btn_settings)

        splitter.addWidget(sidebar)

        # 主内容区域
        self.stacked_widget = QStackedWidget()
        splitter.addWidget(self.stacked_widget)

        # 主页：程序介绍
        intro_page = QWidget()
        intro_layout = QVBoxLayout(intro_page)
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

        # 初始化 Lens 和 Retina 处理器
        lens_processor = LensProcess(best_model_path="models/lens.pth")
        retina_processor = RetinaProcess(model_path="models/retina.pth")

        # 添加 Lens 页面
        lens_page = ImageProcessorPage("Lens", lens_processor, "output/lens")
        self.stacked_widget.addWidget(lens_page)

        # 添加 Retina 页面
        retina_page = ImageProcessorPage("Retina", retina_processor, "output/retina")
        self.stacked_widget.addWidget(retina_page)

        # 添加设置页面（暂留空）
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.addWidget(QLabel("设置页面（待实现）"))
        self.stacked_widget.addWidget(settings_page)

        # 设置分割器比例
        splitter.setSizes([200, 1000])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())