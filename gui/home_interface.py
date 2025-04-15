from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QSize, QEvent, QTimer
from PyQt5.QtGui import QPixmap, QDesktopServices, QIcon, QColor, QPainter, QLinearGradient
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from qfluentwidgets import (ScrollArea, SimpleCardWidget, IconWidget, TransparentToolButton,
                           BodyLabel, CaptionLabel, TitleLabel, CardWidget, 
                           FluentIcon, InfoBar, InfoBarPosition, PrimaryPushButton, SubtitleLabel,
                           StrongBodyLabel, Theme, isDarkTheme)
from common.style_sheet import StyleSheet


class FunctionCard(CardWidget):
    """功能卡片组件，用于展示功能入口"""
    
    clicked = pyqtSignal()
    
    def __init__(self, icon, title, description, parent=None):
        super().__init__(parent)
        self.iconWidget = IconWidget(icon, self)
        self.titleLabel = StrongBodyLabel(title, self)
        self.descriptionLabel = BodyLabel(description, self)
        self.enterButton = TransparentToolButton(FluentIcon.CHEVRON_RIGHT, self)
        
        # 设置图标尺寸和样式
        self.iconWidget.setFixedSize(70, 70)
        self.iconWidget.setBaseSize(QSize(40, 40))
        
        # 设置布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(24, 20, 24, 20)
        self.vBoxLayout.setSpacing(16)
        
        # 创建标题行布局
        titleLayout = QHBoxLayout()
        titleLayout.setContentsMargins(0, 0, 0, 0)
        titleLayout.setSpacing(16)
        titleLayout.addWidget(self.iconWidget)
        
        # 创建文本布局
        textLayout = QVBoxLayout()
        textLayout.setSpacing(6)
        textLayout.addWidget(self.titleLabel)
        textLayout.addWidget(self.descriptionLabel)
        
        titleLayout.addLayout(textLayout)
        titleLayout.addStretch(1)
        titleLayout.addWidget(self.enterButton)
        
        self.vBoxLayout.addLayout(titleLayout)
        
        # 连接信号
        self.enterButton.clicked.connect(self.clicked)
        self.clicked.connect(self.onClicked)
        
        # 设置样式
        self.setFixedHeight(130)
        self.setObjectName("functionCard")
        
        # 添加阴影效果
        self.shadowEffect = QGraphicsDropShadowEffect(self)
        self.shadowEffect.setBlurRadius(15)
        self.shadowEffect.setOffset(0, 2)
        self.shadowEffect.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(self.shadowEffect)
        
        # 添加事件过��器用于悬停效果
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        if obj == self:
            if event.type() == QEvent.Enter:
                # 鼠标进入时的效果
                effect = self.graphicsEffect()
                if effect:
                    effect.setBlurRadius(25)
                    effect.setColor(QColor(0, 0, 0, 80))
                return True
            elif event.type() == QEvent.Leave:
                # 鼠标离开时的效果
                effect = self.graphicsEffect()
                if effect:
                    effect.setBlurRadius(15)
                    effect.setColor(QColor(0, 0, 0, 50))
                return True
        return super().eventFilter(obj, event)
    
    def onClicked(self):
        """点击效果"""
        # 临时改变阴影效果创建点击反馈
        effect = self.graphicsEffect()
        if effect:
            original_blur = effect.blurRadius()
            original_color = effect.color()
            effect.setBlurRadius(5)
            effect.setColor(QColor(0, 0, 0, 30))
            QTimer.singleShot(100, lambda: self.resetEffect(effect, original_blur, original_color))
    
    def resetEffect(self, effect, blur, color):
        """重置阴影效果"""
        if effect:
            effect.setBlurRadius(blur)
            effect.setColor(color)


