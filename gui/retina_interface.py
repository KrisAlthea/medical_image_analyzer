import os

import cv2
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QFileDialog
from qfluentwidgets import (ScrollArea, FluentIcon, TextEdit,
                            CardWidget, StrongBodyLabel, SubtitleLabel,
                            BodyLabel, InfoBar, InfoBarPosition,
                            PushButton, IconWidget, ImageLabel)

from common.db import add_history_record
from common.style_sheet import StyleSheet
# from common.style_sheet import StyleSheet
from core.retina_process import RetinaProcess


class Worker(QThread):
    """后台线程类，用于异步执行图像处理"""
    finished = pyqtSignal(dict)

    def __init__(self, retina_process, image_path):
        super().__init__()
        self.retina_process = retina_process
        self.image_path = image_path

    def run(self):
        result_data = self.retina_process.process_retina(self.image_path)
        self.finished.emit(result_data)


class ImageCard(CardWidget):
    """图片显示卡片组件"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.setObjectName("imageCard")

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)

        # 创建标题
        self.titleLabel = StrongBodyLabel(title, self)
        self.titleLabel.setObjectName("cardTitle")

        # 创建图片标签
        self.imageLabel = ImageLabel(self)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setObjectName("imageLabel")
        self.imageLabel.setStyleSheet("background-color: rgba(0, 0, 0, 0.03); border-radius: 6px;")

        # 添加组件到布局
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.imageLabel, 1)

    def setPixmap(self, pixmap):
        """设置图片并保持纵横比"""
        if pixmap and not pixmap.isNull():
            self.pixmap = pixmap
            scaled = pixmap.scaled(
                self.imageLabel.width(),
                self.imageLabel.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.imageLabel.setPixmap(scaled)

    def resizeEvent(self, event):
        """处理大小调整事件"""
        super().resizeEvent(event)
        if hasattr(self, 'pixmap') and self.pixmap and not self.pixmap.isNull():
            self.setPixmap(self.pixmap)


class ControlCard(CardWidget):
    """控制按钮卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("controlCard")

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)

        # 创建标题
        self.titleLabel = StrongBodyLabel("操作面板", self)
        self.titleLabel.setObjectName("cardTitle")

        # 创建按钮
        self.img_select_btn = PushButton("选择图片", self)
        self.img_select_btn.setObjectName("img_select_btn")
        self.img_process_btn = PushButton("开始分析", self)
        self.img_process_btn.setObjectName("img_process_btn")
        self.origin_img_btn = PushButton("原图", self)
        self.origin_img_btn.setObjectName("origin_img_btn")
        self.result_img_btn = PushButton("结果图", self)
        self.result_img_btn.setObjectName("result_img_btn")

        # 添加组件到布局
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.img_select_btn)
        self.vBoxLayout.addWidget(self.img_process_btn)
        self.vBoxLayout.addWidget(self.origin_img_btn)
        self.vBoxLayout.addWidget(self.result_img_btn)
        # 作用是让按钮在布局中不被垂直拉伸
        # self.vBoxLayout.addStretch(1)


