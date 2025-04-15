import os
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QSplitter, QTextEdit, QLabel, QFileDialog
from qfluentwidgets import ScrollArea, ToolButton, FluentIcon, setTheme, Theme, TextEdit

from common.style_sheet import StyleSheet
from core.retina_process import RetinaProcess  # 需要创建这个处理类


class Worker(QThread):
    """后台线程类，用于异步执行图像处理"""
    finished = pyqtSignal(dict)  # 信号，传递处理结果

    def __init__(self, retina_process, image_path, save_dir):
        super().__init__()
        self.retina_process = retina_process  # RetinaProcess 实例
        self.image_path = image_path  # 输入图片路径
        self.save_dir = save_dir  # 输出保存目录

    def run(self):
        """线程执行函数，调用处理逻辑并发射结果"""
        circle_params = {
            "radius_range": range(200, 350, 5),
            "center_x_range": (0, 400),
            "center_y_range": (0, 640),
            "step": 20
        }
        result_data = self.retina_process.process_retina(self.image_path, circle_params, self.save_dir)
        self.finished.emit(result_data)


class RetinaInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.processed_pixmap = None
        self.original_pixmap = None
        self.image_path = None

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        # 初始化 RetinaProcess 实例
        best_model_path = r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\models\retina.pth"
        self.retina_process = RetinaProcess(best_model_path)

        # 设置保存目录
        self.save_dir = r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\output\retina"
        os.makedirs(self.save_dir, exist_ok=True)  # 创建目录（如果不存在）

        # 创建界面组件
        self.select_button = ToolButton(FluentIcon.ADD, self)  # 选择图片按钮
        self.process_button = ToolButton(FluentIcon.PLAY, self)  # 处理图片按钮
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
        image_splitter.addWidget(original_scroll)
        image_splitter.addWidget(processed_scroll)
        image_splitter.setSizes([600, 600])  # 设置初始宽度

        # 创建垂直分割器
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(image_splitter)  # 图片区的 QSplitter
        main_splitter.addWidget(self.data_text)  # 数据展示区
        main_splitter.setSizes([600, 200])  # 初始高度：图片区 600px，数据区 200px

        # 将工具栏和主分割器添加到 vBoxLayout
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
        self.setObjectName('retinaInterface')
        self.toolbar.setObjectName("toolbar")
        self.original_label.setObjectName("originalLabel")
        self.processed_label.setObjectName("processedLabel")
        self.data_text.setObjectName("dataText")
        StyleSheet.RETINA_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

    def select_image(self):
        """选择图片并显示到左侧 QLabel"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.jpg *.png *.bmp)")  # 文件过滤器
        if file_dialog.exec_():
            self.image_path = file_dialog.selectedFiles()[0]  # 获取选择的文件路径
            # pixmap = QPixmap(self.image_path)  # 读取图片
            # self.original_label.setPixmap(pixmap)  # 设置图片到 QLabel
            # self.original_label.setScaledContents(True)
            # 读取图片并缩放
            self.original_pixmap = QPixmap(self.image_path)
            # 初次加载时缩放
            self.update_original_image_scale()
            # 设置 label 的 resizeEvent，使图片可以随 label 大小变化而自动调整
            self.original_label.resizeEvent = self.original_label_resize_event

    def update_original_image_scale(self):
        """更新原始图像的缩放显示"""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            scaled_pixmap = self.original_pixmap.scaled(
                self.original_label.width(),
                self.original_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.original_label.setPixmap(scaled_pixmap)

    def original_label_resize_event(self, event):
        """处理原始图像标签的大小调整事件"""
        self.update_original_image_scale()
        # 确保调用父类的 resizeEvent 以保持正常行为
        QLabel.resizeEvent(self.original_label, event)

    def update_processed_image_scale(self):
        """更新后图像的缩放显示"""
        if hasattr(self, 'processed_pixmap') and not self.processed_pixmap.isNull():
            scaled_pixmap = self.processed_pixmap.scaled(
                self.processed_label.width(),
                self.processed_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.processed_label.setPixmap(scaled_pixmap)

    def processed_label_resize_event(self, event):
        """处理原始图像标签的大小调整事件"""
        self.update_processed_image_scale()
        # 确保调用父类的 resizeEvent 以保持正常行为
        QLabel.resizeEvent(self.processed_label, event)

    def process_image(self):
        """启动图像处理线程"""
        if self.image_path is None:
            print("请先选择一张图片！")
            return  # 未选择图片时直接返回

        # 禁用处理按钮
        self.process_button.setEnabled(False)

        # 创建并启动 Worker 线程
        self.worker = Worker(self.retina_process, self.image_path, self.save_dir)
        self.worker.finished.connect(self.on_process_finished)  # 连接处理完成信号
        self.worker.start()
        print("开始处理图像...")

    def on_process_finished(self, result_data):
        """处理完成后更新界面"""
        print("处理完成！")
        # 恢复处理按钮状态
        self.process_button.setEnabled(True)

        # 显示处理后的图片
        result_image_path = result_data['result_image_path']
        self.processed_pixmap = QPixmap(result_image_path)
        self.update_processed_image_scale()
        # 设置 label 的 resizeEvent，使图片可以随 label 大小变化而自动调整
        self.processed_label.resizeEvent = self.processed_label_resize_event
        # pixmap = QPixmap(result_image_path)
        # self.processed_label.setPixmap(pixmap)
        # self.processed_label.setScaledContents(True)

        # 显示处理数据
        # 这里根据分析的具体结果结构进行展示
        # data_text = f"眼底图像分析结果:\n"

        # 返回处理结果数据（原始数据 + 格式化的显示信息）
        # result_data = {
        #     'bm_layer': bm_layer,
        #     'best_circle': best_circle,
        #     'result_image_path': save_path,
        #     # 添加用于界面显示的格式化数据
        #     'display_data': {
        #         'circle_center': f"({best_circle[0]}, {best_circle[1]})" if best_circle else "未找到",
        #         'circle_radius': f"{best_circle[2]}像素 ({best_circle[2] / 10:.2f}mm)" if best_circle else "未找到",
        #         'diameter': f"{diameter_mm:.2f}mm" if diameter_mm else "未找到",
        #         'bm_points_count': f"{bm_layer.shape[0]}个点" if bm_layer.shape[0] > 0 else "0",
        #         'bm_depth_avg': f"{bm_avg_y:.2f}像素" if bm_avg_y is not None else "未知",
        #         'bm_variation': f"{bm_variation:.2f}像素" if bm_variation is not None else "未知",
        #         'status': "分析成功" if best_circle else "未找到合适的拟合圆"
        #     }
        # }
        # 从结果数据中提取显示数据并格式化
        if 'display_data' in result_data:
            data = result_data['display_data']
            data_text = "视网膜图像分析结果:\n\n"
            data_text += f"圆形中心位置: {data['circle_center']}\n"
            data_text += f"圆形半径: {data['circle_radius']}\n"
            data_text += f"直径: {data['diameter']}\n"
            data_text += f"BM层点数: {data['bm_points_count']}\n"
            data_text += f"BM层平均深度: {data['bm_depth_avg']}\n"
            data_text += f"BM层变异度: {data['bm_variation']}\n"
            data_text += f"分析状态: {data['status']}\n"

            # 设置文本到显示区域
            self.data_text.setText(data_text)

        # 示例：展示眼底各项指标
        # if 'cup_to_disc_ratio' in result_data:
        #     data_text += f"杯盘比(CDR): {result_data['cup_to_disc_ratio']:.4f}\n"
        #
        # if 'vessel_density' in result_data:
        #     data_text += f"血管密度: {result_data['vessel_density']:.4f}\n"
        #
        # if 'abnormalities' in result_data:
        #     data_text += f"检测到的异常: {', '.join(result_data['abnormalities'])}\n"
        #
        # self.data_text.setText(data_text)


# 主程序入口（示例）
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)  # 设置为暗色主题
    interface = RetinaInterface()
    interface.show()
    sys.exit(app.exec_())
