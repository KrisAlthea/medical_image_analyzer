# gui/main window.py
import os
import sys
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QApplication, QMessageBox
)

from core.analyzer import MedicalImageAnalyzer

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("医学图像识别系统")
        self.resize(800, 600)


        self.analyzer = MedicalImageAnalyzer()
        self._init_ui()

    def _init_ui(self):
        # 使用QTabWidget分别放置晶状体与视网膜处理界面
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.lens_tab = QWidget()
        self.retina_tab = QWidget()
        self.tabs.addTab(self.lens_tab, "晶状体")
        self.tabs.addTab(self.retina_tab, "视网膜")

        self._init_lens_tab()
        self._init_retina_tab()

    def _init_lens_tab(self):
        layout = QVBoxLayout()

        # 文件路径输入框和选择按钮
        self.lens_image_path_le = QLineEdit()
        self.lens_image_path_le.setPlaceholderText("选择晶状体图像文件")
        btn_select_lens_image = QPushButton("选择图像")
        btn_select_lens_image.clicked.connect(self.select_lens_image)

        self.lens_model_path_le = QLineEdit()
        self.lens_model_path_le.setPlaceholderText("选择晶状体模型文件")
        btn_select_lens_model = QPushButton("选择模型")
        btn_select_lens_model.clicked.connect(self.select_lens_model)

        btn_process_lens = QPushButton("处理晶状体")
        btn_process_lens.clicked.connect(self.process_lens)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel("图像路径:"))
        hlayout1.addWidget(self.lens_image_path_le)
        hlayout1.addWidget(btn_select_lens_image)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(QLabel("模型路径:"))
        hlayout2.addWidget(self.lens_model_path_le)
        hlayout2.addWidget(btn_select_lens_model)

        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addWidget(btn_process_lens)
        self.lens_tab.setLayout(layout)

    def _init_retina_tab(self):
        layout = QVBoxLayout()

        self.bm_layer_path_le = QLineEdit()
        self.bm_layer_path_le.setPlaceholderText("选择BM层数据文件 (.npy)")
        btn_select_bm_layer = QPushButton("选择BM数据")
        btn_select_bm_layer.clicked.connect(self.select_bm_layer)

        self.bscan_image_path_le = QLineEdit()
        self.bscan_image_path_le.setPlaceholderText("选择B-scan图像文件")
        btn_select_bscan_image = QPushButton("选择B-scan图像")
        btn_select_bscan_image.clicked.connect(self.select_bscan_image)

        btn_process_retina = QPushButton("处理视网膜")
        btn_process_retina.clicked.connect(self.process_retina)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel("BM层文件:"))
        hlayout1.addWidget(self.bm_layer_path_le)
        hlayout1.addWidget(btn_select_bm_layer)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(QLabel("B-scan图像:"))
        hlayout2.addWidget(self.bscan_image_path_le)
        hlayout2.addWidget(btn_select_bscan_image)

        layout.addLayout(hlayout1)
        layout.addLayout(hlayout2)
        layout.addWidget(btn_process_retina)
        self.retina_tab.setLayout(layout)

    def select_lens_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择晶状体图像", os.getcwd(), "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.lens_image_path_le.setText(file_path)

    def select_lens_model(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择晶状体模型", os.getcwd(), "Model Files (*.pth)")
        if file_path:
            self.lens_model_path_le.setText(file_path)

    def select_bm_layer(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择BM层数据", os.getcwd(), "Numpy Files (*.npy)")
        if file_path:
            self.bm_layer_path_le.setText(file_path)

    def select_bscan_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择B-scan图像", os.getcwd(), "Images (*.png *.jpg *.bmp)")
        if file_path:
            self.bscan_image_path_le.setText(file_path)

    def process_lens(self):
        image_path = self.lens_image_path_le.text().strip()
        model_path = self.lens_model_path_le.text().strip()
        if not image_path or not model_path:
            QMessageBox.warning(self, "警告", "请先选择晶状体图像和模型文件")
            return
        self.analyzer.process_lens(image_path, model_path)

    def process_retina(self):
        bm_layer_path = self.bm_layer_path_le.text().strip()
        bscan_image_path = self.bscan_image_path_le.text().strip()
        if not bm_layer_path or not bscan_image_path:
            QMessageBox.warning(self, "警告", "请先选择BM层数据和B-scan图像")
            return
        self.analyzer.process_retina(bm_layer_path, bscan_image_path)

if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