class ResultCard(CardWidget):
    """分析结果显示卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)

        # 创建标题
        self.titleLabel = StrongBodyLabel("分析结果", self)
        self.titleLabel.setObjectName("cardTitle")

        # 创建文本编辑区
        self.textEdit = TextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName("resultText")
        self.textEdit.setStyleSheet("background-color: rgba(0, 0, 0, 0.02); border-radius: 6px;")

        # 添加导出按钮
        self.exportButton = PushButton("导出报告", self, FluentIcon.SAVE)
        self.exportButton.setObjectName("exportButton")

        # 添加组件到布局
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.textEdit, 1)
        self.vBoxLayout.addWidget(self.exportButton)


class RetinaInterface(ScrollArea):

    def __init__(self, parent=None, current_user_id: int = 0):
        super().__init__(parent=parent)
        self.current_user_id = current_user_id
        self.resized_path = None
        self.image_path = None
        self.result_path = None
        self.processed_flag = None

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        # 初始化界面组件
        self.__initHeader()
        self.__initCenterArea()
        self.__initWidget()

        # 连接信号与槽
        self.controlCard.img_select_btn.clicked.connect(self.select_image)  # 选择图片按钮点击事件
        self.controlCard.img_process_btn.clicked.connect(self.process_image)  # 处理图片按钮点击事件
        self.controlCard.origin_img_btn.clicked.connect(lambda: self.imageCard.setPixmap(QPixmap(self.resized_path)))
        self.controlCard.result_img_btn.clicked.connect(lambda: self.imageCard.setPixmap(QPixmap(self.result_path)))
        self.resultCard.exportButton.clicked.connect(self.export_report)  # 导出报告按钮点击事件

        # 初始化变量
        self.retina_process = RetinaProcess()  # 实例化处理类
        self.worker = None  # 后台线程实例

    def __initHeader(self):
        """初始化页面顶部区域"""
        # 创建顶部标题区域
        self.headerWidget = QWidget(self)
        headerLayout = QHBoxLayout(self.headerWidget)
        headerLayout.setContentsMargins(20, 10, 20, 10)

        # 添加图标
        self.iconWidget = IconWidget(FluentIcon.IOT, self.headerWidget)
        self.iconWidget.setFixedSize(32, 32)

        # 添加标题
        self.titleLabel = SubtitleLabel("视网膜分析", self.headerWidget)
        self.titleLabel.setObjectName("pageTitle")

        # 添加描述
        self.descriptionLabel = BodyLabel("提取视网膜BM层边界，进行圆形拟合计算直径参数", self.headerWidget)
        self.descriptionLabel.setObjectName("pageDescription")

        # 创建标题文本布局
        textLayout = QVBoxLayout()
        textLayout.setSpacing(0)
        textLayout.addWidget(self.titleLabel)
        textLayout.addWidget(self.descriptionLabel)

        # 将组件添加到顶部布局
        headerLayout.addWidget(self.iconWidget)
        headerLayout.addSpacing(10)
        headerLayout.addLayout(textLayout)
        headerLayout.addStretch(1)

    def __initCenterArea(self):

        self.centralAreaWidget = QWidget(self)
        centerLayout = QHBoxLayout(self.centralAreaWidget)

        # 左侧区域
        self.leftWidget = QWidget(self.centralAreaWidget)
        self.leftWidget.setMinimumSize(750, 500)
        leftLayout = QVBoxLayout(self.leftWidget)
        # 图片卡片
        self.imageCard = ImageCard("图像", self.centralAreaWidget)
        leftLayout.addWidget(self.imageCard)
        # 右侧区域
        self.rightWidget = QWidget(self.centralAreaWidget)
        self.rightWidget.setMinimumSize(250, 500)
        self.rightWidget.setMaximumWidth(350)
        rightLayout = QVBoxLayout(self.rightWidget)
        # 控制按钮卡片
        self.controlCard = ControlCard(self)
        self.controlCard.setObjectName("controlCard")
        rightLayout.addWidget(self.controlCard)
        # 结果卡片
        self.resultCard = ResultCard(self)
        self.resultCard.setObjectName("resultCard")
        rightLayout.addWidget(self.resultCard)
        # 添加左, 右区域到中央区域
        centerLayout.addWidget(self.leftWidget)
        centerLayout.addWidget(self.rightWidget)
        centerLayout.setContentsMargins(1, 1, 1, 1)
        centerLayout.setSpacing(10)

    def __initWidget(self):
        """初始化整体布局和样式"""
        self.view.setObjectName('view')
        self.setObjectName('retinaInterface')
        StyleSheet.RETINA_INTERFACE.apply(self)

        # 设置滚动区域属性
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        # 调整整体布局
        self.vBoxLayout.setContentsMargins(24, 24, 24, 24)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        # 添加组件到主布局
        self.vBoxLayout.addWidget(self.headerWidget)
        self.vBoxLayout.addWidget(self.centralAreaWidget)

    def select_image(self):
        """选择图片并显示到左侧卡片"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.jpg *.png *.bmp)")

        if file_dialog.exec_():
            self.image_path = file_dialog.selectedFiles()[0]
            self.imageCard.imageLabel.clear()
            self.resultCard.textEdit.clear()

            # 1. 读取输入灰度图像
            img = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)

            # 3. 将灰度图转换为BGR彩色图，便于绘制彩色标记
            img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            # 4. 为后续绘制和适配固定尺寸，计算上下左右的黑色填充（pad）
            target_h, target_w = 1024, 1440
            h, w = img_color.shape[:2]
            pad_h = max(target_h - h, 0)
            pad_w = max(target_w - w, 0)
            top, bottom = pad_h // 2, pad_h - pad_h // 2
            left, right = pad_w // 2, pad_w - pad_w // 2

            # 5. 扩充彩色图像至目标大小，填充值为黑色
            img_pad = cv2.copyMakeBorder(img_color, top, bottom, left, right,
                                         cv2.BORDER_CONSTANT, value=[0, 0, 0])

            # 8. 构造输出目录并确保存在，然后保存结果图像
            output_dir = os.path.join(
                r"D:\Code\PyCharm_ws\cursor\medical_image_analyzer\output",
                "retina"
            )
            os.makedirs(output_dir, exist_ok=True)

            name, ext = os.path.splitext(os.path.basename(self.image_path))
            save_path = os.path.join(output_dir, f"{name}-resized{ext}")
            cv2.imwrite(save_path, img_pad)

            self.resized_path = save_path

            # 在图片卡片中显示图片
            self.imageCard.setPixmap(QPixmap(self.resized_path))
            # 清空之前的结果
            self.resultCard.textEdit.clear()

            # 显示提示消息
            InfoBar.success(
                title='已选择图片',
                content=f"图片已加载: {os.path.basename(self.image_path)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self,
                duration=3000
            )

    def process_image(self):
        """启动图像处理线程"""
        if self.image_path is None:
            return

        # 先禁用按钮，避免重复点击
        self.controlCard.img_process_btn.setEnabled(False)

        # 创建并启动 Worker 线程
        self.worker = Worker(self.retina_process, self.image_path)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()

    def on_process_finished(self, result_data):
        """处理完成后更新界面"""

        # 显示处理后的图片
        self.result_path = result_data['result_image_path']
        self.imageCard.imageLabel.clear()
        self.imageCard.setPixmap(QPixmap(self.result_path))
        self.processed_flag = True

        # 启用按钮
        self.controlCard.img_process_btn.setEnabled(True)

        # result_data = {
        #     'circle_radius': r,
        #     'circle_curvature': 1.0 / r if r != 0 else None,
        #     'result_image_path': save_path,
        # }

        # 显示处理结果
        circle_radius = result_data['circle_radius']
        circle_curvature = result_data['circle_curvature']

        # 从结果数据中提取显示数据并格式化
        data_text = (
            f"圆形半径: {circle_radius:.2f} 像素\n"
            f"曲率: {circle_curvature:.2f} 像素\n"
        )
        self.resultCard.textEdit.setText(data_text)

        # 显示成功消息
        InfoBar.success(
            title='分析完成',
            content="视网膜BM层边界提取和圆形拟合已完成",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            parent=self,
            duration=3000
        )

        # 记录历史
        add_history_record(
            original_path=self.resized_path,
            processed_path=self.result_path,
            operator_id=self.current_user_id,
            is_retina=True
        )

        # 清理工作线程
        self.worker.quit()
        self.worker = None

    def export_report(self):
        """导出分析报告"""
        if self.image_path is None or not self.processed_flag:
            InfoBar.warning(
                title='无法导出',
                content="请先分析图像再导出报告",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                parent=self,
                duration=3000
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "PDF文件 (*.pdf);;文本文件 (*.txt)"
        )

        if file_path:
            # 这里仅模拟导出功能
            InfoBar.success(
                title='导出成功',
                content=f"报告已保存至: {os.path.basename(file_path)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                parent=self,
                duration=3000
            )


# 主程序入口（示例）
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    interface = RetinaInterface()
    interface.show()
    sys.exit(app.exec_())
