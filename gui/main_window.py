"""
闲鱼数据调研工具 - 主窗口 GUI v3.0
深色卡片设计、悬停动画、高对比度配色
"""

import os
import sys
import json
import random
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QSplitter, QFrame, QComboBox, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
    QGridLayout, QScrollArea, QSizePolicy, QStackedWidget, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCursor, QAction, QPalette, QLinearGradient, QBrush, QPainter, QEnterEvent

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter


# ========== 颜色常量 ==========

C = {
    "bg": "#0F172A",           # 深色背景
    "card": "#1E293B",         # 卡片背景
    "card_hover": "#273549",   # 卡片悬停
    "border": "#334155",       # 边框
    "border_hover": "#475569", # 边框悬停
    "text": "#E2E8F0",         # 主文字
    "text_dim": "#94A3B8",     # 次要文字
    "text_muted": "#64748B",   # 弱文字
    "primary": "#F97316",      # 橙色主色
    "primary_hover": "#FB923C",
    "primary_bg": "#F9731618",
    "success": "#10B981",
    "success_bg": "#10B98118",
    "warning": "#F59E0B",
    "warning_bg": "#F59E0B18",
    "danger": "#EF4444",
    "danger_bg": "#EF444418",
    "info": "#3B82F6",
    "info_bg": "#3B82F618",
    "purple": "#8B5CF6",
    "purple_bg": "#8B5CF618",
    "cyan": "#06B6D4",
    "cyan_bg": "#06B6D418",
    "white": "#FFFFFF",
    "input_bg": "#0F172A",
    "input_border": "#334155",
    "input_focus": "#F97316",
    "table_header": "#1E293B",
    "table_row_alt": "#1A2332",
    "log_bg": "#0B1120",
    "scrollbar": "#334155",
    "scrollbar_hover": "#475569",
}


# ========== 带动画的统计卡片 ==========

class StatCard(QFrame):
    """统计卡片 - 带 hover 动画"""
    def __init__(self, title, value, subtitle="", accent_color=C["primary"], icon=""):
        super().__init__()
        self.accent = accent_color
        self._hovered = False

        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(120)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(20, 16, 20, 16)

        icon_label = QLabel(f"{icon}")
        icon_label.setStyleSheet(f"font-size: 18px; border: none; background: transparent; color: {accent_color};")
        layout.addWidget(icon_label)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {C['white']}; font-size: 26px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.value_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {C['text_muted']}; font-size: 10px; border: none; background: transparent;")
            layout.addWidget(sub)

        self._update_style(False)

    def _update_style(self, hovered):
        if hovered:
            self.setStyleSheet(f"""
                QFrame#statCard {{
                    background: {C['card_hover']};
                    border: 1px solid {self.accent}40;
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#statCard {{
                    background: {C['card']};
                    border: 1px solid {C['border']};
                    border-radius: 14px;
                }}
            """)

    def enterEvent(self, event):
        self._update_style(True)

    def leaveEvent(self, event):
        self._update_style(False)


# ========== 带动画的可点击卡片 ==========

class ClickableCard(QFrame):
    """操作卡片 - hover 时边框发光"""
    clicked = pyqtSignal()

    def __init__(self, icon, title, desc, accent=C["primary"]):
        super().__init__()
        self.accent = accent
        self._hovered = False

        self.setObjectName("clickableCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(20, 18, 20, 18)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px; border: none; background: transparent;")
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C['text']}; border: none; background: transparent;")
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"font-size: 11px; color: {C['text_dim']}; border: none; background: transparent; line-height: 1.5;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self._update_style(False)

    def _update_style(self, hovered):
        if hovered:
            self.setStyleSheet(f"""
                QFrame#clickableCard {{
                    background: {C['card_hover']};
                    border: 2px solid {self.accent};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#clickableCard {{
                    background: {C['card']};
                    border: 1px solid {C['border']};
                    border-radius: 12px;
                }}
            """)

    def enterEvent(self, event):
        self._update_style(True)

    def leaveEvent(self, event):
        self._update_style(False)

    def mousePressEvent(self, event):
        self.clicked.emit()


# ========== 爬虫工作线程 ==========

