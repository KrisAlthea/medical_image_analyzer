# main.py
import os

from PyQt5.QtCore import Qt

from common.config import cfg
from common.db import initialize_db, get_user_id
from gui.login_window import LoginWindow
from gui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication, QDialog
import sys

def main():

    # 初始化数据库
    initialize_db()

    # enable dpi scale
    if cfg.get(cfg.dpiScale) == "Auto":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # create application
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # 弹出登录窗口
    login = LoginWindow()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)
    else:
        user_id = get_user_id(login.login_user.text())

    window = MainWindow(cur_user_id=user_id)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
