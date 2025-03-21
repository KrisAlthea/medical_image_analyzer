import os
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QSplitter, QTextEdit, QLabel, QFileDialog
from qfluentwidgets import ScrollArea, ToolButton, FluentIcon, setTheme, Theme, TextEdit

from common.style_sheet import StyleSheet
from core.lens_process import LensProcess


class Worker(QThread):
    """后台线程类，用于异步执行图像处理"""
    finished = pyqtSignal(dict)  # 信号，传递处理结果

    def __init__(self, lens_process, image_path, save_dir):
        super().__init__()
        self.lens_process = lens_process  # LensProcess 实例
        self.image_path = image_path      # 输入图片路径
        self.save_dir = save_dir          # 输出保存目录

    def run(self):
        """线程执行函数，调用处理逻辑并发射结果"""
        result_data = self.lens_process.process_and_save(self.image_path, self.save_dir)
        self.finished.emit(result_data)

class LensInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.image_path = None

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        # 初始化 LensProcess 实例
        best_model_path = r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\models\lens.pth"  # 请根据实际路径修改
        self.lens_process = LensProcess(best_model_path)

        # 设置保存目录
        self.save_dir = r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\output\lens"  # 请根据实际路径修改
        os.makedirs(self.save_dir, exist_ok=True)  # 创建目录（如果不存在）

        # 创建界面组件
        self.select_button = ToolButton(FluentIcon.ADD,self)  # 选择图片按钮
        self.process_button = ToolButton(FluentIcon.PLAY,self)  # 处理图片按钮
        # pixmap = QPixmap(self.image_path) # 读取图片
        # self.original_label.setPixmap(pixmap) # 设置图片到 QLabel
        self.original_label = QLabel("Original Image")  # 原始图片显示区
        self.original_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.processed_label = QLabel("Processed Image")  # 处理后图片显示区
        self.processed_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.data_text = TextEdit()  # 数据显示区
        self.data_text.setReadOnly(True)  # 设置为只读

        # 设置布局
        # 顶部工具栏布局
        self.toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.addStretch()  # 左侧伸缩
        toolbar_layout.addWidget(self.select_button)
        toolbar_layout.addWidget(self.process_button)
        toolbar_layout.addStretch()  # 右侧伸缩

        # 包装图片标签
        original_scroll = ScrollArea()
        original_scroll.setWidget(self.original_label)
        original_scroll.setWidgetResizable(True)

        processed_scroll = ScrollArea()
        processed_scroll.setWidget(self.processed_label)
        processed_scroll.setWidgetResizable(True)

        # 中间图片展示区，使用 QSplitter 水平分割
        image_splitter = QSplitter(Qt.Horizontal)
        # image_splitter.addWidget(self.original_label)
        # image_splitter.addWidget(self.processed_label)
        image_splitter.addWidget(original_scroll)
        image_splitter.addWidget(processed_scroll)
        image_splitter.setSizes([600, 600])  # 设置初始宽度

        # 创建垂直分割器
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(image_splitter)  # 假设 image_splitter 是图片区的 QSplitter
        main_splitter.addWidget(self.data_text)  # 数据展示区
        main_splitter.setSizes([600, 200])  # 初始高度：图片区 600px，数据区 200px

        # 将工具栏、图片区和数据区添加到 vBoxLayout
        # self.vBoxLayout.addWidget(self.toolbar)
        # self.vBoxLayout.addWidget(image_splitter)
        # self.vBoxLayout.addWidget(self.data_text)
        self.vBoxLayout.addWidget(self.toolbar)
        self.vBoxLayout.addWidget(main_splitter)

        self.__initWidget()

        # 连接信号与槽
        self.select_button.clicked.connect(self.select_image)  # 选择图片按钮点击事件
        self.process_button.clicked.connect(self.process_image)  # 处理图片按钮点击事件

        # 初始化变量
        self.image_path = None  # 当前选择的图片路径
        self.worker = None  # 后台线程实例

    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('lensInterface')
        self.toolbar.setObjectName("toolbar")
        self.original_label.setObjectName("originalLabel")  # 图片标签
        self.processed_label.setObjectName("processedLabel")
        self.data_text.setObjectName("dataText")  # 数据展示区
        StyleSheet.LENS_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

    def select_image(self):
        """选择图片并显示到左侧 QLabel"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.jpg *.png *.bmp)")  # 文件过滤器
        if file_dialog.exec_():
            self.image_path = file_dialog.selectedFiles()[0]  # 获取选择的文件路径
            # pixmap = QPixmap(self.image_path).scaled(
            #     self.original_label.size(),
            #     Qt.KeepAspectRatio,
            #     Qt.SmoothTransformation
            # )
            pixmap = QPixmap(self.image_path)  # 读取图片
            self.original_label.setPixmap(pixmap)  # 设置图片到 QLabel
            self.original_label.setScaledContents(True)

    def process_image(self):
        """启动图像处理线程"""
        if self.image_path is None:
            return  # 未选择图片时直接返回

        # 禁用处理按钮并更新文本
        self.process_button.setEnabled(False)
        # self.process_button.setText("Processing...")

        # 创建并启动 Worker 线程
        self.worker = Worker(self.lens_process, self.image_path, self.save_dir)
        self.worker.finished.connect(self.on_process_finished)  # 连接处理完成信号
        self.worker.start()

    def on_process_finished(self, result_data):
        """处理完成后更新界面"""
        # 恢复处理按钮状态
        self.process_button.setEnabled(True)
        # self.process_button.setText("Process Image")

        # 显示处理后的图片
        result_image_path = result_data['result_image_path']
        # pixmap = QPixmap(result_image_path).scaled(
        #     self.processed_label.size(),
        #     Qt.KeepAspectRatio,
        #     Qt.SmoothTransformation
        # )
        pixmap = QPixmap(result_image_path)
        self.processed_label.setPixmap(pixmap)
        self.processed_label.setScaledContents(True)

        # 显示处理数据
        up_points = result_data['up_boundary_points']
        down_points = result_data['down_boundary_points']
        up_equation = result_data['up_fitting_equation']
        down_equation = result_data['down_fitting_equation']

        # 格式化数据文本
        data_text = f"上边界点数：{len(up_points)}\n"
        data_text += f"下边界点数：{len(down_points)}\n"
        data_text += f"上边界拟合方程：y = {up_equation.coefficients[0]:.4f}*x^2 + {up_equation.coefficients[1]:.4f}*x + {up_equation.coefficients[2]:.4f}\n"
        data_text += f"下边界拟合方程：y = {down_equation.coefficients[0]:.4f}*x^2 + {down_equation.coefficients[1]:.4f}*x + {down_equation.coefficients[2]:.4f}\n"
        self.data_text.setText(data_text)


# 主程序入口（示例）
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)  # 设置为暗色主题
    interface = LensInterface()
    interface.show()
    sys.exit(app.exec_())