class CrawlerWorker(QThread):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(object)
    login_status_signal = pyqtSignal(bool)

    def __init__(self, keyword, max_items, download_images):
        super().__init__()
        self.keyword = keyword
        self.max_items = max_items
        self.download_images = download_images
        self.db = Database()

    def run(self):
        from core.crawler import XianyuCrawler
        import asyncio

        self.crawler = XianyuCrawler(
            db=self.db,
            progress_callback=lambda c, t, m: self.progress_signal.emit(c, t, m),
            log_callback=lambda m, l="info": self.log_signal.emit(m, l),
        )

        async def _run():
            login_ok = await self.crawler.login()
            self.login_status_signal.emit(login_ok)
            if not login_ok:
                return None
            task_id = await self.crawler.search_and_collect(
                keyword=self.keyword,
                max_items=self.max_items,
                download_images=self.download_images,
            )
            return task_id

        try:
            task_id = asyncio.run(_run())
            self.finished_signal.emit(task_id)
        except Exception as e:
            self.log_signal.emit(f"运行异常: {e}", "error")
            self.finished_signal.emit(None)

    def stop(self):
        if hasattr(self, 'crawler') and self.crawler:
            self.crawler.stop()


# ========== 主窗口 ==========

class MainWindow(QMainWindow):
    """闲鱼数据调研工具 v3.0 - 主窗口"""

    def __init__(self):
        super().__init__()
        self.cfg = get_config()
        self.db = Database()
        self.analyzer = Analyzer(self.db)
        self.exporter = Exporter(self.db)
        self.worker = None
        self.current_task_id = None

        self._init_ui()
        self._load_task_history()
        self._refresh_dashboard()

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle("🐟 闲鱼数据调研工具 v3.0")
        self.setMinimumSize(1200, 800)
        self.resize(1300, 880)

        # 全局深色样式
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {C['bg']};
            }}
            QTabWidget::pane {{
                border: none;
                background: {C['bg']};
            }}
            QTabBar::tab {{
                background: {C['card']};
                color: {C['text_dim']};
                padding: 10px 22px;
                font-size: 13px;
                border: 1px solid {C['border']};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {C['bg']};
                color: {C['primary']};
                font-weight: bold;
                border-bottom: 2px solid {C['primary']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {C['card_hover']};
                color: {C['text']};
            }}
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
                border: 2px solid {C['input_border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                background: {C['input_bg']};
                color: {C['text']};
                selection-background-color: {C['primary']};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {{
                border-color: {C['primary']};
            }}
            QLineEdit::placeholder {{
                color: {C['text_muted']};
            }}
            QComboBox {{
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                selection-background-color: {C['primary']}30;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
                color: {C['text']};
                background: {C['card']};
                border: 1px solid {C['border']};
            }}
            QPushButton:hover {{
                background: {C['card_hover']};
                border-color: {C['border_hover']};
            }}
            QTableWidget {{
                gridline-color: {C['border']};
                font-size: 12px;
                border: 1px solid {C['border']};
                border-radius: 8px;
                background: {C['card']};
                color: {C['text']};
                alternate-background-color: {C['table_row_alt']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {C['border']};
            }}
            QTableWidget::item:selected {{
                background: {C['primary']}30;
                color: {C['white']};
            }}
            QHeaderView::section {{
                background-color: {C['table_header']};
                border: none;
                border-bottom: 2px solid {C['border']};
                padding: 10px 8px;
                font-weight: bold;
                color: {C['text_dim']};
            }}
            QProgressBar {{
                border: none;
                border-radius: 10px;
                background-color: {C['border']};
                height: 6px;
                text-align: center;
                font-size: 11px;
                color: {C['text']};
            }}
            QProgressBar::chunk {{
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C['primary']}, stop:1 {C['primary_hover']});
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {C['bg']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['scrollbar']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['scrollbar_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QGroupBox {{
                font-weight: bold;
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 12px;
                margin-top: 14px;
                padding: 24px 16px 16px 16px;
                background: {C['card']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: {C['primary']};
            }}
            QMenuBar {{
                background: {C['card']};
                color: {C['text_dim']};
                border-bottom: 1px solid {C['border']};
                padding: 4px;
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background: {C['card_hover']};
                color: {C['text']};
            }}
            QMenu {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 30px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {C['card_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {C['border']};
                margin: 4px 10px;
            }}
            QCheckBox {{
                color: {C['text']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {C['border']};
                border-radius: 4px;
                background: {C['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['primary']};
                border-color: {C['primary']};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                border: none;
                background: {C['card_hover']};
                border-top-right-radius: 6px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                border: none;
                background: {C['card_hover']};
                border-bottom-right-radius: 6px;
            }}
            QLabel {{
                color: {C['text']};
            }}
        """)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===== 顶部导航栏 =====
        self._create_navbar(main_layout)

        # ===== 标签页 =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        self.dashboard_tab = self._create_dashboard()
        self.tab_widget.addTab(self.dashboard_tab, "🏠 仪表盘")

        self.data_tab = self._create_data_tab()
        self.tab_widget.addTab(self.data_tab, "📊 数据预览")

        self.analysis_tab = self._create_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "📈 文案分析")

        self.log_tab = self._create_log_tab()
        self.tab_widget.addTab(self.log_tab, "📋 运行日志")

        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ 设置")

        main_layout.addWidget(self.tab_widget)

        # ===== 底部状态栏 =====
        self._create_statusbar()
        self._init_menu()

    def _create_navbar(self, parent_layout):
        """顶部导航栏"""
        navbar = QFrame()
        navbar.setFixedHeight(68)
        navbar.setStyleSheet(f"background: {C['card']}; border-bottom: 1px solid {C['border']};")

        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("🐟 闲鱼数据调研工具")
        logo.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {C['white']}; border: none; background: transparent;")
        nav_layout.addWidget(logo)

        version = QLabel("v3.0")
        version.setStyleSheet(f"font-size: 11px; color: {C['text_muted']}; background: {C['primary']}20; border-radius: 4px; padding: 2px 8px; margin-left: 8px;")
        nav_layout.addWidget(version)

        nav_layout.addStretch()

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入商品关键词搜索...")
        self.nav_keyword.setFixedWidth(260)
        self.nav_keyword.setFixedHeight(40)
        self.nav_keyword.returnPressed.connect(self._on_start)
        nav_layout.addWidget(self.nav_keyword)

        self.nav_count = QSpinBox()
        self.nav_count.setRange(5, 100)
        self.nav_count.setValue(30)
        self.nav_count.setSuffix(" 条")
        self.nav_count.setFixedWidth(85)
        self.nav_count.setFixedHeight(40)
        nav_layout.addWidget(self.nav_count)

        self.nav_start_btn = QPushButton("🚀 开始采集")
        self.nav_start_btn.setFixedHeight(40)
        self.nav_start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['primary']};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 8px 24px;
            }}
            QPushButton:hover {{
                background: {C['primary_hover']};
            }}
            QPushButton:disabled {{
                background: {C['border']};
                color: {C['text_muted']};
            }}
        """)
        self.nav_start_btn.clicked.connect(self._on_start)
        nav_layout.addWidget(self.nav_start_btn)

        parent_layout.addWidget(navbar)

    def _create_dashboard(self):
        """仪表盘首页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['bg']}; border: none; }}")

        widget = QWidget()
        widget.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 24, 28, 24)

        # 欢迎横幅
        banner = QFrame()
        banner.setFixedHeight(100)
        banner.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C['primary']}DD, stop:0.5 {C['primary']}CC, stop:1 {C['warning']}BB);
                border-radius: 16px;
            }}
        """)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(28, 16, 28, 16)

        banner_text = QVBoxLayout()
        title = QLabel("👋 欢迎使用闲鱼数据调研工具")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; border: none; background: transparent;")
        banner_text.addWidget(title)

        tips = QLabel("💡 输入关键词 → 自动采集 → 导出分析 → 掌握竞品文案套路")
        tips.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px; border: none; background: transparent; margin-top: 4px;")
        banner_text.addWidget(tips)
        banner_layout.addLayout(banner_text)
        banner_layout.addStretch()
        layout.addWidget(banner)

        # 统计卡片
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)

        self.card_total = StatCard("已采集商品", "0", "所有任务合计", C["primary"], "📦")
        stats_row.addWidget(self.card_total)
        self.card_tasks = StatCard("采集任务数", "0", "历史任务总数", C["info"], "📋")
        stats_row.addWidget(self.card_tasks)
        self.card_avg_price = StatCard("平均价格", "¥0", "最近一次采集", C["success"], "💰")
        stats_row.addWidget(self.card_avg_price)
        self.card_hot_word = StatCard("热门关键词", "-", "出现频率最高", C["purple"], "🔥")
        stats_row.addWidget(self.card_hot_word)

        layout.addLayout(stats_row)

        # 快捷操作
        section_title = QLabel("⚡ 快捷操作")
        section_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {C['text']}; background: transparent;")
        layout.addWidget(section_title)

        ops_grid = QGridLayout()
        ops_grid.setSpacing(12)

        ops = [
            ("📥", "导出Excel", "将采集数据导出为\nExcel电子表格", C["primary"], self._on_export_excel),
            ("📊", "文案分析", "生成标题/描述\n高频词分析报告", C["purple"], self._on_analyze),
            ("📂", "数据目录", "打开数据存储\n文件夹", C["info"], lambda: os.startfile(self.cfg["paths"]["data_dir"])),
            ("🖼", "图片目录", "打开已下载\n商品图片", C["success"], lambda: os.startfile(self.cfg["paths"]["image_dir"])),
            ("⚙️", "防封设置", "调整采集间隔\n和安全策略", C["warning"], self._on_config_dialog),
            ("📖", "使用帮助", "查看完整使用\n说明文档", C["cyan"], self._on_about),
        ]

        for idx, (icon, title, desc, color, handler) in enumerate(ops):
            card = ClickableCard(icon, title, desc, color)
            card.clicked.connect(handler)
            row, col = divmod(idx, 3)
            ops_grid.addWidget(card, row, col)

        layout.addLayout(ops_grid)

        # 最近任务
        recent_label = QLabel("📌 最近采集任务")
        recent_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {C['text']}; background: transparent;")
        layout.addWidget(recent_label)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["任务ID", "关键词", "商品数", "状态", "采集时间"])
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.recent_table.setMaximumHeight(200)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        layout.addWidget(self.recent_table)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_data_tab(self):
        """数据预览"""
        widget = QWidget()
        widget.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("📋 任务:"))
        self.data_task_combo = QComboBox()
        self.data_task_combo.setMinimumWidth(340)
        self.data_task_combo.currentIndexChanged.connect(self._on_task_selected)
        toolbar.addWidget(self.data_task_combo)
        toolbar.addStretch()

        btns = [
            ("📥 导出 Excel", C["primary"], self._on_export_excel),
            ("📄 导出 CSV", C["info"], self._on_export_csv),
            ("📊 分析报告", C["purple"], self._on_analyze),
            ("🔄 刷新", C["text_dim"], self._refresh_data_view),
        ]
        for text, color, handler in btns:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C['card']}; border: 1px solid {C['border']}; }}
                QPushButton:hover {{ border-color: {color}; color: {color}; }}
            """)
            btn.clicked.connect(handler)
            toolbar.addWidget(btn)

        layout.addLayout(toolbar)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(9)
        self.data_table.setHorizontalHeaderLabels(["#", "标题", "价格", "原价", "所在地", "卖家", "浏览", "想要", "采集时间"])
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.data_table)

        return widget

    def _create_analysis_tab(self):
        """文案分析"""
        widget = QWidget()
        widget.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        toolbar = QHBoxLayout()
        toolbar.addStretch()

        analyze_btn = QPushButton("🔍 生成分析报告")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['purple']};
                color: white;
                font-weight: bold;
                padding: 12px 30px;
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{ background: #7C3AED; }}
        """)
        analyze_btn.clicked.connect(self._on_analyze)
        toolbar.addWidget(analyze_btn)

        save_btn = QPushButton("💾 保存报告")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['card']};
                border: 1px solid {C['border']};
                font-weight: bold;
                padding: 12px 30px;
                font-size: 14px;
            }}
            QPushButton:hover {{ border-color: {C['purple']}; color: {C['purple']}; }}
        """)
        save_btn.clicked.connect(self._save_report)
        toolbar.addWidget(save_btn)

        layout.addLayout(toolbar)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Microsoft YaHei", 11))
        self.analysis_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['card']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 20px;
                line-height: 1.7;
            }}
        """)
        self.analysis_text.setPlaceholderText("👈 点击「生成分析报告」查看文案分析...")
        layout.addWidget(self.analysis_text)

        return widget

    def _create_log_tab(self):
        """运行日志"""
        widget = QWidget()
        widget.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 16, 20, 16)

        log_toolbar = QHBoxLayout()
        self.log_status_label = QLabel("🟢 就绪")
        self.log_status_label.setStyleSheet(f"font-size: 12px; color: {C['success']}; font-weight: bold; background: transparent;")
        log_toolbar.addWidget(self.log_status_label)
        log_toolbar.addStretch()

        clear_btn = QPushButton("🗑 清空日志")
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['card']}; border: 1px solid {C['border']}; }}
            QPushButton:hover {{ border-color: {C['danger']}; color: {C['danger']}; }}
        """)
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        log_toolbar.addWidget(clear_btn)
        layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['log_bg']};
                color: #D4D4D4;
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        self.log_text.setPlaceholderText("运行日志将显示在这里...")
        layout.addWidget(self.log_text)

        return widget

    def _create_settings_tab(self):
        """设置"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C['bg']}; border: none; }}")

        widget = QWidget()
        widget.setStyleSheet(f"background: {C['bg']};")
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 24, 28, 24)

        # 防封策略
        anti_group = QGroupBox("🛡 防封策略设置")
        anti_layout = QFormLayout(anti_group)
        anti_layout.setSpacing(14)

        self.set_min_delay = QDoubleSpinBox()
        self.set_min_delay.setRange(1.0, 30.0)
        self.set_min_delay.setValue(self.cfg["anti_ban"]["min_delay"])
        self.set_min_delay.setSuffix(" 秒")
        anti_layout.addRow("最小采集间隔:", self.set_min_delay)

        self.set_max_delay = QDoubleSpinBox()
        self.set_max_delay.setRange(1.0, 60.0)
        self.set_max_delay.setValue(self.cfg["anti_ban"]["max_delay"])
        self.set_max_delay.setSuffix(" 秒")
        anti_layout.addRow("最大采集间隔:", self.set_max_delay)

        self.set_page_min = QDoubleSpinBox()
        self.set_page_min.setRange(2.0, 30.0)
        self.set_page_min.setValue(self.cfg["anti_ban"]["page_delay_min"])
        self.set_page_min.setSuffix(" 秒")
        anti_layout.addRow("翻页最小间隔:", self.set_page_min)

        self.set_page_max = QDoubleSpinBox()
        self.set_page_max.setRange(2.0, 60.0)
        self.set_page_max.setValue(self.cfg["anti_ban"]["page_delay_max"])
        self.set_page_max.setSuffix(" 秒")
        anti_layout.addRow("翻页最大间隔:", self.set_page_max)

        self.set_max_items = QSpinBox()
        self.set_max_items.setRange(10, 200)
        self.set_max_items.setValue(self.cfg["anti_ban"]["max_items_per_session"])
        anti_layout.addRow("单次最大采集:", self.set_max_items)

        layout.addWidget(anti_group)

        # 采集设置
        collect_group = QGroupBox("📷 采集设置")
        collect_layout = QFormLayout(collect_group)
        collect_layout.setSpacing(14)

        self.set_download_img = QCheckBox("自动下载商品图片")
        self.set_download_img.setChecked(self.cfg["collection"]["download_images"])
        collect_layout.addRow(self.set_download_img)

        self.set_img_quality = QSpinBox()
        self.set_img_quality.setRange(10, 100)
        self.set_img_quality.setValue(self.cfg["collection"]["image_quality"])
        self.set_img_quality.setSuffix(" %")
        collect_layout.addRow("图片保存质量:", self.set_img_quality)

        layout.addWidget(collect_group)

        save_btn = QPushButton("💾 保存设置")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['primary']};
                color: white;
                font-weight: bold;
                font-size: 15px;
                padding: 14px;
                border: none;
            }}
            QPushButton:hover {{ background: {C['primary_hover']}; }}
        """)
        save_btn.clicked.connect(self._save_all_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_statusbar(self):
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {C['card']};
                border-top: 1px solid {C['border']};
                padding: 4px 16px;
                font-size: 11px;
                color: {C['text_dim']};
            }}
        """)
        self.status_bar.showMessage("🟢 就绪")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")
        a1 = QAction("打开数据目录", self)
        a1.triggered.connect(lambda: os.startfile(self.cfg["paths"]["data_dir"]))
        file_menu.addAction(a1)
        a2 = QAction("打开导出目录", self)
        a2.triggered.connect(lambda: os.startfile(self.cfg["paths"]["export_dir"]))
        file_menu.addAction(a2)
        file_menu.addSeparator()
        a3 = QAction("退出(&Q)", self)
        a3.setShortcut("Ctrl+Q")
        a3.triggered.connect(self.close)
        file_menu.addAction(a3)

        help_menu = menubar.addMenu("帮助(&H)")
        a4 = QAction("使用说明", self)
        a4.triggered.connect(self._on_about)
        help_menu.addAction(a4)
        a5 = QAction("GitHub 项目", self)
        a5.triggered.connect(lambda: os.startfile("https://github.com/Roue-AFK/xianyu-data-tool"))
        help_menu.addAction(a5)

    # ========== 仪表盘刷新 ==========

    def _refresh_dashboard(self):
        total_items = self.db.get_item_count()
        self.card_total.value_label.setText(str(total_items))

        tasks = self.db.get_tasks(limit=100)
        self.card_tasks.value_label.setText(str(len(tasks)))

        if tasks:
            latest_task = tasks[0]
            stats = self.db.get_price_stats(latest_task["id"])
            avg = stats.get("avg_price", 0) or 0
            self.card_avg_price.value_label.setText(f"¥{avg:.0f}")
        else:
            self.card_avg_price.value_label.setText("¥0")

        if tasks:
            keyword_counts = {}
            for t in tasks:
                kw = t.get("keyword", "")
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            if keyword_counts:
                top_kw = max(keyword_counts, key=keyword_counts.get)
                self.card_hot_word.value_label.setText(top_kw)
            else:
                self.card_hot_word.value_label.setText("-")
        else:
            self.card_hot_word.value_label.setText("-")

        self.recent_table.setRowCount(min(len(tasks), 10))
        for i, task in enumerate(tasks[:10]):
            self.recent_table.setItem(i, 0, QTableWidgetItem(f"#{task['id']}"))
            self.recent_table.setItem(i, 1, QTableWidgetItem(task.get("keyword", "")))
            self.recent_table.setItem(i, 2, QTableWidgetItem(str(task.get("item_count", 0))))
            status = "✅ 完成" if task.get("status") == "finished" else "🔄 进行中"
            self.recent_table.setItem(i, 3, QTableWidgetItem(status))
            self.recent_table.setItem(i, 4, QTableWidgetItem(str(task.get("created_at", "")[:16])))

    # ========== 事件处理 ==========

    def _on_start(self):
        keyword = self.nav_keyword.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return

        max_items = self.nav_count.value()
        download_images = self.set_download_img.isChecked()

        reply = QMessageBox.question(
            self, "确认开始采集",
            f"<h3>即将开始采集</h3>"
            f"<p><b>关键词：</b>{keyword}<br>"
            f"<b>数量：</b>最多 {max_items} 条<br>"
            f"<b>下载图片：</b>{'是' if download_images else '否'}</p>"
            f"<p style='color:{C['danger']};'>⚠ 采集过程会自动打开浏览器窗口<br>"
            f"⚠ 如果未登录，请扫码登录闲鱼<br>"
            f"⚠ 采集过程中请勿手动操作浏览器</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.nav_start_btn.setEnabled(False)
        self.nav_start_btn.setText("⏳ 采集中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, max_items)
        self.progress_bar.setValue(0)
        self.log_status_label.setText("🟡 采集中...")
        self.log_status_label.setStyleSheet(f"font-size: 12px; color: {C['warning']}; font-weight: bold; background: transparent;")
        self.log_text.clear()
        self._log("=" * 60, "info")
        self._log(f"🚀 开始采集：{keyword}（目标 {max_items} 条）", "info")
        self._log("=" * 60, "info")

        self.tab_widget.setCurrentIndex(3)

        self.worker = CrawlerWorker(keyword, max_items, download_images)
        self.worker.log_signal.connect(self._on_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.login_status_signal.connect(self._on_login_status)
        self.worker.start()

    def _on_log(self, message, level="info"):
        self._log(message, level)

    def _on_progress(self, current, total, message):
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"🔄 {message}")

    def _on_login_status(self, success):
        if success:
            self._log("✅ 登录状态：已登录", "success")
        else:
            self._log("⏳ 等待扫码登录...", "warning")

    def _on_finished(self, task_id):
        self.nav_start_btn.setEnabled(True)
        self.nav_start_btn.setText("🚀 开始采集")
        self.progress_bar.setVisible(False)
        self.log_status_label.setText("🟢 就绪")
        self.log_status_label.setStyleSheet(f"font-size: 12px; color: {C['success']}; font-weight: bold; background: transparent;")
        self.worker = None

        if task_id:
            self.current_task_id = task_id
            self.status_bar.showMessage(f"✅ 采集完成 - 任务 #{task_id}")
            self._log("=" * 60, "success")
            self._log(f"🎉 采集任务 #{task_id} 完成！", "success")
            self._log("=" * 60, "success")
            self._load_task_history()
            self._refresh_data_view()
            self._refresh_dashboard()

            reply = QMessageBox.question(
                self, "采集完成",
                f"<h3>🎉 采集完成！</h3><p>是否立即导出 Excel？</p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_export_excel()
        else:
            self.status_bar.showMessage("⚠ 采集中断或失败")

    def _log(self, message, level="info"):
        colors = {
            "info": "#D4D4D4",
            "success": "#4EC9B0",
            "warning": "#CE9178",
            "error": "#F44747",
            "debug": "#808080",
        }
        color = QColor(colors.get(level, "#D4D4D4"))
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.setTextColor(color)
        self.log_text.insertPlainText(message + "\n")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    # ========== 数据操作 ==========

    def _load_task_history(self):
        self.data_task_combo.blockSignals(True)
        self.data_task_combo.clear()
        self.data_task_combo.addItem("📋 全部任务", None)

        tasks = self.db.get_tasks(limit=50)
        for task in tasks:
            label = f"#{task['id']} | {task['keyword']} | {task.get('item_count', 0)}条 | {task['created_at'][:16]}"
            self.data_task_combo.addItem(label, task["id"])

        self.data_task_combo.blockSignals(False)
        self._refresh_dashboard()

    def _on_task_selected(self, index):
        task_id = self.data_task_combo.currentData()
        self.current_task_id = task_id
        self._refresh_data_view()

    def _refresh_data_view(self):
        task_id = self.data_task_combo.currentData()
        items = self.db.get_items(task_id=task_id, limit=200)

        self.data_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.data_table.setItem(i, 1, QTableWidgetItem(item.get("title", "")))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"¥{item.get('price', 0):.2f}"))
            self.data_table.setItem(i, 3, QTableWidgetItem(f"¥{item.get('original_price', 0):.2f}"))
            self.data_table.setItem(i, 4, QTableWidgetItem(item.get("location", "")))
            self.data_table.setItem(i, 5, QTableWidgetItem(item.get("seller_name", "")))
            self.data_table.setItem(i, 6, QTableWidgetItem(str(item.get("views", 0))))
            self.data_table.setItem(i, 7, QTableWidgetItem(str(item.get("wants", 0))))
            self.data_table.setItem(i, 8, QTableWidgetItem(str(item.get("collected_at", "")[:16])))

        self.status_bar.showMessage(f"📊 共 {len(items)} 条数据")

    def _on_export_excel(self):
        task_id = self.data_task_combo.currentData()
        keyword = self.nav_keyword.text().strip() or "全部"

        try:
            path = self.exporter.export_to_excel(task_id=task_id, keyword=keyword)
            self._log(f"✅ Excel 导出成功: {path}", "success")
            QMessageBox.information(self, "导出成功",
                                    f"<h3>✅ 导出成功</h3>"
                                    f"<p>文件位置：<br><code>{path}</code></p>"
                                    f"<p>包含：商品数据 | 统计分析 | 文案汇总</p>")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"错误：{e}")

    def _on_export_csv(self):
        task_id = self.data_task_combo.currentData()
        keyword = self.nav_keyword.text().strip() or "全部"

        try:
            path = self.exporter.export_to_csv(task_id=task_id, keyword=keyword)
            self._log(f"✅ CSV 导出成功: {path}", "success")
            QMessageBox.information(self, "导出成功", f"<h3>✅ 导出成功</h3><p>{path}</p>")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"错误：{e}")

    def _on_analyze(self):
        task_id = self.data_task_combo.currentData()
        keyword = self.nav_keyword.text().strip() or "全部"

        try:
            report_md = self.analyzer.generate_markdown_report(task_id, keyword)
            self.analysis_text.setMarkdown(report_md)
            self.tab_widget.setCurrentIndex(2)
            self._log("✅ 分析报告生成完成", "success")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._last_report_path = os.path.join(self.cfg["paths"]["export_dir"], f"分析报告_{timestamp}.md")
            with open(self._last_report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            self._log(f"💾 报告已保存: {self._last_report_path}", "info")
        except Exception as e:
            QMessageBox.critical(self, "分析失败", f"错误：{e}")

    def _save_report(self):
        if hasattr(self, '_last_report_path'):
            os.startfile(os.path.dirname(self._last_report_path))
        else:
            QMessageBox.information(self, "提示", "请先生成分析报告")

    def _save_all_settings(self):
        self.cfg["anti_ban"]["min_delay"] = self.set_min_delay.value()
        self.cfg["anti_ban"]["max_delay"] = self.set_max_delay.value()
        self.cfg["anti_ban"]["page_delay_min"] = self.set_page_min.value()
        self.cfg["anti_ban"]["page_delay_max"] = self.set_page_max.value()
        self.cfg["anti_ban"]["max_items_per_session"] = self.set_max_items.value()
        self.cfg["collection"]["download_images"] = self.set_download_img.isChecked()
        self.cfg["collection"]["image_quality"] = self.set_img_quality.value()

        save_user_config(self.cfg)
        QMessageBox.information(self, "设置已保存", "<h3>✅ 设置已保存</h3><p>新设置将在下次采集时生效</p>")

    def _on_config_dialog(self):
        self.tab_widget.setCurrentIndex(4)

    def _on_about(self):
        QMessageBox.about(self, "使用说明",
                          f"""<h2 style='color:{C['primary']};'>🐟 闲鱼数据调研工具 v3.0</h2>

<h3>📖 使用步骤</h3>
<ol>
<li>在顶部搜索框输入关键词（如：蓝牙耳机）</li>
<li>设置采集数量（建议30-50条）</li>
<li>点击「开始采集」</li>
<li>在弹出的浏览器中扫码登录闲鱼（仅首次需要）</li>
<li>等待自动采集完成</li>
<li>在「数据预览」查看结果，导出 Excel</li>
<li>在「文案分析」生成竞品文案报告</li>
</ol>

<h3>🛡 防封保护</h3>
<ul>
<li>模拟真人浏览节奏，每条商品间隔3-8秒</li>
<li>随机滚动、随机鼠标移动</li>
<li>单次最多100条，不进行大规模批量爬取</li>
<li>Cookie 本地保存，不反复登录</li>
</ul>

<h3>⚠ 注意事项</h3>
<ul>
<li>仅供个人学习研究使用</li>
<li>请勿用于商业用途或大规模数据采集</li>
<li>采集过程中请勿手动操作浏览器</li>
</ul>
                          """)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "采集任务正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait(3000)
                self.db.close()
                event.accept()
            else:
                event.ignore()
        else:
            self.db.close()
            event.accept()
