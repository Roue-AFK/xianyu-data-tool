"""
闲鱼数据调研工具 - 主窗口 GUI v6.0
左下角设置面板、AI配置套件、滚轮禁用、即时保存
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
    QGridLayout, QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QSplitter, QApplication, QSlider, QStackedWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction, QWheelEvent

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter
from core.researcher import MarketResearcher
from core.assistant import AIAssistant


# ========== 配色 ==========

class C:
    bg              = "#F5F3EE"
    card            = "#FFFFFF"
    card_hover      = "#FFFBEB"
    border          = "#E8E3D9"
    border_hover    = "#F5C842"
    text            = "#3D3929"
    text_dim        = "#8B8576"
    text_muted      = "#B8B2A6"
    primary         = "#F5A623"
    primary_hover   = "#F7B84E"
    primary_bg      = "#FFF8E7"
    success         = "#52C41A"
    warning         = "#FAAD14"
    danger          = "#FF4D4F"
    info            = "#1890FF"
    info_bg         = "#E6F7FF"
    purple          = "#722ED1"
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
    panel_bg        = "#FAFAFA"


# ========== 禁用滚轮的控件 ==========

class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, e: QWheelEvent): e.ignore()

class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, e: QWheelEvent): e.ignore()

class NoWheelComboBox(QComboBox):
    def wheelEvent(self, e: QWheelEvent): e.ignore()


# ========== 统计卡片 ==========

class StatCard(QFrame):
    def __init__(self, icon, title, value):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(105)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(18, 14, 18, 14)
        i = QLabel(icon)
        i.setStyleSheet("font-size:20px; border:none; background:transparent;")
        layout.addWidget(i)
        t = QLabel(title)
        t.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        layout.addWidget(t)
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color:{C.stat_value}; font-size:24px; font-weight:bold; border:none; background:transparent;")
        layout.addWidget(self.value_label)
        self._upd(False)

    def _upd(self, h):
        if h:
            self.setStyleSheet(f"StatCard {{ background:{C.card_hover}; border:1px solid {C.primary}60; border-radius:14px; }}")
        else:
            self.setStyleSheet(f"StatCard {{ background:{C.card}; border:1px solid {C.border}; border-radius:14px; }}")
    def enterEvent(self, e): self._upd(True)
    def leaveEvent(self, e): self._upd(False)


# ========== 快捷操作卡片 ==========

class QuickCard(QFrame):
    clicked = pyqtSignal()
    def __init__(self, icon, title, desc, accent=C.primary):
        super().__init__()
        self.accent = accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(100)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 14, 16, 14)
        i = QLabel(icon)
        i.setStyleSheet("font-size:22px; border:none; background:transparent;")
        layout.addWidget(i)
        t = QLabel(title)
        t.setStyleSheet(f"font-size:13px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        layout.addWidget(t)
        d = QLabel(desc)
        d.setStyleSheet(f"font-size:11px; color:{C.text_dim}; border:none; background:transparent;")
        d.setWordWrap(True)
        layout.addWidget(d)
        self._upd(False)

    def _upd(self, h):
        if h:
            self.setStyleSheet(f"QuickCard {{ background:{C.card_hover}; border:2px solid {self.accent}; border-radius:12px; }}")
        else:
            self.setStyleSheet(f"QuickCard {{ background:{C.card}; border:1px solid {C.border}; border-radius:12px; }}")
    def enterEvent(self, e): self._upd(True)
    def leaveEvent(self, e): self._upd(False)
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
        self.crawler = XianyuCrawler(db=self.db, progress_callback=lambda c, t, m: self.progress_signal.emit(c, t, m),
                                      log_callback=lambda m, l="info": self.log_signal.emit(m, l))
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
        self._load_settings_to_panel()
        self._load_task_history()
        self._refresh_dashboard()

    def _init_ui(self):
        self.setWindowTitle("🐟 闲鱼数据调研工具 v6.0")
        self.setMinimumSize(1200, 800)
        self.resize(1350, 900)

        self.setStyleSheet(f"""
            QMainWindow {{ background:{C.bg}; }}
            QTabWidget::pane {{ border:none; background:{C.bg}; }}
            QTabBar::tab {{
                background:{C.card}; color:{C.text_dim}; padding:10px 22px;
                font-size:13px; border:1px solid {C.border}; border-bottom:none;
                border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px;
            }}
            QTabBar::tab:selected {{ background:{C.bg}; color:{C.primary}; font-weight:bold; border-bottom:2px solid {C.primary}; }}
            QTabBar::tab:hover:!selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
                border:2px solid {C.input_border}; border-radius:8px;
                padding:10px 14px; font-size:13px; background:{C.input_bg}; color:{C.text};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color:{C.input_focus}; background:{C.primary_bg}; }}
            QLineEdit::placeholder {{ color:{C.text_muted}; }}
            QComboBox::drop-down {{ border:none; padding-right:10px; }}
            QComboBox QAbstractItemView {{
                background:{C.card}; color:{C.text}; border:1px solid {C.border};
                selection-background-color:{C.primary_bg};
            }}
            QPushButton {{ border-radius:8px; padding:8px 20px; font-size:13px; font-weight:500; color:{C.text}; background:{C.card}; border:1px solid {C.border}; }}
            QPushButton:hover {{ background:{C.primary_bg}; border-color:{C.primary}; }}
            QTableWidget {{ gridline-color:{C.border}; font-size:12px; border:1px solid {C.border}; border-radius:8px; background:{C.card}; color:{C.text}; alternate-background-color:{C.table_row_alt}; }}
            QTableWidget::item {{ padding:8px; border-bottom:1px solid {C.border}; }}
            QTableWidget::item:selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QHeaderView::section {{ background:{C.table_header}; border:none; border-bottom:2px solid {C.border}; padding:10px 8px; font-weight:bold; color:{C.text_dim}; }}
            QProgressBar {{ border:none; border-radius:10px; background:{C.border}; height:6px; }}
            QProgressBar::chunk {{ border-radius:10px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {C.primary},stop:1 {C.primary_hover}); }}
            QScrollArea {{ border:none; background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:8px; }}
            QScrollBar::handle:vertical {{ background:{C.scrollbar}; border-radius:4px; min-height:30px; }}
            QScrollBar::handle:vertical:hover {{ background:{C.scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QGroupBox {{ font-weight:bold; color:{C.text}; border:1px solid {C.border}; border-radius:10px; margin-top:12px; padding:20px 14px 14px 14px; background:{C.card}; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:14px; padding:0 6px; color:{C.primary}; }}
            QCheckBox {{ color:{C.text}; spacing:8px; }}
            QCheckBox::indicator {{ width:18px; height:18px; border:2px solid {C.border}; border-radius:4px; background:{C.card}; }}
            QCheckBox::indicator:checked {{ background:{C.primary}; border-color:{C.primary}; }}
            QLabel {{ color:{C.text}; }}
            QStatusBar {{ background:{C.card}; border-top:1px solid {C.border}; padding:4px 16px; font-size:11px; color:{C.text_dim}; }}
            QListWidget {{ background:transparent; border:none; }}
            QListWidget::item {{ padding:10px 12px; border-radius:8px; margin:2px 0; color:{C.text}; }}
            QListWidget::item:hover {{ background:{C.primary_bg}; }}
            QListWidget::item:selected {{ background:{C.primary_bg}; color:{C.primary}; font-weight:bold; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._navbar(main_layout)

        # 主体：标签页 + 左下设置面板
        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        # 左下设置面板
        self._settings_panel(body)

        # 标签页区域
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.addTab(self._dashboard(), "🏠 仪表盘")
        self.tab_widget.addTab(self._chat_tab(), "💬 AI助手")
        self.tab_widget.addTab(self._research_tab(), "🔍 AI调研")
        self.tab_widget.addTab(self._data_tab(), "📊 数据预览")
        self.tab_widget.addTab(self._analysis_tab(), "📈 文案分析")
        self.tab_widget.addTab(self._log_tab(), "📋 运行日志")
        body.addWidget(self.tab_widget)

        main_layout.addLayout(body)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("🟢 就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)

    # ===== 左下设置面板 =====

    def _settings_panel(self, body):
        """左下角设置面板"""
        panel = QFrame()
        panel.setFixedWidth(280)
        panel.setStyleSheet(f"""
            QFrame {{ background:{C.panel_bg}; border-right:1px solid {C.border}; }}
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 8, 10, 8)

        # 标题
        header = QLabel("⚙️ 设置")
        header.setStyleSheet(f"font-size:15px; font-weight:bold; color:{C.text}; background:transparent; padding:4px;")
        layout.addWidget(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ background:transparent; border:none; }}")

        sw = QWidget()
        sw.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(sw)
        sl.setSpacing(4)
        sl.setContentsMargins(2, 2, 2, 2)

        # === AI 设置 ===
        ai_g = QGroupBox("🤖 AI 配置")
        ai_l = QVBoxLayout(ai_g)
        ai_l.setSpacing(6)

        ai_l.addWidget(QLabel("提供商:"))
        self.cfg_ai_provider = NoWheelComboBox()
        for key, info in MarketResearcher.API_PROVIDERS.items():
            self.cfg_ai_provider.addItem(f"{info['name']}", key)
        self.cfg_ai_provider.currentIndexChanged.connect(self._on_cfg_provider_changed)
        ai_l.addWidget(self.cfg_ai_provider)

        ai_l.addWidget(QLabel("模型:"))
        self.cfg_ai_model = NoWheelComboBox()
        self.cfg_ai_model.setEditable(True)
        self.cfg_ai_model.setToolTip("选择或输入模型名称")
        ai_l.addWidget(self.cfg_ai_model)

        self.cfg_ai_enabled = QCheckBox("启用AI助手和调研")
        ai_l.addWidget(self.cfg_ai_enabled)

        ai_l.addWidget(QLabel("API Key:"))
        self.cfg_ai_key = QLineEdit()
        self.cfg_ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_ai_key.setPlaceholderText("sk-...")
        ai_l.addWidget(self.cfg_ai_key)

        self.cfg_ai_link = QLabel("")
        self.cfg_ai_link.setOpenExternalLinks(True)
        self.cfg_ai_link.setStyleSheet(f"color:{C.info}; font-size:10px; background:transparent;")
        self.cfg_ai_link.setWordWrap(True)
        ai_l.addWidget(self.cfg_ai_link)

        test_btn = QPushButton("🧪 测试连接")
        test_btn.setStyleSheet(f"QPushButton {{ background:{C.info}; color:white; font-weight:bold; padding:6px; }}")
        test_btn.clicked.connect(self._on_test_ai)
        ai_l.addWidget(test_btn)

        self.cfg_ai_status = QLabel("")
        self.cfg_ai_status.setStyleSheet("font-size:10px; background:transparent;")
        self.cfg_ai_status.setWordWrap(True)
        ai_l.addWidget(self.cfg_ai_status)

        sl.addWidget(ai_g)

        # === 防封设置 ===
        ab_g = QGroupBox("🛡 防封策略")
        ab_l = QFormLayout(ab_g)
        ab_l.setSpacing(4)

        self.cfg_min_delay = NoWheelDoubleSpinBox()
        self.cfg_min_delay.setRange(1.0, 30.0)
        self.cfg_min_delay.setSuffix(" 秒")
        ab_l.addRow("最小间隔:", self.cfg_min_delay)

        self.cfg_max_delay = NoWheelDoubleSpinBox()
        self.cfg_max_delay.setRange(1.0, 60.0)
        self.cfg_max_delay.setSuffix(" 秒")
        ab_l.addRow("最大间隔:", self.cfg_max_delay)

        self.cfg_max_items = NoWheelSpinBox()
        self.cfg_max_items.setRange(10, 200)
        self.cfg_max_items.setSuffix(" 条")
        ab_l.addRow("最大采集:", self.cfg_max_items)
        sl.addWidget(ab_g)

        # === 采集设置 ===
        cl_g = QGroupBox("📷 采集")
        cl_l = QVBoxLayout(cl_g)
        cl_l.setSpacing(4)
        self.cfg_download_img = QCheckBox("下载商品图片")
        cl_l.addWidget(self.cfg_download_img)
        self.cfg_headless = QCheckBox("后台运行浏览器")
        self.cfg_headless.setToolTip("浏览器不可见，速度更快但无法手动登录")
        cl_l.addWidget(self.cfg_headless)
        sl.addWidget(cl_g)

        # === 界面设置 ===
        ui_g = QGroupBox("🎨 界面")
        ui_l = QVBoxLayout(ui_g)
        ui_l.setSpacing(4)
        self.cfg_show_welcome = QCheckBox("显示欢迎横幅")
        self.cfg_show_welcome.setChecked(True)
        ui_l.addWidget(self.cfg_show_welcome)
        sl.addWidget(ui_g)

        # === 配置套件 ===
        suite_g = QGroupBox("📦 配置套件")
        suite_l = QVBoxLayout(suite_g)
        suite_l.setSpacing(4)

        self.suite_combo = NoWheelComboBox()
        self.suite_combo.addItem("自定义配置", None)
        self.suite_combo.addItem("🛡 安全优先（慢但稳）", "safe")
        self.suite_combo.addItem("⚡ 平衡模式（推荐）", "balanced")
        self.suite_combo.addItem("🚀 快速采集", "fast")
        self.suite_combo.currentIndexChanged.connect(self._on_suite_changed)
        suite_l.addWidget(self.suite_combo)
        sl.addWidget(suite_g)

        sl.addStretch()

        # 保存按钮
        save_btn = QPushButton("💾 保存设置")
        save_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; padding:10px; border:none; font-size:14px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        save_btn.clicked.connect(self._save_all_settings)
        sl.addWidget(save_btn)

        scroll.setWidget(sw)
        layout.addWidget(scroll)
        body.addWidget(panel)

    def _on_cfg_provider_changed(self, idx):
        """切换AI提供商时更新模型列表和链接"""
        key = self.cfg_ai_provider.itemData(idx)
        if not key: return
        info = MarketResearcher.API_PROVIDERS.get(key, {})

        # 更新模型列表
        self.cfg_ai_model.clear()
        models = {
            "agnes": ["agnes-2.0-flash"],
            "deepseek": ["deepseek-chat", "deepseek-reasoner"],
            "qwen": ["qwen-plus", "qwen-max", "qwen-turbo"],
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            "custom": [],
        }
        for m in models.get(key, []):
            self.cfg_ai_model.addItem(m)

        if info.get("get_key_url"):
            self.cfg_ai_link.setText(f"<a href='{info['get_key_url']}'>🔑 获取Key</a>")
        else:
            self.cfg_ai_link.setText("")

    def _on_suite_changed(self, idx):
        """切换配置套件"""
        key = self.suite_combo.itemData(idx)
        if key == "safe":
            self.cfg_min_delay.setValue(5.0)
            self.cfg_max_delay.setValue(12.0)
            self.cfg_max_items.setValue(50)
        elif key == "balanced":
            self.cfg_min_delay.setValue(2.0)
            self.cfg_max_delay.setValue(5.0)
            self.cfg_max_items.setValue(80)
        elif key == "fast":
            self.cfg_min_delay.setValue(1.0)
            self.cfg_max_delay.setValue(2.0)
            self.cfg_max_items.setValue(100)

    def _load_settings_to_panel(self):
        """加载配置到面板"""
        # AI 配置
        ai_config = self.researcher.config
        self.cfg_ai_enabled.setChecked(ai_config.get("enabled", False))
        self.cfg_ai_key.setText(ai_config.get("api_key", ""))
        self.cfg_ai_model.setCurrentText(ai_config.get("model", ""))

        prov = ai_config.get("provider", "agnes")
        for i in range(self.cfg_ai_provider.count()):
            if self.cfg_ai_provider.itemData(i) == prov:
                self.cfg_ai_provider.setCurrentIndex(i)
                break

        # 防封
        self.cfg_min_delay.setValue(self.cfg["anti_ban"]["min_delay"])
        self.cfg_max_delay.setValue(self.cfg["anti_ban"]["max_delay"])
        self.cfg_max_items.setValue(self.cfg["anti_ban"]["max_items_per_session"])

        # 采集
        self.cfg_download_img.setChecked(self.cfg["collection"]["download_images"])
        self.cfg_headless.setChecked(self.cfg["xianyu"].get("headless", False))

    def _on_test_ai(self):
        key = self.cfg_ai_key.text().strip()
        model = self.cfg_ai_model.currentText().strip()
        prov = self.cfg_ai_provider.currentData()
        info = MarketResearcher.API_PROVIDERS.get(prov, {})
        url = info.get("url", "")

        if not key or not url:
            self.cfg_ai_status.setText("❌ 请填写 API Key")
            self.cfg_ai_status.setStyleSheet(f"font-size:10px; color:{C.danger}; background:transparent;")
            return

        self.cfg_ai_status.setText("⏳ 测试中...")
        self.cfg_ai_status.setStyleSheet(f"font-size:10px; color:{C.warning}; background:transparent;")
        QApplication.processEvents()

        try:
            mr = MarketResearcher({"enabled": True, "provider": prov, "api_key": key, "api_url": url, "model": model})
            result = mr.research("iPhone")
            if result.get("ai_powered"):
                self.cfg_ai_status.setText(f"✅ 连接成功！")
                self.cfg_ai_status.setStyleSheet(f"font-size:10px; color:{C.success}; background:transparent;")
            else:
                self.cfg_ai_status.setText("⚠ 连接成功但降级到本地")
                self.cfg_ai_status.setStyleSheet(f"font-size:10px; color:{C.warning}; background:transparent;")
        except Exception as e:
            self.cfg_ai_status.setText(f"❌ {str(e)[:80]}")
            self.cfg_ai_status.setStyleSheet(f"font-size:10px; color:{C.danger}; background:transparent;")

    def _save_all_settings(self):
        """保存所有设置"""
        self.cfg["anti_ban"]["min_delay"] = self.cfg_min_delay.value()
        self.cfg["anti_ban"]["max_delay"] = self.cfg_max_delay.value()
        self.cfg["anti_ban"]["max_items_per_session"] = self.cfg_max_items.value()
        self.cfg["collection"]["download_images"] = self.cfg_download_img.isChecked()
        self.cfg["xianyu"]["headless"] = self.cfg_headless.isChecked()
        save_user_config(self.cfg)

        # AI 配置
        prov = self.cfg_ai_provider.currentData()
        info = MarketResearcher.API_PROVIDERS.get(prov, {})
        ai_config = {
            "enabled": self.cfg_ai_enabled.isChecked(),
            "provider": prov,
            "api_key": self.cfg_ai_key.text().strip(),
            "api_url": info.get("url", ""),
            "model": self.cfg_ai_model.currentText().strip(),
        }
        mr = MarketResearcher()
        mr.save_config(ai_config)
        self.researcher = MarketResearcher(ai_config)
        self._init_assistant()

        QMessageBox.information(self, "✅ 设置已保存", "所有配置已保存并生效")

    # ===== 导航栏 =====

    def _navbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"background:{C.navbar_bg}; border-bottom:1px solid {C.border};")
        nl = QHBoxLayout(bar)
        nl.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("🐟 闲鱼数据调研工具")
        logo.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        nl.addWidget(logo)
        ver = QLabel("v6.0")
        ver.setStyleSheet(f"font-size:10px; color:{C.primary}; background:{C.primary_bg}; border-radius:4px; padding:2px 8px; margin-left:8px;")
        nl.addWidget(ver)
        nl.addStretch()

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入商品关键词...")
        self.nav_keyword.setFixedWidth(240)
        self.nav_keyword.setFixedHeight(36)
        self.nav_keyword.returnPressed.connect(self._on_start)
        nl.addWidget(self.nav_keyword)

        self.nav_count = NoWheelSpinBox()
        self.nav_count.setRange(5, 100)
        self.nav_count.setValue(30)
        self.nav_count.setSuffix(" 条")
        self.nav_count.setFixedWidth(80)
        self.nav_count.setFixedHeight(36)
        nl.addWidget(self.nav_count)

        research_btn = QPushButton("🔍 AI调研")
        research_btn.setFixedHeight(36)
        research_btn.clicked.connect(self._on_research)
        nl.addWidget(research_btn)

        self.nav_start_btn = QPushButton("🚀 开始采集")
        self.nav_start_btn.setFixedHeight(36)
        self.nav_start_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; border:none; padding:8px 22px; }}
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
        lay.setSpacing(16)
        lay.setContentsMargins(24, 20, 24, 20)

        # 欢迎横幅（可关闭）
        self.welcome_banner = QFrame()
        self.welcome_banner.setFixedHeight(75)
        self.welcome_banner.setStyleSheet(f"""
            QFrame {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {C.primary},stop:1 #F7C948);
                     border-radius:14px; }}
        """)
        bl = QHBoxLayout(self.welcome_banner)
        bl.setContentsMargins(24, 10, 24, 10)
        t1 = QLabel("👋 欢迎使用闲鱼数据调研工具 v6.0")
        t1.setStyleSheet("color:white; font-size:18px; font-weight:bold; border:none; background:transparent;")
        bl.addWidget(t1)
        bl.addStretch()
        lay.addWidget(self.welcome_banner)

        sr = QHBoxLayout()
        sr.setSpacing(12)
        self.card_total = StatCard("📦", "已采集商品", "0")
        sr.addWidget(self.card_total)
        self.card_tasks = StatCard("📋", "采集任务数", "0")
        sr.addWidget(self.card_tasks)
        self.card_avg_price = StatCard("💰", "平均价格", "¥0")
        sr.addWidget(self.card_avg_price)
        self.card_hot_word = StatCard("🔥", "热门关键词", "-")
        sr.addWidget(self.card_hot_word)
        lay.addLayout(sr)

        lay.addWidget(QLabel("⚡ 快捷操作"))
        grid = QGridLayout()
        grid.setSpacing(10)
        ops = [
            ("📥", "导出Excel", "导出采集数据", C.primary, self._on_export_excel),
            ("📊", "文案分析", "高频词报告", C.purple, self._on_analyze),
            ("📂", "数据目录", "打开文件夹", C.info, lambda: os.startfile(self.cfg["paths"]["data_dir"])),
            ("🖼", "图片目录", "已下载图片", C.success, lambda: os.startfile(self.cfg["paths"]["image_dir"])),
            ("📖", "使用帮助", "查看说明", C.cyan, self._on_about),
        ]
        for idx, (ic, ti, de, co, cb) in enumerate(ops):
            card = QuickCard(ic, ti, de, co)
            card.clicked.connect(cb)
            grid.addWidget(card, idx // 3, idx % 3)
        lay.addLayout(grid)

        lay.addWidget(QLabel("📌 最近采集任务"))
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["任务ID", "关键词", "商品数", "状态", "采集时间"])
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.recent_table.setMaximumHeight(180)
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        lay.addWidget(self.recent_table)
        lay.addStretch()
        scroll.setWidget(w)
        return scroll

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

    # ===== 数据预览 =====

    def _data_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 12, 16, 12)

        tb = QHBoxLayout()
        tb.setSpacing(8)
        tb.addWidget(QLabel("📋 任务:"))
        self.data_task_combo = NoWheelComboBox()
        self.data_task_combo.setMinimumWidth(300)
        self.data_task_combo.currentIndexChanged.connect(self._on_task_selected)
        tb.addWidget(self.data_task_combo)
        tb.addStretch()
        for txt, cb in [("📥 导出 Excel", self._on_export_excel), ("📄 CSV", self._on_export_csv),
                         ("📊 分析报告", self._on_analyze), ("🔄 刷新", self._refresh_data_view)]:
            btn = QPushButton(txt)
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
            kw = "全部"
            if task_id:
                task = self.db.get_task(task_id)
                if task: kw = task.get("keyword", "全部")
            p = self.exporter.export_to_excel(task_id=task_id, keyword=kw)
            self._log(f"✅ Excel 导出成功: {p}", "success")
            QMessageBox.information(self, "导出成功", f"<h3>✅ 导出成功</h3><p>{p}</p>")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_export_csv(self):
        try:
            task_id = self.data_task_combo.currentData()
            kw = "全部"
            if task_id:
                task = self.db.get_task(task_id)
                if task: kw = task.get("keyword", "全部")
            p = self.exporter.export_to_csv(task_id=task_id, keyword=kw)
            self._log(f"✅ CSV 导出成功: {p}", "success")
            QMessageBox.information(self, "导出成功", f"<h3>✅ 导出成功</h3><p>{p}</p>")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ===== 文案分析 =====

    def _analysis_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 12, 16, 12)

        tb = QHBoxLayout()
        tb.addStretch()
        ab = QPushButton("🔍 生成分析报告")
        ab.setStyleSheet(f"QPushButton {{ background:{C.purple}; color:white; font-weight:bold; padding:10px 28px; border:none; }} QPushButton:hover {{ background:#5B21B6; }}")
        ab.clicked.connect(self._on_analyze)
        tb.addWidget(ab)
        sb = QPushButton("💾 保存报告")
        sb.clicked.connect(self._save_report)
        tb.addWidget(sb)
        lay.addLayout(tb)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Microsoft YaHei", 11))
        self.analysis_text.setStyleSheet(f"QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; line-height:1.7; }}")
        lay.addWidget(self.analysis_text)
        return w

    def _on_analyze(self):
        try:
            md = self.analyzer.generate_markdown_report(self.data_task_combo.currentData(),
                                                         self.nav_keyword.text().strip() or "全部")
            self.analysis_text.setMarkdown(md)
            self.tab_widget.setCurrentIndex(3)
            self._log("✅ 分析报告生成完成", "success")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._last_report_path = os.path.join(self.cfg["paths"]["export_dir"], f"分析报告_{ts}.md")
            with open(self._last_report_path, "w", encoding="utf-8") as f: f.write(md)
        except Exception as e:
            QMessageBox.critical(self, "分析失败", str(e))

    def _save_report(self):
        if hasattr(self, '_last_report_path'): os.startfile(os.path.dirname(self._last_report_path))
        else: QMessageBox.information(self, "提示", "请先生成分析报告")

    # ===== 运行日志 =====

    def _log_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(6)
        lay.setContentsMargins(16, 12, 16, 12)

        lt = QHBoxLayout()
        self.log_status_label = QLabel("🟢 就绪")
        self.log_status_label.setStyleSheet(f"font-size:12px; color:{C.success}; font-weight:bold; background:transparent;")
        lt.addWidget(self.log_status_label)
        lt.addStretch()
        cb = QPushButton("🗑 清空日志")
        cb.clicked.connect(lambda: self.log_text.clear())
        lt.addWidget(cb)
        lay.addLayout(lt)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(f"QTextEdit {{ background:{C.log_bg}; color:#D4D4D4; border:1px solid #3D3929; border-radius:10px; padding:12px; }}")
        lay.addWidget(self.log_text)
        return w

    # ===== AI 对话 =====

    def _chat_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        ml = QHBoxLayout(w)
        ml.setSpacing(0)
        ml.setContentsMargins(0, 0, 0, 0)

        # 左侧场景面板
        lp = QFrame()
        lp.setFixedWidth(180)
        lp.setStyleSheet(f"background:{C.card}; border-right:1px solid {C.border};")
        ll = QVBoxLayout(lp)
        ll.setContentsMargins(10, 12, 10, 12)

        ll.addWidget(QLabel("📋 场景模板"))
        desc = QLabel("选择一个场景")
        desc.setStyleSheet(f"font-size:11px; color:{C.text_muted}; background:transparent;")
        ll.addWidget(desc)

        from core.assistant import AIAssistant
        self.scene_list = QListWidget()
        for name, info in AIAssistant.SCENARIOS.items():
            item = QListWidgetItem(f"{info['icon']} {name}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.scene_list.addItem(item)
        self.scene_list.clicked.connect(self._on_scene_selected)
        ll.addWidget(self.scene_list)

        clear_btn = QPushButton("🗑 清空对话")
        clear_btn.clicked.connect(self._on_clear_chat)
        ll.addWidget(clear_btn)
        ml.addWidget(lp)

        # 右侧对话区
        rp = QFrame()
        rp.setStyleSheet(f"background:{C.bg};")
        rl = QVBoxLayout(rp)
        rl.setSpacing(8)
        rl.setContentsMargins(14, 10, 14, 10)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Microsoft YaHei", 11))
        self.chat_display.setStyleSheet(f"QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:14px; line-height:1.7; }}")
        self.chat_display.setPlaceholderText("👋 你好！我是闲鱼运营助手。\n\n选择左侧场景模板或直接输入问题开始对话。\n\n我可以帮你：运营策略/文案优化/定价分析/选品建议/客户沟通/数据分析")
        rl.addWidget(self.chat_display)

        ir = QHBoxLayout()
        ir.setSpacing(8)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入问题，如：蓝牙耳机怎么定价？")
        self.chat_input.setFixedHeight(40)
        self.chat_input.returnPressed.connect(self._on_send_message)
        ir.addWidget(self.chat_input)
        send_btn = QPushButton("发送 📤")
        send_btn.setFixedHeight(40)
        send_btn.setStyleSheet(f"QPushButton {{ background:{C.primary}; color:white; font-weight:bold; border:none; }} QPushButton:hover {{ background:{C.primary_hover}; }}")
        send_btn.clicked.connect(self._on_send_message)
        ir.addWidget(send_btn)
        rl.addLayout(ir)

        self.chat_status = QLabel("")
        self.chat_status.setStyleSheet(f"font-size:11px; color:{C.text_muted}; background:transparent;")
        rl.addWidget(self.chat_status)
        ml.addWidget(rp)

        self._init_assistant()
        return w

    def _init_assistant(self):
        self.ai_assistant = AIAssistant(config=self.researcher.config, db=self.db)

    def _on_scene_selected(self):
        item = self.scene_list.currentItem()
        if not item: return
        scene_name = item.data(Qt.ItemDataRole.UserRole)
        kw = self.nav_keyword.text().strip() or ""
        if scene_name == "自由对话":
            self.chat_display.append("\n💡 **自由对话模式**\n")
            return
        self.chat_display.append(f"\n📌 **已选择场景：{scene_name}**\n")
        QApplication.processEvents()
        self.chat_status.setText("⏳ AI 思考中...")
        reply = self.ai_assistant.chat_with_scenario(scene_name, kw)
        if reply:
            self.chat_display.append(f"\n🤖 **AI助手：**\n\n{reply}\n")
        self.chat_status.setText("✅ 就绪")
        self.tab_widget.setCurrentIndex(1)

    def _on_send_message(self):
        msg = self.chat_input.text().strip()
        if not msg: return
        self.chat_input.clear()
        self.chat_display.append(f"\n🧑 **你：** {msg}\n")
        QApplication.processEvents()
        self.chat_status.setText("⏳ AI 思考中...")
        kw = self.nav_keyword.text().strip() or ""
        reply = self.ai_assistant.chat(msg, kw)
        self.chat_display.append(f"🤖 **AI助手：**\n\n{reply}\n")
        self.chat_status.setText("✅ 就绪")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def _on_clear_chat(self):
        self.ai_assistant.clear_history()
        self.chat_display.clear()

    # ===== AI 调研 =====

    def _research_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 12, 16, 12)

        info = QLabel("💡 <b>AI市场调研</b>：输入关键词先分析市场热度、品类、价格区间，确认后再采集。")
        info.setStyleSheet(f"color:{C.text_dim}; font-size:12px; background:{C.primary_bg}; border:1px solid {C.primary}30; border-radius:8px; padding:10px;")
        info.setWordWrap(True)
        lay.addWidget(info)

        ir = QHBoxLayout()
        self.research_keyword = QLineEdit()
        self.research_keyword.setPlaceholderText("输入关键词，如：蓝牙耳机")
        self.research_keyword.setFixedHeight(38)
        self.research_keyword.returnPressed.connect(self._on_research)
        ir.addWidget(self.research_keyword)
        btn = QPushButton("🔍 开始调研")
        btn.setFixedHeight(38)
        btn.setStyleSheet(f"QPushButton {{ background:{C.primary}; color:white; font-weight:bold; border:none; }} QPushButton:hover {{ background:{C.primary_hover}; }}")
        btn.clicked.connect(self._on_research)
        ir.addWidget(btn)
        quick_btn = QPushButton("📊 调研后直接采集")
        quick_btn.setFixedHeight(38)
        quick_btn.setStyleSheet(f"QPushButton {{ background:{C.success}; color:white; font-weight:bold; border:none; }} QPushButton:hover {{ background:#38B820; }}")
        quick_btn.clicked.connect(self._on_research_and_collect)
        ir.addWidget(quick_btn)
        lay.addLayout(ir)

        self.research_text = QTextEdit()
        self.research_text.setReadOnly(True)
        self.research_text.setFont(QFont("Microsoft YaHei", 11))
        self.research_text.setStyleSheet(f"QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; line-height:1.7; }}")
        lay.addWidget(self.research_text)
        return w

    def _on_research(self):
        kw = self.research_keyword.text().strip() or self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return
        self.tab_widget.setCurrentIndex(2)
        self.research_text.setPlainText("🔍 分析中...")
        QApplication.processEvents()
        try:
            md = self.researcher.generate_markdown_report(kw)
            self.research_text.setMarkdown(md)
        except Exception as e:
            self.research_text.setPlainText(f"调研失败: {e}")

    def _on_research_and_collect(self):
        kw = self.research_keyword.text().strip() or self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return
        self._on_research()
        self.nav_keyword.setText(kw)
        if QMessageBox.question(self, "确认采集", f"<h3>调研已生成</h3><p>是否开始采集「{kw}」？</p>") == QMessageBox.StandardButton.Yes:
            self._on_start()

    # ===== 采集事件 =====

    def _on_start(self):
        kw = self.nav_keyword.text().strip()
        if not kw:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        mx = self.nav_count.value()
        di = self.cfg_download_img.isChecked()

        if QMessageBox.question(self, "确认开始采集",
            f"<h3>即将开始采集</h3><p><b>关键词：</b>{kw}<br><b>数量：</b>最多 {mx} 条<br>"
            f"<b>下载图片：</b>{'是' if di else '否'}</p>"
            f"<p style='color:{C.danger};'>⚠ 采集过程会自动打开浏览器<br>⚠ 请扫码登录闲鱼</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return

        self.nav_start_btn.setEnabled(False)
        self.nav_start_btn.setText("⏳ 采集中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, mx)
        self.progress_bar.setValue(0)
        self.log_status_label.setText("🟡 采集中...")
        self.log_status_label.setStyleSheet(f"font-size:12px; color:{C.warning}; font-weight:bold; background:transparent;")
        self.log_text.clear()
        self._log(f"🚀 开始采集：{kw}（目标 {mx} 条）", "info")
        self.tab_widget.setCurrentIndex(4)

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
            self._log(f"🎉 采集任务 #{tid} 完成！", "success")
            self._load_task_history()
            self._refresh_data_view()
            self._refresh_dashboard()
            if QMessageBox.question(self, "采集完成", "<h3>🎉 采集完成！</h3><p>是否立即导出 Excel？</p>") == QMessageBox.StandardButton.Yes:
                self._on_export_excel()
        else:
            self.status_bar.showMessage("⚠ 采集中断或失败")

    def _log(self, msg, lv="info"):
        cols = {"info": "#D4D4D4", "success": "#4EC9B0", "warning": "#CE9178", "error": "#F44747", "debug": "#808080"}
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.setTextColor(QColor(cols.get(lv, "#D4D4D4")))
        self.log_text.insertPlainText(msg + "\n")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def _on_about(self):
        QMessageBox.about(self, "使用说明",
            """<h2 style='color:#F5A623;'>🐟 闲鱼数据调研工具 v6.0</h2>
            <h3>📖 使用步骤</h3><ol>
            <li>左下角配置AI和防封参数</li><li>输入关键词→开始采集</li>
            <li>扫码登录闲鱼→等待采集</li><li>导出Excel或生成文案报告</li></ol>
            <h3>🤖 AI功能</h3><ul>
            <li>AI助手：运营策略/文案优化/定价分析</li>
            <li>AI调研：市场热度/品类分析/采集建议</li></ul>
            <h3>⚠ 注意</h3><ul><li>仅供个人学习研究</li><li>勿用于商业用途</li></ul>""")

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            if QMessageBox.question(self, "确认退出", "采集进行中，确定退出？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.worker.stop(); self.worker.wait(3000); self.db.close(); e.accept()
            else: e.ignore()
        else: self.db.close(); e.accept()
