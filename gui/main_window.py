"""
闲鱼数据调研工具 - 主窗口 GUI v2.0
全新设计：仪表盘首页、卡片式布局、现代化配色
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
    QGridLayout, QScrollArea, QSizePolicy, QStackedWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCursor, QAction, QPalette, QLinearGradient, QBrush, QPainter

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter


# ========== 自定义卡片组件 ==========

class StatCard(QFrame):
    """统计卡片"""
    def __init__(self, title, value, subtitle="", color="#FF6B35", icon=""):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}15, stop:1 {color}08);
                border: 1px solid {color}30;
                border-radius: 12px;
                padding: 16px;
                min-height: 90px;
            }}
            QFrame#statCard:hover {{
                border-color: {color}60;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}25, stop:1 {color}12);
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        title_label = QLabel(icon + " " + title)
        title_label.setStyleSheet(f"color: #888; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(title_label)

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(value_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet("color: #AAA; font-size: 10px; border: none; background: transparent;")
            layout.addWidget(sub)


class ClickableCard(QFrame):
    """可点击的操作卡片"""
    clicked = pyqtSignal()

    def __init__(self, icon, title, desc, color="#FF6B35"):
        super().__init__()
        self.setObjectName("clickableCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#clickableCard {{
                background: white;
                border: 1px solid #E8E8E8;
                border-radius: 10px;
                padding: 20px;
                min-height: 100px;
            }}
            QFrame#clickableCard:hover {{
                border-color: {color};
                background: {color}08;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 28px; border: none; background: transparent;")
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: #333; border: none; background: transparent;")
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 11px; color: #999; border: none; background: transparent;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

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
    """闲鱼数据调研工具 v2.0 - 主窗口"""

    # 品牌色
    COLORS = {
        "primary": "#FF6B35",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "info": "#3B82F6",
        "purple": "#8B5CF6",
        "dark": "#1F2937",
        "bg": "#F8FAFC",
        "card_bg": "#FFFFFF",
    }

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
        self.setWindowTitle("🐟 闲鱼数据调研工具 v2.0")
        self.setMinimumSize(1200, 800)
        self.resize(1280, 860)

        # 应用全局样式
        self.setStyleSheet(self._global_stylesheet())

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ===== 顶部导航栏 =====
        self._create_navbar(main_layout)

        # ===== 主内容区（标签页） =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Tab 0: 仪表盘首页
        self.dashboard_tab = self._create_dashboard()
        self.tab_widget.addTab(self.dashboard_tab, "🏠 仪表盘")

        # Tab 1: 数据预览
        self.data_tab = self._create_data_tab()
        self.tab_widget.addTab(self.data_tab, "📊 数据预览")

        # Tab 2: 文案分析
        self.analysis_tab = self._create_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "📈 文案分析")

        # Tab 3: 运行日志
        self.log_tab = self._create_log_tab()
        self.tab_widget.addTab(self.log_tab, "📋 运行日志")

        # Tab 4: 设置
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ 设置")

        main_layout.addWidget(self.tab_widget)

        # ===== 底部状态栏 =====
        self._create_statusbar()

        # 菜单栏
        self._init_menu()

    def _global_stylesheet(self):
        return """
            QMainWindow {
                background-color: #F8FAFC;
            }
            QTabWidget::pane {
                border: none;
                background: #F8FAFC;
            }
            QTabBar::tab {
                background: transparent;
                padding: 12px 24px;
                font-size: 13px;
                color: #666;
                border: none;
                border-bottom: 3px solid transparent;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                color: #FF6B35;
                border-bottom: 3px solid #FF6B35;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                color: #333;
                background: #F0F0F0;
            }
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border-color: #FF6B35;
                background: #FFF8F5;
            }
            QPushButton {
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
            }
            QTableWidget {
                gridline-color: #F0F0F0;
                font-size: 12px;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #F9FAFB;
                border: none;
                border-bottom: 2px solid #E5E7EB;
                padding: 10px 8px;
                font-weight: bold;
                color: #374151;
            }
            QProgressBar {
                border: none;
                border-radius: 10px;
                background-color: #E5E7EB;
                height: 20px;
                text-align: center;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:1 #FF8C5A);
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 24px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: #374151;
            }
        """

    def _create_navbar(self, parent_layout):
        """创建顶部导航栏"""
        navbar = QFrame()
        navbar.setFixedHeight(64)
        navbar.setStyleSheet("""
            QFrame {
                background: white;
                border-bottom: 1px solid #E5E7EB;
            }
        """)

        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)

        # Logo
        logo = QLabel("🐟 闲鱼数据调研工具")
        logo.setStyleSheet("font-size: 18px; font-weight: bold; color: #1F2937; border: none;")
        nav_layout.addWidget(logo)

        nav_layout.addStretch()

        # 快速搜索入口（在导航栏）
        search_frame = QFrame()
        search_frame.setStyleSheet("background: transparent; border: none;")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入商品关键词...")
        self.nav_keyword.setFixedWidth(240)
        self.nav_keyword.setFixedHeight(36)
        self.nav_keyword.returnPressed.connect(self._on_start)
        search_layout.addWidget(self.nav_keyword)

        self.nav_count = QSpinBox()
        self.nav_count.setRange(5, 100)
        self.nav_count.setValue(30)
        self.nav_count.setSuffix(" 条")
        self.nav_count.setFixedWidth(80)
        self.nav_count.setFixedHeight(36)
        search_layout.addWidget(self.nav_count)

        self.nav_start_btn = QPushButton("🚀 开始采集")
        self.nav_start_btn.setFixedHeight(36)
        self.nav_start_btn.setStyleSheet("""
            QPushButton {
                background: #FF6B35;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }
            QPushButton:hover { background: #FF8C5A; }
            QPushButton:disabled { background: #CCC; }
        """)
        self.nav_start_btn.clicked.connect(self._on_start)
        search_layout.addWidget(self.nav_start_btn)

        nav_layout.addWidget(search_frame)

        parent_layout.addWidget(navbar)

    def _create_dashboard(self):
        """创建仪表盘首页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # ===== 欢迎区域 =====
        welcome_frame = QFrame()
        welcome_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B35, stop:0.5 #FF8C5A, stop:1 #F59E0B);
                border-radius: 16px;
                padding: 24px;
            }
        """)
        welcome_layout = QHBoxLayout(welcome_frame)
        welcome_text = QVBoxLayout()

        title = QLabel("👋 欢迎使用闲鱼数据调研工具")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; border: none;")
        welcome_text.addWidget(title)

        tips = [
            "💡 输入关键词 → 自动采集闲鱼商品数据",
            "📊 支持数据预览、Excel导出、文案分析",
            "🛡 内置防封策略，模拟真人浏览节奏",
            "⚡ 零基础友好，一键操作即可完成",
        ]
        tip_label = QLabel("\n".join(tips))
        tip_label.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 12px; border: none; line-height: 1.8;")
        welcome_text.addWidget(tip_label)
        welcome_layout.addLayout(welcome_text)
        welcome_layout.addStretch()

        layout.addWidget(welcome_frame)

        # ===== 统计卡片行 =====
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.card_total = StatCard("总采集商品", "0", "所有任务合计", self.COLORS["primary"], "📦")
        stats_row.addWidget(self.card_total)

        self.card_tasks = StatCard("采集任务", "0", "历史任务数", self.COLORS["info"], "📋")
        stats_row.addWidget(self.card_tasks)

        self.card_avg_price = StatCard("平均价格", "¥0", "最近一次采集", self.COLORS["success"], "💰")
        stats_row.addWidget(self.card_avg_price)

        self.card_hot_word = StatCard("热门关键词", "-", "出现最多", self.COLORS["purple"], "🔥")
        stats_row.addWidget(self.card_hot_word)

        layout.addLayout(stats_row)

        # ===== 快捷操作 =====
        ops_label = QLabel("⚡ 快捷操作")
        ops_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1F2937;")
        layout.addWidget(ops_label)

        ops_grid = QGridLayout()
        ops_grid.setSpacing(12)

        ops = [
            ("📥", "导出Excel", "将采集数据导出为\nExcel电子表格", self.COLORS["primary"], self._on_export_excel),
            ("📊", "文案分析", "生成标题/描述\n高频词分析报告", self.COLORS["purple"], self._on_analyze),
            ("📂", "数据目录", "打开数据存储\n文件夹", self.COLORS["info"], lambda: os.startfile(self.cfg["paths"]["data_dir"])),
            ("🖼", "图片目录", "打开已下载\n商品图片", self.COLORS["success"], lambda: os.startfile(self.cfg["paths"]["image_dir"])),
            ("⚙️", "防封设置", "调整采集间隔\n和安全策略", self.COLORS["warning"], self._on_config_dialog),
            ("📖", "使用帮助", "查看完整使用\n说明文档", self.COLORS["dark"], self._on_about),
        ]

        for idx, (icon, title, desc, color, handler) in enumerate(ops):
            card = ClickableCard(icon, title, desc, color)
            card.clicked.connect(handler)
            row, col = divmod(idx, 3)
            ops_grid.addWidget(card, row, col)

        layout.addLayout(ops_grid)

        # ===== 最近任务 =====
        recent_label = QLabel("📌 最近采集任务")
        recent_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1F2937;")
        layout.addWidget(recent_label)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["任务ID", "关键词", "商品数", "状态", "采集时间"])
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.recent_table.setMaximumHeight(200)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.recent_table)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_data_tab(self):
        """数据预览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.data_task_combo = QComboBox()
        self.data_task_combo.setMinimumWidth(320)
        self.data_task_combo.currentIndexChanged.connect(self._on_task_selected)
        toolbar.addWidget(QLabel("📋 任务:"))
        toolbar.addWidget(self.data_task_combo)

        toolbar.addStretch()

        for text, icon, color, handler in [
            ("导出 Excel", "📥", self.COLORS["primary"], self._on_export_excel),
            ("导出 CSV", "📄", self.COLORS["info"], self._on_export_csv),
            ("生成报告", "📊", self.COLORS["purple"], self._on_analyze),
            ("刷新", "🔄", self.COLORS["dark"], self._refresh_data_view),
        ]:
            btn = QPushButton(f"{icon} {text}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    border: 1px solid #E5E7EB;
                    color: #374151;
                }}
                QPushButton:hover {{
                    border-color: {color};
                    color: {color};
                }}
            """)
            btn.clicked.connect(handler)
            toolbar.addWidget(btn)

        layout.addLayout(toolbar)

        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(9)
        self.data_table.setHorizontalHeaderLabels([
            "#", "标题", "价格", "原价", "所在地", "卖家", "浏览", "想要", "采集时间"
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.data_table)

        return widget

    def _create_analysis_tab(self):
        """文案分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addStretch()

        analyze_btn = QPushButton("🔍 生成分析报告")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.COLORS["purple"]};
                color: white;
                font-weight: bold;
                padding: 10px 28px;
                border: none;
            }}
            QPushButton:hover {{ background: #7C3AED; }}
        """)
        analyze_btn.clicked.connect(self._on_analyze)
        toolbar.addWidget(analyze_btn)

        save_report_btn = QPushButton("💾 保存报告")
        save_report_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 1px solid #E5E7EB;
                color: #374151;
                font-weight: bold;
                padding: 10px 28px;
            }}
            QPushButton:hover {{ border-color: {self.COLORS["purple"]}; color: {self.COLORS["purple"]}; }}
        """)
        save_report_btn.clicked.connect(self._save_report)
        toolbar.addWidget(save_report_btn)

        layout.addLayout(toolbar)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Microsoft YaHei", 11))
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 10px;
                padding: 16px;
                line-height: 1.6;
            }
        """)
        self.analysis_text.setPlaceholderText("👈 点击「生成分析报告」查看文案分析...")
        layout.addWidget(self.analysis_text)

        return widget

    def _create_log_tab(self):
        """运行日志标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 日志工具栏
        log_toolbar = QHBoxLayout()

        self.log_status_label = QLabel("🟢 就绪")
        self.log_status_label.setStyleSheet("font-size: 12px; color: #10B981; font-weight: bold;")
        log_toolbar.addWidget(self.log_status_label)

        log_toolbar.addStretch()

        clear_btn = QPushButton("🗑 清空日志")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E7EB;
                color: #666;
            }
            QPushButton:hover { border-color: #EF4444; color: #EF4444; }
        """)
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        log_toolbar.addWidget(clear_btn)

        layout.addLayout(log_toolbar)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        self.log_text.setPlaceholderText("运行日志将显示在这里...")
        layout.addWidget(self.log_text)

        return widget

    def _create_settings_tab(self):
        """设置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # 防封策略设置
        anti_group = QGroupBox("🛡 防封策略设置")
        anti_layout = QFormLayout(anti_group)
        anti_layout.setSpacing(12)

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
        collect_layout.setSpacing(12)

        self.set_download_img = QCheckBox("自动下载商品图片")
        self.set_download_img.setChecked(self.cfg["collection"]["download_images"])
        collect_layout.addRow(self.set_download_img)

        self.set_img_quality = QSpinBox()
        self.set_img_quality.setRange(10, 100)
        self.set_img_quality.setValue(self.cfg["collection"]["image_quality"])
        self.set_img_quality.setSuffix(" %")
        collect_layout.addRow("图片保存质量:", self.set_img_quality)

        layout.addWidget(collect_group)

        # 保存按钮
        save_btn = QPushButton("💾 保存设置")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.COLORS["primary"]};
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border: none;
            }}
            QPushButton:hover {{ background: #FF8C5A; }}
        """)
        save_btn.clicked.connect(self._save_all_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_statusbar(self):
        """底部状态栏"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: white;
                border-top: 1px solid #E5E7EB;
                padding: 4px 16px;
                font-size: 11px;
                color: #666;
            }
        """)
        self.status_bar.showMessage("🟢 就绪")

        # 进度条（放在状态栏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _init_menu(self):
        """菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background: white; border-bottom: 1px solid #E5E7EB; padding: 4px; }
            QMenuBar::item { padding: 6px 12px; border-radius: 4px; }
            QMenuBar::item:selected { background: #F0F0F0; }
        """)

        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("打开数据目录", lambda: os.startfile(self.cfg["paths"]["data_dir"]))
        file_menu.addAction("打开导出目录", lambda: os.startfile(self.cfg["paths"]["export_dir"]))
        file_menu.addSeparator()
        file_menu.addAction("退出(&Q)", self.close, "Ctrl+Q")

        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("使用说明", self._on_about)
        help_menu.addAction("GitHub 项目", lambda: os.startfile("https://github.com/Roue-AFK/xianyu-data-tool"))

    # ========== 仪表盘刷新 ==========

    def _refresh_dashboard(self):
        """刷新仪表盘统计数据"""
        # 总商品数
        total_items = self.db.get_item_count()
        self.card_total.findChildren(QLabel)[1].setText(str(total_items))

        # 任务数
        tasks = self.db.get_tasks(limit=100)
        self.card_tasks.findChildren(QLabel)[1].setText(str(len(tasks)))

        # 平均价格（最近一次任务）
        if tasks:
            latest_task = tasks[0]
            stats = self.db.get_price_stats(latest_task["id"])
            avg = stats.get("avg_price", 0) or 0
            self.card_avg_price.findChildren(QLabel)[1].setText(f"¥{avg:.0f}")
        else:
            self.card_avg_price.findChildren(QLabel)[1].setText("¥0")

        # 热门关键词
        if tasks:
            keyword_counts = {}
            for t in tasks:
                kw = t.get("keyword", "")
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            if keyword_counts:
                top_kw = max(keyword_counts, key=keyword_counts.get)
                self.card_hot_word.findChildren(QLabel)[1].setText(top_kw)
            else:
                self.card_hot_word.findChildren(QLabel)[1].setText("-")
        else:
            self.card_hot_word.findChildren(QLabel)[1].setText("-")

        # 最近任务表格
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
        """点击开始采集"""
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
            f"<p style='color:#EF4444;'>⚠ 采集过程会自动打开浏览器窗口<br>"
            f"⚠ 如果未登录，请扫码登录闲鱼<br>"
            f"⚠ 采集过程中请勿手动操作浏览器</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 更新 UI
        self.nav_start_btn.setEnabled(False)
        self.nav_start_btn.setText("⏳ 采集中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, max_items)
        self.progress_bar.setValue(0)
        self.log_status_label.setText("🟡 采集中...")
        self.log_status_label.setStyleSheet("font-size: 12px; color: #F59E0B; font-weight: bold;")
        self.log_text.clear()
        self._log("=" * 60, "info")
        self._log(f"🚀 开始采集：{keyword}（目标 {max_items} 条）", "info")
        self._log("=" * 60, "info")

        self.tab_widget.setCurrentIndex(3)  # 切换到日志页

        # 启动后台线程
        self.worker = CrawlerWorker(keyword, max_items, download_images)
        self.worker.log_signal.connect(self._on_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.login_status_signal.connect(self._on_login_status)
        self.worker.start()

    def _on_stop(self):
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止当前采集任务吗？已采集的数据会保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes and self.worker:
            self.worker.stop()
            self._log("⏹ 用户手动停止采集", "warning")

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
        self.log_status_label.setStyleSheet("font-size: 12px; color: #10B981; font-weight: bold;")
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
        """保存所有设置"""
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
        self.tab_widget.setCurrentIndex(4)  # 切换到设置页

    def _on_about(self):
        QMessageBox.about(self, "使用说明",
                          """<h2>🐟 闲鱼数据调研工具 v2.0</h2>

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
