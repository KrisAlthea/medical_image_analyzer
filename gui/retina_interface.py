import os
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QSplitter, QLabel, QFileDialog, QFrame
from qfluentwidgets import (ScrollArea, FluentIcon, setTheme, Theme, TextEdit,
                            PrimaryPushButton, CardWidget, StrongBodyLabel, SubtitleLabel,
                           BodyLabel, InfoBar, InfoBarPosition,
                           TransparentToolButton, PushButton, IconWidget, ProgressRing)

from common.style_sheet import StyleSheet
from core.retina_process import RetinaProcess  # 需要创建这个处理类


class Worker(QThread):
    """后台线程类，用于异步执行图像处理"""
    finished = pyqtSignal(dict)  # 信号，传递处理结果
    progress = pyqtSignal(int)  # 进度信号

    def __init__(self, retina_process, image_path, save_dir):
        super().__init__()
        self.retina_process = retina_process  # RetinaProcess 实例
        self.image_path = image_path  # 输入图片路径
        self.save_dir = save_dir  # 输出保存目录

    def run(self):
        """线程执行函数，调用处理逻辑并发射结果"""
        # 模拟进度更新
        for i in range(0, 101, 10):
            self.progress.emit(i)
            self.msleep(100)
            
        circle_params = {
            "radius_range": range(200, 350, 5),
            "center_x_range": (0, 400),
            "center_y_range": (0, 640),
            "step": 20
        }
        result_data = self.retina_process.process_retina(self.image_path, circle_params, self.save_dir)
        self.progress.emit(100)
        self.finished.emit(result_data)


