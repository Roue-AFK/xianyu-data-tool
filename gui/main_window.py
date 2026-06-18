"""
闲鱼数据调研工具 - 主窗口 GUI v4.0
浅色白黄主题、柔和护眼、悬停动画
"""

import os
import sys
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QComboBox, QStatusBar, QFormLayout, QDoubleSpinBox,
    QGridLayout, QScrollArea, QFrame, QMenuBar, QMenu,
    QDialog, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter
from core.researcher import MarketResearcher


# ========== 配色方案：白黄柔和 ==========

class C:
    bg              = "#F5F3EE"   # 暖灰底色（护眼不刺眼）
    card            = "#FFFFFF"   # 纯白卡片
    card_hover      = "#FFFBEB"   # 悬停淡黄
    border          = "#E8E3D9"   # 浅边框
    border_hover    = "#F5C842"   # 悬停黄色边框
    text            = "#3D3929"   # 深棕文字（比纯黑柔和）
    text_dim        = "#8B8576"   # 次要文字
    text_muted      = "#B8B2A6"   # 弱文字
    primary         = "#F5A623"   # 暖黄主色
    primary_hover   = "#F7B84E"   # 悬停
    primary_bg      = "#FFF8E7"   # 主色浅背景
    success         = "#52C41A"   # 绿色
    success_bg      = "#F6FFED"
    warning         = "#FAAD14"   # 黄色
    warning_bg      = "#FFFBE6"
    danger          = "#FF4D4F"   # 红色
    info            = "#1890FF"   # 蓝色
    info_bg         = "#E6F7FF"
    purple          = "#722ED1"
    purple_bg       = "#F9F0FF"
    cyan            = "#13C2C2"
    white           = "#FFFFFF"
    input_bg        = "#FFFFFF"
    input_border    = "#E0DBD0"
    input_focus     = "#F5A623"
    table_header    = "#FAF8F5"
    table_row_alt   = "#FDFCF9"
    log_bg          = "#2D2A24"
    scrollbar       = "#D5D0C7"
    scrollbar_hover = "#B8B2A6"
    navbar_bg       = "#FFFFFF"
    stat_value      = "#3D3929"


# ========== 统计卡片 ==========

class StatCard(QFrame):
    def __init__(self, icon, title, value, accent=C.primary):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(20, 16, 20, 16)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 20px; border:none; background:transparent;")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        layout.addWidget(title_lbl)

        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color:{C.stat_value}; font-size:26px; font-weight:bold; border:none; background:transparent;")
        layout.addWidget(self.value_label)

        self._update(False)

    def _update(self, hovered):
        if hovered:
            self.setStyleSheet(f"""
                StatCard {{ background:{C.card_hover}; border:1px solid {C.primary}60; border-radius:14px; }}
            """)
        else:
            self.setStyleSheet(f"""
                StatCard {{ background:{C.card}; border:1px solid {C.border}; border-radius:14px; }}
            """)

    def enterEvent(self, e): self._update(True)
    def leaveEvent(self, e): self._update(False)


# ========== 快捷操作卡片 ==========

class QuickCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon, title, desc, accent=C.primary):
        super().__init__()
        self.accent = accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(105)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(18, 16, 18, 16)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size:22px; border:none; background:transparent;")
        layout.addWidget(icon_lbl)

        t = QLabel(title)
        t.setStyleSheet(f"font-size:14px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        layout.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(f"font-size:11px; color:{C.text_dim}; border:none; background:transparent;")
        d.setWordWrap(True)
        layout.addWidget(d)

        self._update(False)

    def _update(self, hovered):
        if hovered:
            self.setStyleSheet(f"""
                QuickCard {{ background:{C.card_hover}; border:2px solid {self.accent}; border-radius:12px; }}
            """)
        else:
            self.setStyleSheet(f"""
                QuickCard {{ background:{C.card}; border:1px solid {C.border}; border-radius:12px; }}
            """)

    def enterEvent(self, e): self._update(True)
    def leaveEvent(self, e): self._update(False)
    def mousePressEvent(self, e): self.clicked.emit()


# ========== 爬虫线程 ==========

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
            ok = await self.crawler.login()
            self.login_status_signal.emit(ok)
            if not ok: return None
            return await self.crawler.search_and_collect(self.keyword, self.max_items, self.download_images)
        try:
            tid = asyncio.run(_run())
            self.finished_signal.emit(tid)
        except Exception as e:
            self.log_signal.emit(f"运行异常: {e}", "error")
            self.finished_signal.emit(None)

    def stop(self):
        if hasattr(self, 'crawler') and self.crawler: self.crawler.stop()


# ========== 主窗口 ==========

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = get_config()
        self.db = Database()
        self.analyzer = Analyzer(self.db)
        self.exporter = Exporter(self.db)
        self.researcher = MarketResearcher()
        self.worker = None
        self.current_task_id = None
        self._init_ui()
        self._load_task_history()
        self._refresh_dashboard()

    def _init_ui(self):
        self.setWindowTitle("🐟 闲鱼数据调研工具 v5.0")
        self.setMinimumSize(1200, 800)
        self.resize(1300, 880)

        self.setStyleSheet(f"""
            QMainWindow {{ background:{C.bg}; }}
            QTabWidget::pane {{ border:none; background:{C.bg}; }}
            QTabBar::tab {{
                background:{C.card}; color:{C.text_dim}; padding:10px 22px;
                font-size:13px; border:1px solid {C.border}; border-bottom:none;
                border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px;
            }}
            QTabBar::tab:selected {{
                background:{C.bg}; color:{C.primary}; font-weight:bold;
                border-bottom:2px solid {C.primary};
            }}
            QTabBar::tab:hover:!selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
                border:2px solid {C.input_border}; border-radius:8px;
                padding:10px 14px; font-size:13px; background:{C.input_bg}; color:{C.text};
                selection-background-color:{C.primary_bg};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color:{C.input_focus}; background:{C.primary_bg};
            }}
            QLineEdit::placeholder {{ color:{C.text_muted}; }}
            QComboBox::drop-down {{ border:none; padding-right:10px; }}
            QComboBox QAbstractItemView {{
                background:{C.card}; color:{C.text}; border:1px solid {C.border};
                selection-background-color:{C.primary_bg};
            }}
            QPushButton {{
                border-radius:8px; padding:8px 20px; font-size:13px; font-weight:500;
                color:{C.text}; background:{C.card}; border:1px solid {C.border};
            }}
            QPushButton:hover {{ background:{C.primary_bg}; border-color:{C.primary}; }}
            QTableWidget {{
                gridline-color:{C.border}; font-size:12px; border:1px solid {C.border};
                border-radius:8px; background:{C.card}; color:{C.text};
                alternate-background-color:{C.table_row_alt};
            }}
            QTableWidget::item {{ padding:8px; border-bottom:1px solid {C.border}; }}
            QTableWidget::item:selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QHeaderView::section {{
                background:{C.table_header}; border:none; border-bottom:2px solid {C.border};
                padding:10px 8px; font-weight:bold; color:{C.text_dim};
            }}
            QProgressBar {{
                border:none; border-radius:10px; background:{C.border}; height:6px;
            }}
            QProgressBar::chunk {{
                border-radius:10px;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.primary}, stop:1 {C.primary_hover});
            }}
            QScrollArea {{ border:none; background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:8px; }}
            QScrollBar::handle:vertical {{ background:{C.scrollbar}; border-radius:4px; min-height:30px; }}
            QScrollBar::handle:vertical:hover {{ background:{C.scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QGroupBox {{
                font-weight:bold; color:{C.text}; border:1px solid {C.border};
                border-radius:12px; margin-top:14px; padding:24px 16px 16px 16px;
                background:{C.card};
            }}
            QGroupBox::title {{ subcontrol-origin:margin; left:16px; padding:0 8px; color:{C.primary}; }}
            QMenuBar {{ background:{C.card}; color:{C.text_dim}; border-bottom:1px solid {C.border}; padding:4px; }}
            QMenuBar::item {{ padding:6px 12px; border-radius:4px; }}
            QMenuBar::item:selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QMenu {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; padding:6px; }}
            QMenu::item {{ padding:8px 30px; border-radius:4px; }}
            QMenu::item:selected {{ background:{C.primary_bg}; }}
            QMenu::separator {{ height:1px; background:{C.border}; margin:4px 10px; }}
            QCheckBox {{ color:{C.text}; spacing:8px; }}
            QCheckBox::indicator {{
                width:18px; height:18px; border:2px solid {C.border};
                border-radius:4px; background:{C.card};
            }}
            QCheckBox::indicator:checked {{ background:{C.primary}; border-color:{C.primary}; }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                border:none; background:{C.table_header}; border-top-right-radius:6px;
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                border:none; background:{C.table_header}; border-bottom-right-radius:6px;
            }}
            QLabel {{ color:{C.text}; }}
            QStatusBar {{ background:{C.card}; border-top:1px solid {C.border}; padding:4px 16px; font-size:11px; color:{C.text_dim}; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout(central)
        ml.setSpacing(0)
        ml.setContentsMargins(0, 0, 0, 0)

        self._navbar(ml)
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.addTab(self._dashboard(), "🏠 仪表盘")
        self.tab_widget.addTab(self._research_tab(), "🔍 AI调研")
        self.tab_widget.addTab(self._data_tab(), "📊 数据预览")
        self.tab_widget.addTab(self._analysis_tab(), "📈 文案分析")
        self.tab_widget.addTab(self._log_tab(), "📋 运行日志")
        self.tab_widget.addTab(self._settings_tab(), "⚙️ 设置")
        ml.addWidget(self.tab_widget)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("🟢 就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self._menus()

    # ===== 导航栏 =====

    def _navbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"background:{C.navbar_bg}; border-bottom:1px solid {C.border};")
        nl = QHBoxLayout(bar)
        nl.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("🐟 闲鱼数据调研工具")
        logo.setStyleSheet(f"font-size:19px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        nl.addWidget(logo)

        ver = QLabel("v5.0")
        ver.setStyleSheet(f"font-size:10px; color:{C.primary}; background:{C.primary_bg}; border-radius:4px; padding:2px 8px; margin-left:8px;")
        nl.addWidget(ver)
        nl.addStretch()

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入商品关键词搜索...")
        self.nav_keyword.setFixedWidth(260)
        self.nav_keyword.setFixedHeight(40)
        self.nav_keyword.returnPressed.connect(self._on_start)
        nl.addWidget(self.nav_keyword)

        self.nav_count = QSpinBox()
        self.nav_count.setRange(5, 100)
        self.nav_count.setValue(30)
        self.nav_count.setSuffix(" 条")
        self.nav_count.setFixedWidth(85)
        self.nav_count.setFixedHeight(40)
        nl.addWidget(self.nav_count)

        # AI调研按钮
        self.research_btn = QPushButton("🔍 AI调研")
        self.research_btn.setFixedHeight(40)
        self.research_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.card}; border:1px solid {C.border}; color:{C.text}; font-weight:bold; }}
            QPushButton:hover {{ border-color:{C.info}; color:{C.info}; background:{C.info_bg}; }}
        """)
        self.research_btn.clicked.connect(self._on_research)
        nl.addWidget(self.research_btn)

        self.nav_start_btn = QPushButton("🚀 开始采集")
        self.nav_start_btn.setFixedHeight(40)
        self.nav_start_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; font-size:14px; border:none; padding:8px 24px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
            QPushButton:disabled {{ background:{C.border}; color:{C.text_muted}; }}
        """)
        self.nav_start_btn.clicked.connect(self._on_start)
        nl.addWidget(self.nav_start_btn)
        parent.addWidget(bar)

    # ===== 仪表盘 =====

    def _dashboard(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(20)
        lay.setContentsMargins(28, 24, 28, 24)

        # 横幅
        banner = QFrame()
        banner.setFixedHeight(90)
        banner.setStyleSheet(f"""
            QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.primary}, stop:1 #F7C948);
                     border-radius:16px; }}
        """)
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(28, 14, 28, 14)
        bt = QVBoxLayout()
        t1 = QLabel("👋 欢迎使用闲鱼数据调研工具")
        t1.setStyleSheet("color:white; font-size:21px; font-weight:bold; border:none; background:transparent;")
        bt.addWidget(t1)
        t2 = QLabel("💡 输入关键词 → 自动采集 → 导出分析 → 掌握竞品文案套路")
        t2.setStyleSheet("color:rgba(255,255,255,0.9); font-size:13px; border:none; background:transparent; margin-top:2px;")
        bt.addWidget(t2)
        bl.addLayout(bt)
        bl.addStretch()
        lay.addWidget(banner)

        # 统计
        sr = QHBoxLayout()
        sr.setSpacing(14)
        self.card_total = StatCard("📦", "已采集商品", "0", C.primary)
        sr.addWidget(self.card_total)
        self.card_tasks = StatCard("📋", "采集任务数", "0", C.info)
        sr.addWidget(self.card_tasks)
        self.card_avg_price = StatCard("💰", "平均价格", "¥0", C.success)
        sr.addWidget(self.card_avg_price)
        self.card_hot_word = StatCard("🔥", "热门关键词", "-", C.purple)
        sr.addWidget(self.card_hot_word)
        lay.addLayout(sr)

        # 快捷操作
        st = QLabel("⚡ 快捷操作")
        st.setStyleSheet(f"font-size:16px; font-weight:bold; color:{C.text}; background:transparent;")
        lay.addWidget(st)

        grid = QGridLayout()
        grid.setSpacing(12)
        ops = [
            ("📥", "导出Excel", "导出采集数据\n为Excel表格", C.primary, self._on_export_excel),
            ("📊", "文案分析", "生成竞品文案\n高频词分析报告", C.purple, self._on_analyze),
            ("📂", "数据目录", "打开数据存储\n文件夹", C.info, lambda: os.startfile(self.cfg["paths"]["data_dir"])),
            ("🖼", "图片目录", "打开已下载\n商品图片", C.success, lambda: os.startfile(self.cfg["paths"]["image_dir"])),
            ("⚙️", "防封设置", "调整采集间隔\n和安全策略", C.warning, self._on_config_dialog),
            ("📖", "使用帮助", "查看完整使用\n说明文档", C.cyan, self._on_about),
        ]
        for idx, (ic, ti, de, co, cb) in enumerate(ops):
            card = QuickCard(ic, ti, de, co)
            card.clicked.connect(cb)
            r, c = divmod(idx, 3)
            grid.addWidget(card, r, c)
        lay.addLayout(grid)

        # 最近任务
        rl = QLabel("📌 最近采集任务")
        rl.setStyleSheet(f"font-size:16px; font-weight:bold; color:{C.text}; background:transparent;")
        lay.addWidget(rl)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["任务ID", "关键词", "商品数", "状态", "采集时间"])
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.recent_table.setMaximumHeight(200)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        lay.addWidget(self.recent_table)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    # ===== AI调研 =====

    def _research_tab(self):
        """AI市场调研标签页"""
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        # 说明区
        info = QLabel(
            "💡 <b>AI市场调研</b>：输入关键词，先分析市场热度、品类、价格区间、采集策略，\n"
            "确认值得采集后再启动爬虫，避免浪费时间采集无价值的数据。"
        )
        info.setStyleSheet(f"color:{C.text_dim}; font-size:12px; background:{C.primary_bg}; "
                           f"border:1px solid {C.primary}30; border-radius:8px; padding:12px;")
        info.setWordWrap(True)
        lay.addWidget(info)

        # 输入区
        input_row = QHBoxLayout()
        self.research_keyword = QLineEdit()
        self.research_keyword.setPlaceholderText("输入要调研的关键词，如：蓝牙耳机、机械键盘...")
        self.research_keyword.setFixedHeight(40)
        self.research_keyword.returnPressed.connect(self._on_research)
        input_row.addWidget(self.research_keyword)

        btn = QPushButton("🔍 开始调研")
        btn.setFixedHeight(40)
        btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; border:none; padding:8px 24px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        btn.clicked.connect(self._on_research)
        input_row.addWidget(btn)

        # 快捷采集按钮
        quick_btn = QPushButton("📊 调研后直接采集")
        quick_btn.setFixedHeight(40)
        quick_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.success}; color:white; font-weight:bold; border:none; padding:8px 20px; }}
            QPushButton:hover {{ background:#38B820; }}
        """)
        quick_btn.clicked.connect(self._on_research_and_collect)
        input_row.addWidget(quick_btn)

        lay.addLayout(input_row)

        # 调研结果
        self.research_text = QTextEdit()
        self.research_text.setReadOnly(True)
        self.research_text.setFont(QFont("Microsoft YaHei", 11))
        self.research_text.setStyleSheet(f"""
            QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border};
                        border-radius:10px; padding:20px; line-height:1.7; }}
        """)
        self.research_text.setPlaceholderText("👈 输入关键词，点击「开始调研」查看市场分析报告...")
        lay.addWidget(self.research_text)

        return w

    def _on_research(self):
        """执行AI调研"""
        kw = self.research_keyword.text().strip()
        if not kw:
            kw = self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入要调研的关键词")
            return

        self.tab_widget.setCurrentIndex(1)
        self.research_text.setPlainText("🔍 正在分析中...\n")
        QApplication.processEvents()

        try:
            md = self.researcher.generate_markdown_report(kw)
            self.research_text.setMarkdown(md)
        except Exception as e:
            self.research_text.setPlainText(f"调研失败: {e}")

    def _on_research_and_collect(self):
        """调研后直接采集"""
        kw = self.research_keyword.text().strip()
        if not kw:
            kw = self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return

        # 先生成调研报告
        self._on_research()

        # 然后设置导航栏关键词并开始采集
        self.nav_keyword.setText(kw)
        reply = QMessageBox.question(
            self, "确认采集",
            f"<h3>调研报告已生成</h3>"
            f"<p>是否现在开始采集「{kw}」的商品数据？</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_start()

    # ===== 数据预览 =====

    def _data_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        tb = QHBoxLayout()
        tb.setSpacing(8)
        tb.addWidget(QLabel("📋 任务:"))
        self.data_task_combo = QComboBox()
        self.data_task_combo.setMinimumWidth(340)
        self.data_task_combo.currentIndexChanged.connect(self._on_task_selected)
        tb.addWidget(self.data_task_combo)
        tb.addStretch()

        for txt, co, cb in [
            ("📥 导出 Excel", C.primary, self._on_export_excel),
            ("📄 导出 CSV", C.info, self._on_export_csv),
            ("📊 分析报告", C.purple, self._on_analyze),
            ("🔄 刷新", C.text_dim, self._refresh_data_view),
        ]:
            btn = QPushButton(txt)
            btn.setStyleSheet(f"QPushButton:hover {{ border-color:{co}; color:{co}; }}")
            btn.clicked.connect(cb)
            tb.addWidget(btn)
        lay.addLayout(tb)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(9)
        self.data_table.setHorizontalHeaderLabels(["#", "标题", "价格", "原价", "所在地", "卖家", "浏览", "想要", "采集时间"])
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        lay.addWidget(self.data_table)
        return w

    # ===== 文案分析 =====

    def _analysis_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        tb = QHBoxLayout()
        tb.addStretch()
        ab = QPushButton("🔍 生成分析报告")
        ab.setStyleSheet(f"""
            QPushButton {{ background:{C.purple}; color:white; font-weight:bold; padding:12px 30px; border:none; font-size:14px; }}
            QPushButton:hover {{ background:#5B21B6; }}
        """)
        ab.clicked.connect(self._on_analyze)
        tb.addWidget(ab)
        sb = QPushButton("💾 保存报告")
        sb.setStyleSheet(f"""
            QPushButton {{ font-weight:bold; padding:12px 30px; font-size:14px; }}
            QPushButton:hover {{ border-color:{C.purple}; color:{C.purple}; }}
        """)
        sb.clicked.connect(self._save_report)
        tb.addWidget(sb)
        lay.addLayout(tb)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Microsoft YaHei", 11))
        self.analysis_text.setStyleSheet(f"""
            QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border};
                        border-radius:10px; padding:20px; line-height:1.7; }}
        """)
        self.analysis_text.setPlaceholderText("👈 点击「生成分析报告」查看文案分析...")
        lay.addWidget(self.analysis_text)
        return w

    # ===== 运行日志 =====

    def _log_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(8)
        lay.setContentsMargins(20, 16, 20, 16)

        lt = QHBoxLayout()
        self.log_status_label = QLabel("🟢 就绪")
        self.log_status_label.setStyleSheet(f"font-size:12px; color:{C.success}; font-weight:bold; background:transparent;")
        lt.addWidget(self.log_status_label)
        lt.addStretch()
        cb = QPushButton("🗑 清空日志")
        cb.setStyleSheet(f"QPushButton:hover {{ border-color:{C.danger}; color:{C.danger}; }}")
        cb.clicked.connect(lambda: self.log_text.clear())
        lt.addWidget(cb)
        lay.addLayout(lt)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{ background:{C.log_bg}; color:#D4D4D4; border:1px solid #3D3929;
                        border-radius:10px; padding:14px; }}
        """)
        self.log_text.setPlaceholderText("运行日志将显示在这里...")
        lay.addWidget(self.log_text)
        return w

    # ===== 设置 =====

    def _settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(20)
        lay.setContentsMargins(28, 24, 28, 24)

        # ===== AI 调研设置 =====
        ai_group = QGroupBox("🤖 AI 市场调研设置")
        ai_layout = QFormLayout(ai_group)
        ai_layout.setSpacing(14)

        # 加载AI配置
        from core.researcher import MarketResearcher
        mr = MarketResearcher()
        ai_config = mr.config

        self.ai_enabled = QCheckBox("启用AI大模型调研（需要配置API）")
        self.ai_enabled.setChecked(ai_config.get("enabled", False))
        self.ai_enabled.setToolTip("勾选后优先使用大模型分析，失败自动降级到本地规则")
        ai_layout.addRow(self.ai_enabled)

        # API提供商选择
        self.ai_provider = QComboBox()
        providers = MarketResearcher.API_PROVIDERS
        for key, info in providers.items():
            self.ai_provider.addItem(f"{info['name']} ({info.get('price_note', '')})", key)
        current_provider = ai_config.get("provider", "deepseek")
        for i in range(self.ai_provider.count()):
            if self.ai_provider.itemData(i) == current_provider:
                self.ai_provider.setCurrentIndex(i)
                break
        self.ai_provider.currentIndexChanged.connect(self._on_provider_changed)
        ai_layout.addRow("API提供商:", self.ai_provider)

        # API地址
        self.ai_url = QLineEdit()
        self.ai_url.setPlaceholderText("https://api.deepseek.com/v1/chat/completions")
        self.ai_url.setText(ai_config.get("api_url", ""))
        ai_layout.addRow("API地址:", self.ai_url)

        # API密钥
        self.ai_key = QLineEdit()
        self.ai_key.setPlaceholderText("sk-xxxxxxxxxxxxxxxx")
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_key.setText(ai_config.get("api_key", ""))
        ai_layout.addRow("API密钥:", self.ai_key)

        # 模型名
        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("deepseek-chat")
        self.ai_model.setText(ai_config.get("model", ""))
        ai_layout.addRow("模型名称:", self.ai_model)

        # 获取API Key链接
        self.ai_key_link = QLabel("")
        self.ai_key_link.setOpenExternalLinks(True)
        self.ai_key_link.setStyleSheet(f"color:{C.info}; font-size:11px; background:transparent;")
        ai_layout.addRow("", self.ai_key_link)
        self._on_provider_changed(self.ai_provider.currentIndex())

        # 测试按钮
        test_row = QHBoxLayout()
        self.ai_test_btn = QPushButton("🧪 测试连接")
        self.ai_test_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.info}; color:white; font-weight:bold; padding:8px 20px; border:none; }}
            QPushButton:hover {{ background:#0066CC; }}
        """)
        self.ai_test_btn.clicked.connect(self._on_test_ai)
        test_row.addWidget(self.ai_test_btn)
        self.ai_test_status = QLabel("")
        self.ai_test_status.setStyleSheet("font-size:12px; background:transparent;")
        test_row.addWidget(self.ai_test_status)
        test_row.addStretch()
        ai_layout.addRow(test_row)

        lay.addWidget(ai_group)

        # ===== 防封策略设置 =====
        ag = QGroupBox("🛡 防封策略设置")
        al = QFormLayout(ag)
        al.setSpacing(14)
        self.set_min_delay = QDoubleSpinBox()
        self.set_min_delay.setRange(1.0, 30.0)
        self.set_min_delay.setValue(self.cfg["anti_ban"]["min_delay"])
        self.set_min_delay.setSuffix(" 秒")
        al.addRow("最小采集间隔:", self.set_min_delay)
        self.set_max_delay = QDoubleSpinBox()
        self.set_max_delay.setRange(1.0, 60.0)
        self.set_max_delay.setValue(self.cfg["anti_ban"]["max_delay"])
        self.set_max_delay.setSuffix(" 秒")
        al.addRow("最大采集间隔:", self.set_max_delay)
        self.set_page_min = QDoubleSpinBox()
        self.set_page_min.setRange(2.0, 30.0)
        self.set_page_min.setValue(self.cfg["anti_ban"]["page_delay_min"])
        self.set_page_min.setSuffix(" 秒")
        al.addRow("翻页最小间隔:", self.set_page_min)
        self.set_page_max = QDoubleSpinBox()
        self.set_page_max.setRange(2.0, 60.0)
        self.set_page_max.setValue(self.cfg["anti_ban"]["page_delay_max"])
        self.set_page_max.setSuffix(" 秒")
        al.addRow("翻页最大间隔:", self.set_page_max)
        self.set_max_items = QSpinBox()
        self.set_max_items.setRange(10, 200)
        self.set_max_items.setValue(self.cfg["anti_ban"]["max_items_per_session"])
        al.addRow("单次最大采集:", self.set_max_items)
        lay.addWidget(ag)

        cg = QGroupBox("📷 采集设置")
        cl = QFormLayout(cg)
        cl.setSpacing(14)
        self.set_download_img = QCheckBox("自动下载商品图片")
        self.set_download_img.setChecked(self.cfg["collection"]["download_images"])
        cl.addRow(self.set_download_img)
        self.set_img_quality = QSpinBox()
        self.set_img_quality.setRange(10, 100)
        self.set_img_quality.setValue(self.cfg["collection"]["image_quality"])
        self.set_img_quality.setSuffix(" %")
        cl.addRow("图片保存质量:", self.set_img_quality)
        lay.addWidget(cg)

        sv = QPushButton("💾 保存设置")
        sv.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; font-size:15px; padding:14px; border:none; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        sv.clicked.connect(self._save_all_settings)
        lay.addWidget(sv)
        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _on_provider_changed(self, index):
        """切换API提供商时更新默认配置"""
        key = self.ai_provider.itemData(index)
        if not key:
            return
        from core.researcher import MarketResearcher
        info = MarketResearcher.API_PROVIDERS.get(key, {})
        # Agnes AI 默认填写
        if info.get("url"):
            self.ai_url.setText(info["url"])
        if info.get("default_model"):
            self.ai_model.setText(info["default_model"])
        if info.get("get_key_url"):
            desc = info.get("description", "")
            self.ai_key_link.setText(
                f"<a href='{info['get_key_url']}'>🔑 获取 {info['name']} API Key</a>"
                + (f" — {desc}" if desc else "")
            )
        else:
            self.ai_key_link.setText("")

    def _on_test_ai(self):
        """测试AI连接"""
        key = self.ai_key.text().strip()
        url = self.ai_url.text().strip()
        model = self.ai_model.text().strip()

        if not key or not url:
            self.ai_test_status.setText("❌ 请填写 API密钥 和 API地址")
            self.ai_test_status.setStyleSheet(f"font-size:12px; color:{C.danger}; background:transparent;")
            return

        self.ai_test_status.setText("⏳ 测试中...")
        self.ai_test_status.setStyleSheet(f"font-size:12px; color:{C.warning}; background:transparent;")
        QApplication.processEvents()

        try:
            from core.researcher import MarketResearcher
            mr = MarketResearcher({
                "enabled": True, "provider": self.ai_provider.currentData(),
                "api_key": key, "api_url": url, "model": model,
            })
            result = mr.research("iPhone 15")
            if result.get("ai_powered"):
                self.ai_test_status.setText(f"✅ 连接成功！（{result.get('model', '')}）")
                self.ai_test_status.setStyleSheet(f"font-size:12px; color:{C.success}; background:transparent;")
            else:
                self.ai_test_status.setText(f"⚠ 连接成功但解析失败，已降级到本地规则")
                self.ai_test_status.setStyleSheet(f"font-size:12px; color:{C.warning}; background:transparent;")
        except Exception as e:
            self.ai_test_status.setText(f"❌ 连接失败: {str(e)[:80]}")
            self.ai_test_status.setStyleSheet(f"font-size:12px; color:{C.danger}; background:transparent;")

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

        # 保存AI配置
        from core.researcher import MarketResearcher
        mr = MarketResearcher()
        ai_config = {
            "enabled": self.ai_enabled.isChecked(),
            "provider": self.ai_provider.currentData(),
            "api_key": self.ai_key.text().strip(),
            "api_url": self.ai_url.text().strip(),
            "model": self.ai_model.text().strip(),
        }
        mr.save_config(ai_config)
        # 更新当前实例的配置
        self.researcher = MarketResearcher(ai_config)

        QMessageBox.information(self, "设置已保存", "<h3>✅ 所有设置已保存</h3><p>新设置将在下次操作时生效</p>")
        return scroll

    # ===== 菜单 =====

    def _menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("文件(&F)")
        for t, cb in [("打开数据目录", lambda: os.startfile(self.cfg["paths"]["data_dir"])),
                       ("打开导出目录", lambda: os.startfile(self.cfg["paths"]["export_dir"]))]:
            a = QAction(t, self)
            a.triggered.connect(cb)
            fm.addAction(a)
        fm.addSeparator()
        a = QAction("退出(&Q)", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        fm.addAction(a)
        hm = mb.addMenu("帮助(&H)")
        for t, cb in [("使用说明", self._on_about),
                       ("GitHub 项目", lambda: os.startfile("https://github.com/Roue-AFK/xianyu-data-tool"))]:
            a = QAction(t, self)
            a.triggered.connect(cb)
            hm.addAction(a)

    # ===== 仪表盘数据 =====

    def _refresh_dashboard(self):
        total = self.db.get_item_count()
        self.card_total.value_label.setText(str(total))
        tasks = self.db.get_tasks(limit=100)
        self.card_tasks.value_label.setText(str(len(tasks)))
        if tasks:
            s = self.db.get_price_stats(tasks[0]["id"])
            self.card_avg_price.value_label.setText(f"¥{(s.get('avg_price',0) or 0):.0f}")
            kc = {}
            for t in tasks:
                kw = t.get("keyword", "")
                if kw: kc[kw] = kc.get(kw, 0) + 1
            self.card_hot_word.value_label.setText(max(kc, key=kc.get) if kc else "-")
        else:
            self.card_avg_price.value_label.setText("¥0")
            self.card_hot_word.value_label.setText("-")

        self.recent_table.setRowCount(min(len(tasks), 10))
        for i, t in enumerate(tasks[:10]):
            self.recent_table.setItem(i, 0, QTableWidgetItem(f"#{t['id']}"))
            self.recent_table.setItem(i, 1, QTableWidgetItem(t.get("keyword", "")))
            self.recent_table.setItem(i, 2, QTableWidgetItem(str(t.get("item_count", 0))))
            st = "✅ 完成" if t.get("status") == "finished" else "🔄 进行中"
            self.recent_table.setItem(i, 3, QTableWidgetItem(st))
            self.recent_table.setItem(i, 4, QTableWidgetItem(str(t.get("created_at", "")[:16])))

    # ===== 事件 =====

    def _on_start(self):
        kw = self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        mx = self.nav_count.value()
        di = self.set_download_img.isChecked()

        r = QMessageBox.question(self, "确认开始采集",
            f"<h3>即将开始采集</h3><p><b>关键词：</b>{kw}<br><b>数量：</b>最多 {mx} 条<br>"
            f"<b>下载图片：</b>{'是' if di else '否'}</p>"
            f"<p style='color:{C.danger};'>⚠ 采集过程会自动打开浏览器窗口<br>"
            f"⚠ 如果未登录请扫码登录闲鱼<br>⚠ 采集过程中请勿手动操作浏览器</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if r != QMessageBox.StandardButton.Yes: return

        self.nav_start_btn.setEnabled(False)
        self.nav_start_btn.setText("⏳ 采集中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, mx)
        self.progress_bar.setValue(0)
        self.log_status_label.setText("🟡 采集中...")
        self.log_status_label.setStyleSheet(f"font-size:12px; color:{C.warning}; font-weight:bold; background:transparent;")
        self.log_text.clear()
        self._log("=" * 60, "info")
        self._log(f"🚀 开始采集：{kw}（目标 {mx} 条）", "info")
        self._log("=" * 60, "info")
        self.tab_widget.setCurrentIndex(3)

        self.worker = CrawlerWorker(kw, mx, di)
        self.worker.log_signal.connect(self._on_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.login_status_signal.connect(self._on_login_status)
        self.worker.start()

    def _on_log(self, m, lv="info"): self._log(m, lv)

    def _on_progress(self, cur, tot, msg):
        self.progress_bar.setValue(cur)
        self.status_bar.showMessage(f"🔄 {msg}")

    def _on_login_status(self, ok):
        self._log("✅ 登录状态：已登录" if ok else "⏳ 等待扫码登录...", "success" if ok else "warning")

    def _on_finished(self, tid):
        self.nav_start_btn.setEnabled(True)
        self.nav_start_btn.setText("🚀 开始采集")
        self.progress_bar.setVisible(False)
        self.log_status_label.setText("🟢 就绪")
        self.log_status_label.setStyleSheet(f"font-size:12px; color:{C.success}; font-weight:bold; background:transparent;")
        self.worker = None
        if tid:
            self.current_task_id = tid
            self.status_bar.showMessage(f"✅ 采集完成 - 任务 #{tid}")
            self._log("=" * 60, "success")
            self._log(f"🎉 采集任务 #{tid} 完成！", "success")
            self._log("=" * 60, "success")
            self._load_task_history()
            self._refresh_data_view()
            self._refresh_dashboard()
            r = QMessageBox.question(self, "采集完成", "<h3>🎉 采集完成！</h3><p>是否立即导出 Excel？</p>",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.Yes)
            if r == QMessageBox.StandardButton.Yes: self._on_export_excel()
        else:
            self.status_bar.showMessage("⚠ 采集中断或失败")

    def _log(self, msg, lv="info"):
        cols = {"info": "#D4D4D4", "success": "#4EC9B0", "warning": "#CE9178", "error": "#F44747", "debug": "#808080"}
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.setTextColor(QColor(cols.get(lv, "#D4D4D4")))
        self.log_text.insertPlainText(msg + "\n")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    # ===== 数据操作 =====

    def _load_task_history(self):
        self.data_task_combo.blockSignals(True)
        self.data_task_combo.clear()
        self.data_task_combo.addItem("📋 全部任务", None)
        for t in self.db.get_tasks(limit=50):
            lb = f"#{t['id']} | {t['keyword']} | {t.get('item_count',0)}条 | {t['created_at'][:16]}"
            self.data_task_combo.addItem(lb, t["id"])
        self.data_task_combo.blockSignals(False)
        self._refresh_dashboard()

    def _on_task_selected(self, _):
        self.current_task_id = self.data_task_combo.currentData()
        self._refresh_data_view()

    def _refresh_data_view(self):
        items = self.db.get_items(task_id=self.data_task_combo.currentData(), limit=200)
        self.data_table.setRowCount(len(items))
        for i, it in enumerate(items):
            for j, v in enumerate([str(i+1), it.get("title",""), f"¥{it.get('price',0):.2f}",
                                   f"¥{it.get('original_price',0):.2f}", it.get("location",""),
                                   it.get("seller_name",""), str(it.get("views",0)),
                                   str(it.get("wants",0)), str(it.get("collected_at","")[:16])]):
                self.data_table.setItem(i, j, QTableWidgetItem(v))
        self.status_bar.showMessage(f"📊 共 {len(items)} 条数据")

    def _on_export_excel(self):
        try:
            task_id = self.data_task_combo.currentData()
            # 获取任务关键词
            keyword = "全部"
            if task_id:
                task = self.db.get_task(task_id)
                if task:
                    keyword = task.get("keyword", "全部")
            else:
                keyword = self.nav_keyword.text().strip() or "全部"

            p = self.exporter.export_to_excel(task_id=task_id, keyword=keyword)
            self._log(f"✅ Excel 导出成功: {p}", "success")
            QMessageBox.information(self, "导出成功",
                f"<h3>✅ 导出成功</h3>"
                f"<p>文件位置：<br><code>{p}</code></p>"
                f"<p>包含三个工作表：商品数据 | 统计分析 | 文案汇总</p>")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出时发生错误：\n{str(e)}")

    def _on_export_csv(self):
        try:
            task_id = self.data_task_combo.currentData()
            keyword = "全部"
            if task_id:
                task = self.db.get_task(task_id)
                if task:
                    keyword = task.get("keyword", "全部")
            else:
                keyword = self.nav_keyword.text().strip() or "全部"

            p = self.exporter.export_to_csv(task_id=task_id, keyword=keyword)
            self._log(f"✅ CSV 导出成功: {p}", "success")
            QMessageBox.information(self, "导出成功", f"<h3>✅ 导出成功</h3><p>{p}</p>")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出时发生错误：\n{str(e)}")

    def _on_analyze(self):
        try:
            md = self.analyzer.generate_markdown_report(self.data_task_combo.currentData(),
                                                         self.nav_keyword.text().strip() or "全部")
            self.analysis_text.setMarkdown(md)
            self.tab_widget.setCurrentIndex(2)
            self._log("✅ 分析报告生成完成", "success")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._last_report_path = os.path.join(self.cfg["paths"]["export_dir"], f"分析报告_{ts}.md")
            with open(self._last_report_path, "w", encoding="utf-8") as f:
                f.write(md)
            self._log(f"💾 报告已保存: {self._last_report_path}", "info")
        except Exception as e:
            QMessageBox.critical(self, "分析失败", str(e))

    def _save_report(self):
        if hasattr(self, '_last_report_path'): os.startfile(os.path.dirname(self._last_report_path))
        else: QMessageBox.information(self, "提示", "请先生成分析报告")

    def _on_config_dialog(self): self.tab_widget.setCurrentIndex(4)

    def _on_about(self):
        QMessageBox.about(self, "使用说明",
            f"""<h2 style='color:{C.primary};'>🐟 闲鱼数据调研工具 v5.0</h2>
            <h3>📖 使用步骤</h3><ol>
            <li>在顶部搜索框输入关键词</li><li>设置采集数量（建议30-50条）</li>
            <li>点击「开始采集」</li><li>扫码登录闲鱼（仅首次）</li>
            <li>等待自动采集</li><li>导出 Excel 或生成文案报告</li></ol>
            <h3>🛡 防封保护</h3><ul>
            <li>模拟真人浏览，每条间隔3-8秒</li><li>随机滚动和鼠标移动</li>
            <li>单次最多100条</li><li>Cookie 本地保存</li></ul>
            <h3>⚠ 注意</h3><ul><li>仅供个人学习研究</li><li>勿用于商业用途</li><li>采集时勿操作浏览器</li></ul>""")

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            r = QMessageBox.question(self, "确认退出", "采集进行中，确定退出？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self.worker.stop(); self.worker.wait(3000); self.db.close(); e.accept()
            else:
                e.ignore()
        else:
            self.db.close(); e.accept()
