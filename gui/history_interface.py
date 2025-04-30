# ui/history_interface.py

import sqlite3
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from qfluentwidgets import (
    ScrollArea, CardWidget, IconWidget, StrongBodyLabel,
    FluentIcon, SubtitleLabel, BodyLabel,
    PushButton, InfoBar, InfoBarPosition
)
from common.db import get_connection, clear_history, add_history_record


class TableCard(CardWidget):
    """封装了一个带标题的 Table 卡片"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("tableCard")

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(8)

        # 卡片标题
        self.titleLabel = StrongBodyLabel(title, self)
        self.titleLabel.setObjectName("cardTitle")
        self.vBoxLayout.addWidget(self.titleLabel)

        # 表格
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "操作时间","操作人", "原始图片路径",
            "处理后路径", "类型"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.vBoxLayout.addWidget(self.table, 1)


class HistoryInterface(ScrollArea):
    """
    历史记录管理界面——展示、刷新、清空操作记录。
    样式与 retina_interface.py 保持一致，
    将“刷新”“清空”按钮移到 Header 区右侧。
    """

    def __init__(self, parent=None, current_user_id: int = 0):
        super().__init__(parent=parent)
        self.current_user_id = current_user_id

        # 根容器与布局
        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        # 初始化各部分
        self.__initHeader()
        self.__initCenterArea()
        self.__initWidget()

        # 首次拉取数据
        self._load_data()

    def __initHeader(self):
        """顶部：图标 + 标题 + 描述 + 操作按钮"""
        self.headerWidget = QWidget(self)
        hl = QHBoxLayout(self.headerWidget)
        hl.setContentsMargins(20, 10, 20, 10)

        icon = IconWidget(FluentIcon.HISTORY, self.headerWidget)
        icon.setFixedSize(32, 32)
        icon.setObjectName("pageIcon")
        title = SubtitleLabel(self.headerWidget)
        title.setText("历史记录")
        title.setObjectName("pageTitle")
        desc = BodyLabel(self.headerWidget)
        desc.setText("查看并管理所有图像处理操作记录")
        desc.setObjectName("pageDescription")

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.refresh_btn = PushButton("刷新", self.headerWidget)
        self.clear_btn = PushButton("清空记录", self.headerWidget)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.clear_btn)

        # 标题文本布局
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.addWidget(title)
        text_layout.addWidget(desc)

        # 组装 Header
        hl.addWidget(icon)
        hl.addSpacing(10)
        hl.addLayout(text_layout)
        hl.addStretch(1)
        hl.addLayout(btn_layout)
        self.vBoxLayout.addWidget(self.headerWidget)

        # 按钮信号
        self.refresh_btn.clicked.connect(self._load_data)
        self.clear_btn.clicked.connect(self._on_clear)

    def __initCenterArea(self):
        """中间区：仅展示表格"""
        self.centralAreaWidget = QWidget(self)
        cl = QVBoxLayout(self.centralAreaWidget)
        cl.setContentsMargins(1, 1, 1, 1)
        cl.setSpacing(10)

        self.tableCard = TableCard("历史记录", self.centralAreaWidget)
        cl.addWidget(self.tableCard, 1)

        self.vBoxLayout.addWidget(self.centralAreaWidget)

    def __initWidget(self):
        """配置 ScrollArea 属性"""
        self.view.setObjectName('historyView')
        self.setObjectName('historyInterface')
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.vBoxLayout.setContentsMargins(24, 24, 24, 24)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

    def _load_data(self):
        """查询并展示历史记录"""
        conn = get_connection()
        cur = conn.execute('''
            SELECT
                -- h.id,
                h.original_path,
                h.processed_path,
                h.timestamp,
                u.username AS operator,
                h.is_retina
            FROM history h
            LEFT JOIN users u ON h.operator_id = u.id
            ORDER BY h.timestamp DESC
        ''')
        rows = cur.fetchall()
        conn.close()

        tbl = self.tableCard.table
        tbl.setRowCount(len(rows))
        for r, rec in enumerate(rows):
            # tbl.setItem(r, 0, QTableWidgetItem(str(rec["id"])))
            tbl.setItem(r, 0, QTableWidgetItem(rec["timestamp"]))
            tbl.setItem(r, 1, QTableWidgetItem(rec["operator"] or ""))
            tbl.setItem(r, 2, QTableWidgetItem(rec["original_path"]))
            tbl.setItem(r, 3, QTableWidgetItem(rec["processed_path"]))
            kind = "视网膜" if rec["is_retina"] else "晶状体"
            tbl.setItem(r, 4, QTableWidgetItem(kind))

        InfoBar.info(
            "已刷新",
            f"共 {len(rows)} 条记录",
            InfoBarPosition.TOP,
            parent=self
        )

    def _on_clear(self):
        """清空并刷新"""
        clear_history()
        self._load_data()
        InfoBar.success(
            "已清空",
            "所有历史记录已被删除",
            InfoBarPosition.TOP,
            parent=self
        )

    def add_record(self, original_path: str, processed_path: str, is_retina: bool):
        """新增历史记录并刷新"""
        add_history_record(
            original_path, processed_path,
            operator_id=self.current_user_id,
            is_retina=is_retina
        )
        self._load_data()
