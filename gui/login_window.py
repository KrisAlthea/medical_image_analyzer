from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout,
    QWidget, QDesktopWidget, QStackedWidget, QLabel
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    Pivot, LineEdit, PasswordLineEdit,
    PrimaryPushButton, PushButton,
    TitleLabel, CardWidget,
    InfoBar, InfoBarPosition
)
from common.db import check_user, add_user
from common.style_sheet import StyleSheet


class LoginWindow(QDialog):
    """
    美化后的登录/注册窗口，顶部使用 Pivot 切换页面。
    登录/注册内容放在 CardWidget 中，并保持简洁统一的风格。
    登录成功后返回 Accepted。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("眼科图像处理系统 - 登录")
        self.setWindowIcon(QIcon(r"resource/images/logo.png"))
        # 移除帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        # 固定大小
        self.setFixedSize(480, 420)
        self._init_ui()
        self._center_on_screen()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 20)
        main_layout.setSpacing(10)

        # 顶部 Logo + 系统名 居中
        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 20, 0, 0)
        header_layout.setSpacing(12)
        header_layout.addStretch(1)
        icon = QLabel(header)
        icon.setPixmap(
            QPixmap(r"resource/images/logo.png").scaled(
                48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        title = TitleLabel("眼科图像处理系统", header)
        title.setStyleSheet("font-size:20px; font-weight:600;")
        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        main_layout.addWidget(header)

        # Pivot 导航，标签间距较小
        self.pivot = Pivot(self)
        # 调整间距并与 header 保持距离
        self.pivot.hBoxLayout.setSpacing(16)
        self.pivot.setContentsMargins(0, 10, 0, 10)
        self.pivot.addItem(
            routeKey="login", text="登录",
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.login_card)
        )
        self.pivot.addItem(
            routeKey="register", text="注册",
            onClick=lambda: self.stackedWidget.setCurrentWidget(self.register_card)
        )
        main_layout.addWidget(self.pivot, alignment=Qt.AlignHCenter)

        # 页面堆栈
        self.stackedWidget = QStackedWidget(self)
        self.stackedWidget.setContentsMargins(20, 0, 20, 0)

        # 登录卡片
        self.login_card = CardWidget(self)
        login_layout = QVBoxLayout(self.login_card)
        login_layout.setContentsMargins(24, 24, 24, 24)
        login_layout.setSpacing(16)
        lbl = TitleLabel("请输入您的账户信息", self.login_card)
        lbl.setStyleSheet("font-size:16px; font-weight:500;")
        login_layout.addWidget(lbl, alignment=Qt.AlignHCenter)
        form = QFormLayout()
        self.login_user = LineEdit(self.login_card)
        self.login_user.setPlaceholderText("用户名")
        self.login_pwd = PasswordLineEdit(self.login_card)
        self.login_pwd.setPlaceholderText("密码")
        form.addRow("用户名：", self.login_user)
        form.addRow("密码：", self.login_pwd)
        login_layout.addLayout(form)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.forgot_btn = PushButton("忘记密码", self.login_card)
        self.login_btn = PrimaryPushButton("登录", self.login_card)
        self.login_btn.setFixedWidth(120)
        btn_row.addWidget(self.forgot_btn)
        btn_row.addWidget(self.login_btn)
        login_layout.addLayout(btn_row)
        self.stackedWidget.addWidget(self.login_card)

        # 注册卡片
        self.register_card = CardWidget(self)
        reg_layout = QVBoxLayout(self.register_card)
        reg_layout.setContentsMargins(24, 24, 24, 24)
        reg_layout.setSpacing(16)
        lbl2 = TitleLabel("创建新用户账户", self.register_card)
        lbl2.setStyleSheet("font-size:16px; font-weight:500;")
        reg_layout.addWidget(lbl2, alignment=Qt.AlignHCenter)
        reg_form = QFormLayout()
        self.reg_user = LineEdit(self.register_card)
        self.reg_user.setPlaceholderText("用户名")
        self.reg_pwd = PasswordLineEdit(self.register_card)
        self.reg_pwd.setPlaceholderText("密码")
        self.reg_conf = PasswordLineEdit(self.register_card)
        self.reg_conf.setPlaceholderText("确认密码")
        reg_form.addRow("用户名：", self.reg_user)
        reg_form.addRow("密码：", self.reg_pwd)
        reg_form.addRow("确认密码：", self.reg_conf)
        reg_layout.addLayout(reg_form)
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch(1)
        self.reg_btn = PrimaryPushButton("注册", self.register_card)
        self.reg_btn.setFixedWidth(120)
        btn_row2.addWidget(self.reg_btn)
        reg_layout.addLayout(btn_row2)
        self.stackedWidget.addWidget(self.register_card)

        main_layout.addWidget(self.stackedWidget)
        main_layout.addStretch(1)

        # 默认显示登录
        self.pivot.setCurrentItem("login")
        self.stackedWidget.setCurrentWidget(self.login_card)

        # 设置样式表
        # self.setObjectName("loginWindow")
        StyleSheet.LOGIN_WINDOW.apply(self)

        # 信号绑定
        self.login_btn.clicked.connect(self._on_login)
        self.forgot_btn.clicked.connect(self._on_forgot)
        self.reg_btn.clicked.connect(self._on_register)

    def _center_on_screen(self):
        rect = QDesktopWidget().availableGeometry()
        self.move((rect.width() - self.width()) // 2,
                  (rect.height() - self.height()) // 2)

    def _on_login(self):
        u, p = self.login_user.text().strip(), self.login_pwd.text().strip()
        if not u or not p:
            InfoBar.error("登录失败", "用户名或密码不能为空", position=InfoBarPosition.TOP, parent=self)
            return
        if check_user(u, p):
            self.accept()
        else:
            InfoBar.error("登录失败", "用户名或密码错误", position=InfoBarPosition.TOP, parent=self)

    def _on_forgot(self):
        InfoBar.info("忘记密码", "请联系管理员重置密码", position=InfoBarPosition.TOP, parent=self)

    def _on_register(self):
        u, p, c = self.reg_user.text().strip(), self.reg_pwd.text().strip(), self.reg_conf.text().strip()
        if not u or not p:
            InfoBar.error("注册失败", "用户名或密码不能为空", position=InfoBarPosition.TOP, parent=self)
            return
        if p != c:
            InfoBar.error("注册失败", "两次密码不一致", position=InfoBarPosition.TOP, parent=self)
            return
        if add_user(u, p):
            InfoBar.success("注册成功", "请切换到登录页登录", position=InfoBarPosition.TOP, parent=self)
            self.pivot.setCurrentItem("login")
            self.stackedWidget.setCurrentWidget(self.login_card)
            # 填充刚注册的用户名和密码
            self.login_user.setText(u)
            self.login_pwd.setText(p)
        else:
            InfoBar.error("注册失败", "用户名已存在", position=InfoBarPosition.TOP, parent=self)