class GradientBanner(CardWidget):
    """带渐变背景的Banner"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gradientBanner")
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变
        if isDarkTheme():
            gradient = QLinearGradient(0, 0, self.width(), 0)
            gradient.setColorAt(0, QColor(44, 62, 80))
            gradient.setColorAt(1, QColor(52, 73, 94))
        else:
            gradient = QLinearGradient(0, 0, self.width(), 0)
            gradient.setColorAt(0, QColor(65, 105, 225, 50))  # 医疗蓝色调
            gradient.setColorAt(1, QColor(135, 206, 235, 30))
            
        painter.fillRect(self.rect(), gradient)


class HomeInterface(ScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        
        # 创建界面组件
        self.__initBanner()
        self.__initFunctionCards()
        self.__initFooter()
        self.__initWidget()
        
        # 导入额外模块
        from PyQt5.QtCore import QTimer

    def __initBanner(self):
        """初始化Banner区域"""
        self.banner = GradientBanner(self)
        
        # 创建横幅布局
        bannerLayout = QHBoxLayout(self.banner)
        bannerLayout.setContentsMargins(40, 30, 40, 30)
        bannerLayout.setSpacing(30)
        
        # 创建图标
        iconWidget = IconWidget(FluentIcon.HEART, self.banner)
        iconWidget.setFixedSize(80, 80)
        iconWidget.setBaseSize(QSize(45, 45))
        
        # 为图标添加阴影效果
        iconShadow = QGraphicsDropShadowEffect()
        iconShadow.setBlurRadius(20)
        iconShadow.setColor(QColor(0, 0, 0, 60))
        iconShadow.setOffset(0, 0)
        iconWidget.setGraphicsEffect(iconShadow)

        # 创建文本区域
        textLayout = QVBoxLayout()
        textLayout.setSpacing(10)
        
        # 添加标题和描述
        titleLabel = TitleLabel("医学图像分析器", self.banner)
        titleLabel.setObjectName("bannerTitle")
        
        descriptionLabel = BodyLabel(
            "集成化医学图像处理平台，实现晶状体与视网膜图像的智能分析", 
            self.banner
        )
        descriptionLabel.setObjectName("bannerDescription")
        
        # 添加"开始体验"按钮
        startButton = PrimaryPushButton("开始体验", self.banner)
        startButton.setFixedWidth(120)
        
        textLayout.addWidget(titleLabel)
        textLayout.addWidget(descriptionLabel)
        textLayout.addSpacing(10)
        textLayout.addWidget(startButton)
        
        # 将组件添加到横幅布局
        bannerLayout.addWidget(iconWidget)
        bannerLayout.addLayout(textLayout)
        bannerLayout.addStretch(1)
        
    def __initFunctionCards(self):
        """初始化功能卡片区域"""
        # 创建功能卡片区域标题
        self.sectionTitle = SubtitleLabel("功能模块", self)
        self.sectionTitle.setObjectName("sectionTitle")
        
        # 创建功能卡片容器
        self.cardContainer = QWidget(self)
        self.cardLayout = QHBoxLayout(self.cardContainer)
        self.cardLayout.setContentsMargins(36, 10, 36, 10)
        self.cardLayout.setSpacing(30)
        
        # 创建晶状体分析卡片
        self.lensCard = FunctionCard(
            FluentIcon.PEOPLE,  # 使用更贴合主题的图标
            "晶状体分析",
            "提取晶状体边界，进行曲线拟合并生成详细分析报告",
            self
        )
        
        # 创建视网膜分析卡片
        self.retinaCard = FunctionCard(
            FluentIcon.PEOPLE,  # 使用更贴合主题的图标
            "视网膜分析",
            "识别眼底视网膜BM层，进行圆形拟合并计算关键参数",
            self
        )
        
        # 将卡片添加到布局
        self.cardLayout.addWidget(self.lensCard)
        self.cardLayout.addWidget(self.retinaCard)
        
    def __initFooter(self):
        """初始化页脚区域"""
        self.footer = CardWidget(self)
        self.footer.setObjectName("footer")
        footerLayout = QVBoxLayout(self.footer)
        footerLayout.setContentsMargins(36, 24, 36, 24)
        footerLayout.setSpacing(16)
        
        # 使用说明文本
        self.tipsLabel = SubtitleLabel("使用提示：点击功能卡片进入相应的分析模块", self)
        self.tipsLabel.setAlignment(Qt.AlignCenter)
        self.tipsLabel.setObjectName("tipsLabel")
        
        # 分割线
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.HLine)
        self.separator.setFrameShadow(QFrame.Sunken)
        self.separator.setObjectName("footerSeparator")
        
        # 添加版本和版权信息
        self.versionInfo = CaptionLabel("版本 1.0.0 | © 2025 医学图像分析团队", self)
        self.versionInfo.setAlignment(Qt.AlignCenter)
        self.versionInfo.setObjectName("versionInfo")
        
        # 添加组件到页脚
        footerLayout.addWidget(self.tipsLabel)
        footerLayout.addWidget(self.separator)
        footerLayout.addWidget(self.versionInfo)
        
    def __initWidget(self):
        self.view.setObjectName('view')
        self.setObjectName('homeInterface')
        StyleSheet.HOME_INTERFACE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        # 调整整体布局的间距和边距
        self.vBoxLayout.setContentsMargins(24, 24, 24, 24)
        self.vBoxLayout.setSpacing(30)
        self.vBoxLayout.addWidget(self.banner)
        self.vBoxLayout.addSpacing(15)
        self.vBoxLayout.addWidget(self.sectionTitle)
        self.vBoxLayout.addWidget(self.cardContainer)
        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addWidget(self.footer)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        
        # 添加自定义样式
        self.setStyleSheet("""
            #bannerTitle {
                font-size: 28px;
                font-weight: bold;
            }
            
            #bannerDescription {
                font-size: 15px;
                opacity: 0.85;
            }
            
            #sectionTitle {
                font-size: 20px;
                font-weight: bold;
                margin-left: 36px;
            }
            
            #footer {
                background-color: rgba(245, 245, 245, 0.7);
                border-radius: 10px;
            }
            
            #footerSeparator {
                max-height: 1px;
                background-color: rgba(0, 0, 0, 0.1);
            }
            
            #versionInfo {
                opacity: 0.7;
            }
            
            #tipsLabel {
                font-weight: normal;
                color: #555;
            }
            
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
    def showLensAnalysisInfo(self):
        """显示晶状体分析功能简介"""
        InfoBar.success(
            title='晶状体分析',
            content="实现晶状体边界的自动提取和曲线拟合",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            parent=self,
            duration=3000
        )
        
    def showRetinaAnalysisInfo(self):
        """显示视网膜分析功能简介"""
        InfoBar.success(
            title='视网膜分析',
            content="实现眼底视网膜BM层的识别与圆形拟合",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            parent=self,
            duration=3000
        )
        
    def connectSignalToSlot(self, switchTo):
        """连接信号到切换界面的槽函数"""
        self.lensCard.clicked.connect(lambda: switchTo(0))
        self.lensCard.clicked.connect(self.showLensAnalysisInfo)
        self.retinaCard.clicked.connect(lambda: switchTo(1))
        self.retinaCard.clicked.connect(self.showRetinaAnalysisInfo)
        
        # 连接Banner中的开始按钮
        self.banner.findChild(PrimaryPushButton).clicked.connect(lambda: switchTo(0))