class ImageCard(CardWidget):
    """图片显示卡片组件"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("imageCard")
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)
        
        # 创建标题
        self.titleLabel = StrongBodyLabel(title, self)
        self.titleLabel.setObjectName("cardTitle")
        
        # 创建图片标签
        self.imageLabel = QLabel(self)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setMinimumSize(300, 200)
        self.imageLabel.setObjectName("imageLabel")
        self.imageLabel.setStyleSheet("background-color: rgba(0, 0, 0, 0.03); border-radius: 6px;")
        
        # 添加组件到布局
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.imageLabel, 1)
    
    def setPixmap(self, pixmap):
        """设置图片并保持纵横比"""
        if pixmap and not pixmap.isNull():
            self.pixmap = pixmap
            scaled_pixmap = pixmap.scaled(
                self.imageLabel.width(),
                self.imageLabel.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.imageLabel.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """处理大小调整事件"""
        super().resizeEvent(event)
        if hasattr(self, 'pixmap') and self.pixmap and not self.pixmap.isNull():
            self.setPixmap(self.pixmap)


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

        # 初始化界面组件
        self.__initHeader()
        self.__initImageArea()
        self.__initResultArea()
        self.__initWidget()

        # 连接信号与槽
        self.selectButton.clicked.connect(self.select_image)  # 选择图片按钮点击事件
        self.processButton.clicked.connect(self.process_image)  # 处理图片按钮点击事件
        self.resultCard.exportButton.clicked.connect(self.export_report)  # 导出报告按钮点击事件

        # 初始化变量
        self.worker = None  # 后台线程实例
        self.progressWidget = None  # 进度指示器

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
        
        # 添加按钮
        self.selectButton = PrimaryPushButton("选择图片", self, FluentIcon.FOLDER)
        self.selectButton.setObjectName("selectButton")
        self.processButton = PrimaryPushButton("开始分析", self, FluentIcon.PLAY)
        self.processButton.setObjectName("processButton")
        self.processButton.setEnabled(False)  # 初始禁用
        
        headerLayout.addWidget(self.selectButton)
        headerLayout.addSpacing(10)
        headerLayout.addWidget(self.processButton)
        
        # 添加分隔线
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setObjectName("headerSeparator")

    def __initImageArea(self):
        """初始化图片显示区域"""
        # 创建图片显示卡片
        self.originalCard = ImageCard("原始图像", self)
        self.processedCard = ImageCard("分析结果图像", self)
        
        # 创建图片区水平布局
        self.imageAreaWidget = QWidget(self)
        self.imageAreaLayout = QHBoxLayout(self.imageAreaWidget)
        self.imageAreaLayout.setContentsMargins(0, 0, 0, 0)
        self.imageAreaLayout.setSpacing(20)
        
        # 添加卡片到布局
        self.imageAreaLayout.addWidget(self.originalCard)
        self.imageAreaLayout.addWidget(self.processedCard)

    def __initResultArea(self):
        """初始化结果显示区域"""
        self.resultCard = ResultCard(self)

    def __initWidget(self):
        """初始化整体布局和样式"""
        self.view.setObjectName('view')
        self.setObjectName('retinaInterface')
        StyleSheet.RETINA_INTERFACE.apply(self)
        
        # 设置滚动区域属性
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        # 调整整体布局的间距和边距
        self.vBoxLayout.setContentsMargins(24, 24, 24, 24)
        self.vBoxLayout.setSpacing(20)
        
        # 添加组件到主布局
        self.vBoxLayout.addWidget(self.headerWidget)
        self.vBoxLayout.addWidget(self.separator)
        self.vBoxLayout.addWidget(self.imageAreaWidget)
        self.vBoxLayout.addWidget(self.resultCard)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # 添加自定义样式
        self.setStyleSheet("""
            #pageTitle {
                font-size: 22px;
                font-weight: bold;
            }
            
            #pageDescription {
                font-size: 14px;
                opacity: 0.8;
            }
            
            #headerSeparator {
                max-height: 1px;
                background-color: rgba(0, 0, 0, 0.1);
                margin: 5px 0px;
            }
            
            #cardTitle {
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            #imageCard, #resultCard {
                background-color: white;
                border-radius: 8px;
            }
            
            #exportButton {
                margin-top: 5px;
            }
        """)

    def select_image(self):
        """选择图片并显示到左侧卡片"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.jpg *.png *.bmp)")
        
        if file_dialog.exec_():
            self.image_path = file_dialog.selectedFiles()[0]
            self.original_pixmap = QPixmap(self.image_path)
            
            # 在图片卡片中显示图片
            self.originalCard.setPixmap(self.original_pixmap)
            
            # 清空之前的结果
            self.processedCard.imageLabel.clear()
            self.resultCard.textEdit.clear()
            
            # 启用处理按钮
            self.processButton.setEnabled(True)
            
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

        # 禁用处理按钮
        self.processButton.setEnabled(False)
        
        # 显示进度指示器
        self.show_progress_indicator()
        
        # 创建并启动 Worker 线程
        self.worker = Worker(self.retina_process, self.image_path, self.save_dir)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.start()

    def show_progress_indicator(self):
        """显示处理进度指示器"""
        # 在结果卡片上添加进度环
        if not self.progressWidget:
            self.progressWidget = QWidget(self)
            progressLayout = QVBoxLayout(self.progressWidget)
            progressLayout.setAlignment(Qt.AlignCenter)
            
            # 添加进度环
            self.progressRing = ProgressRing(self)
            self.progressRing.setFixedSize(60, 60)
            
            # 添加提示文字
            self.progressLabel = BodyLabel("正在分析图像...", self)
            self.progressLabel.setAlignment(Qt.AlignCenter)
            
            progressLayout.addWidget(self.progressRing, 0, Qt.AlignCenter)
            progressLayout.addWidget(self.progressLabel, 0, Qt.AlignCenter)
            
            # 清空并添加到结果卡片
            self.processedCard.imageLabel.clear()
            self.processedCard.vBoxLayout.addWidget(self.progressWidget)

    def update_progress(self, value):
        """更新进度值"""
        if hasattr(self, 'progressRing'):
            self.progressRing.setValue(value)

    def on_process_finished(self, result_data):
        """处理完成后更新界面"""
        # 恢复处理按钮状态
        self.processButton.setEnabled(True)
        
        # 移除进度指示器
        if self.progressWidget:
            self.progressWidget.setParent(None)
            self.progressWidget = None

        # 显示处理后的图片
        result_image_path = result_data['result_image_path']
        self.processed_pixmap = QPixmap(result_image_path)
        self.processedCard.setPixmap(self.processed_pixmap)

        # 从结果数据中提取显示数据并格式化
        if 'display_data' in result_data:
            data = result_data['display_data']
            data_text = "📊 视网膜图像分析结果\n\n"
            data_text += f"🔹 圆形中心位置: {data['circle_center']}\n"
            data_text += f"🔹 圆形半径: {data['circle_radius']}\n"
            data_text += f"🔹 直径: {data['diameter']}\n"
            data_text += f"🔹 BM层点数: {data['bm_points_count']}\n"
            data_text += f"🔹 BM层平均深度: {data['bm_depth_avg']}\n"
            data_text += f"🔹 BM层变异度: {data['bm_variation']}\n"
            data_text += f"🔹 分析状态: {data['status']}\n"

            # 设置文本到显示区域
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

    def export_report(self):
        """导出分析报告"""
        if not hasattr(self, 'processed_pixmap') or self.processed_pixmap is None:
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
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)  # 设置为暗色主题
    interface = RetinaInterface()
    interface.show()
    sys.exit(app.exec_())
