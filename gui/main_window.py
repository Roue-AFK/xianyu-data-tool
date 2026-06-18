"""
闲鱼数据调研工具 - 主窗口 GUI v7.0
齿轮按钮设置弹窗、右键删除、AI Agent自主操作
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
    QDialog, QDialogButtonBox, QMenu, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction, QWheelEvent, QIcon

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


# ========== 设置弹窗 ==========

class SettingsDialog(QDialog):
    """弹出式设置对话框，齿轮按钮触发"""

    def __init__(self, parent, researcher, cfg):
        super().__init__(parent)
        self.researcher = researcher
        self.cfg = cfg
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        self.setWindowTitle("⚙️ 设置")
        self.setMinimumSize(500, 600)
        self.resize(520, 650)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background:{C.card}; }}
            QLabel {{ color:{C.text}; }}
            QGroupBox {{ font-weight:bold; color:{C.text}; border:1px solid {C.border}; border-radius:10px; margin-top:14px; padding:20px 14px 14px 14px; background:{C.card}; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:14px; padding:0 6px; color:{C.primary}; }}
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
                border:2px solid {C.input_border}; border-radius:8px;
                padding:8px 12px; font-size:13px; background:{C.input_bg}; color:{C.text};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDoubleSpinBox:focus {{ border-color:{C.input_focus}; background:{C.primary_bg}; }}
            QCheckBox {{ color:{C.text}; spacing:8px; }}
            QCheckBox::indicator {{ width:18px; height:18px; border:2px solid {C.border}; border-radius:4px; background:{C.card}; }}
            QCheckBox::indicator:checked {{ background:{C.primary}; border-color:{C.primary}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")

        sw = QWidget()
        sw.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(sw)
        sl.setSpacing(10)
        sl.setContentsMargins(4, 4, 4, 4)

        # === AI 设置 ===
        ai_g = QGroupBox("🤖 AI 配置")
        ai_l = QFormLayout(ai_g)
        ai_l.setSpacing(8)

        self.cfg_ai_provider = NoWheelComboBox()
        for key, info in MarketResearcher.API_PROVIDERS.items():
            self.cfg_ai_provider.addItem(f"{info['name']}", key)
        self.cfg_ai_provider.currentIndexChanged.connect(self._on_cfg_provider_changed)
        ai_l.addRow("提供商:", self.cfg_ai_provider)

        self.cfg_ai_model = NoWheelComboBox()
        self.cfg_ai_model.setEditable(True)
        self.cfg_ai_model.setToolTip("选择或输入模型名称")
        ai_l.addRow("模型:", self.cfg_ai_model)

        self.cfg_ai_enabled = QCheckBox("启用AI助手和调研")
        ai_l.addRow("", self.cfg_ai_enabled)

        self.cfg_ai_key = QLineEdit()
        self.cfg_ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_ai_key.setPlaceholderText("sk-...")
        ai_l.addRow("API Key:", self.cfg_ai_key)

        self.cfg_ai_link = QLabel("")
        self.cfg_ai_link.setOpenExternalLinks(True)
        self.cfg_ai_link.setStyleSheet(f"color:{C.info}; font-size:10px; background:transparent;")
        self.cfg_ai_link.setWordWrap(True)
        ai_l.addRow("", self.cfg_ai_link)

        self.cfg_ai_status = QLabel("")
        self.cfg_ai_status.setStyleSheet("font-size:10px; background:transparent;")
        self.cfg_ai_status.setWordWrap(True)
        ai_l.addRow("", self.cfg_ai_status)

        test_btn = QPushButton("🧪 测试连接")
        test_btn.setStyleSheet(f"QPushButton {{ background:{C.info}; color:white; font-weight:bold; padding:8px; border:none; border-radius:8px; }} QPushButton:hover {{ background:#40A9FF; }}")
        test_btn.clicked.connect(self._on_test_ai)
        ai_l.addRow("", test_btn)

        sl.addWidget(ai_g)

        # === 防封设置 ===
        ab_g = QGroupBox("🛡 防封策略")
        ab_l = QFormLayout(ab_g)
        ab_l.setSpacing(8)

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

        # === 记忆保存路径 ===
        mem_g = QGroupBox("🧠 AI记忆")
        mem_l = QHBoxLayout(mem_g)
        mem_l.setSpacing(8)
        self.cfg_memory_path = QLineEdit()
        self.cfg_memory_path.setPlaceholderText("AI对话记忆保存路径...")
        self.cfg_memory_path.setReadOnly(True)
        mem_l.addWidget(self.cfg_memory_path)
        browse_btn = QPushButton("📂 浏览")
        browse_btn.clicked.connect(self._on_browse_memory_path)
        mem_l.addWidget(browse_btn)
        sl.addWidget(mem_g)

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

        scroll.setWidget(sw)
        layout.addWidget(scroll)

        # 按钮
        btn_box = QDialogButtonBox()
        save_btn = QPushButton("💾 保存设置")
        save_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:white; font-weight:bold; padding:10px 24px; border:none; border-radius:8px; font-size:14px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        save_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(f"QPushButton {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; padding:10px 24px; border-radius:8px; }}")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addButton(save_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(btn_box)

    def _on_cfg_provider_changed(self, idx):
        key = self.cfg_ai_provider.itemData(idx)
        if not key: return
        info = MarketResearcher.API_PROVIDERS.get(key, {})

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

    def _on_browse_memory_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择AI记忆保存目录")
        if path:
            self.cfg_memory_path.setText(path)

    def _load_settings(self):
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

        # 记忆路径
        mem_path = self.cfg.get("ui", {}).get("memory_path", os.path.join(self.cfg["paths"]["data_dir"], "ai_memory"))
        self.cfg_memory_path.setText(mem_path)

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

    def _save_and_close(self):
        """保存设置到父窗口"""
        parent = self.parent()
        if not isinstance(parent, MainWindow):
            self.accept()
            return

        parent.cfg["anti_ban"]["min_delay"] = self.cfg_min_delay.value()
        parent.cfg["anti_ban"]["max_delay"] = self.cfg_max_delay.value()
        parent.cfg["anti_ban"]["max_items_per_session"] = self.cfg_max_items.value()
        parent.cfg["collection"]["download_images"] = self.cfg_download_img.isChecked()
        parent.cfg["xianyu"]["headless"] = self.cfg_headless.isChecked()
        if "ui" not in parent.cfg:
            parent.cfg["ui"] = {}
        parent.cfg["ui"]["memory_path"] = self.cfg_memory_path.text().strip()
        parent.cfg["ui"]["show_welcome"] = self.cfg_show_welcome.isChecked()
        save_user_config(parent.cfg)

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
        parent.researcher = MarketResearcher(ai_config)
        parent._init_assistant()

        # 更新AI记忆路径
        mem_path = self.cfg_memory_path.text().strip()
        if mem_path and hasattr(parent, 'ai_assistant'):
            parent.ai_assistant.set_memory_path(mem_path)

        # 更新欢迎横幅
        if hasattr(parent, 'welcome_banner'):
            parent.welcome_banner.setVisible(self.cfg_show_welcome.isChecked())

        QMessageBox.information(self, "✅ 设置已保存", "所有配置已保存并生效")
        self.accept()


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
        self.setWindowTitle("🐟 闲鱼数据调研工具 v7.0")
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
            QMenu {{ background:{C.card}; border:1px solid {C.border}; border-radius:8px; padding:4px; }}
            QMenu::item {{ padding:8px 28px; border-radius:4px; }}
            QMenu::item:selected {{ background:{C.primary_bg}; color:{C.primary}; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._navbar(main_layout)

        # 标签页区域（不再有左下设置面板）
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.addTab(self._dashboard(), "🏠 仪表盘")
        self.tab_widget.addTab(self._chat_tab(), "💬 AI助手")
        self.tab_widget.addTab(self._research_tab(), "🔍 AI调研")
        self.tab_widget.addTab(self._data_tab(), "📊 数据预览")
        self.tab_widget.addTab(self._analysis_tab(), "📈 文案分析")
        self.tab_widget.addTab(self._log_tab(), "📋 运行日志")
        main_layout.addWidget(self.tab_widget)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("🟢 就绪")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.status_bar.addPermanentWidget(self.progress_bar)

    # ===== 导航栏 =====

    def _navbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"background:{C.navbar_bg}; border-bottom:1px solid {C.border};")
        nl = QHBoxLayout(bar)
        nl.setContentsMargins(20, 0, 12, 0)

        logo = QLabel("🐟 闲鱼数据调研工具")
        logo.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        nl.addWidget(logo)
        ver = QLabel("v7.0")
        ver.setStyleSheet(f"font-size:10px; color:{C.primary}; background:{C.primary_bg}; border-radius:4px; padding:2px 8px; margin-left:8px;")
        nl.addWidget(ver)
        nl.addStretch()

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入商品关键词...")
        self.nav_keyword.setFixedWidth(240)
        self.nav_keyword.setFixedHeight(36)
        self.nav_keyword.returnPressed.connect(self._on_start)
        nl.addWidget(self.nav_keyword)

        count_label = QLabel("数量")
        count_label.setStyleSheet(f"color:{C.text_dim}; font-size:11px; border:none; background:transparent; margin-right:2px;")
        nl.addWidget(count_label)
        self.nav_count = QLineEdit("30")
        self.nav_count.setPlaceholderText("条数")
        self.nav_count.setFixedWidth(52)
        self.nav_count.setFixedHeight(36)
        self.nav_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        # 齿轮设置按钮 - 放在导航栏最右侧
        gear_btn = QPushButton("⚙️")
        gear_btn.setFixedSize(38, 38)
        gear_btn.setToolTip("打开设置面板")
        gear_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:1px solid {C.border}; border-radius:19px; font-size:20px; padding:0; }}
            QPushButton:hover {{ background:{C.primary_bg}; border-color:{C.primary}; }}
        """)
        gear_btn.clicked.connect(self._on_open_settings)
        nl.addWidget(gear_btn)
        parent.addWidget(bar)

    def _on_open_settings(self):
        """打开设置弹窗"""
        dlg = SettingsDialog(self, self.researcher, self.cfg)
        dlg.exec()

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
        t1 = QLabel("👋 欢迎使用闲鱼数据调研工具 v7.0")
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
        self.card_avg_price = StatCard("💰", "平均价格(按类型)", "¥0")
        self.card_avg_price.setToolTip("鼠标悬停查看各类型均价")
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
        self.recent_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_table.customContextMenuRequested.connect(self._on_task_table_context_menu)
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
            # 按关键词分类计算平均价格
            keyword_prices = {}  # {keyword: [price1, price2, ...]}
            for t in tasks:
                if t.get("status") != "finished":
                    continue
                kw = t.get("keyword", "")
                if not kw:
                    continue
                stats = self.db.get_price_stats(t["id"])
                avg = stats.get("avg_price", 0) or 0
                cnt = stats.get("count", 0) or 0
                if cnt > 0 and avg > 0:
                    keyword_prices[kw] = (avg, cnt)

            if keyword_prices:
                # 显示第一个关键词的均价，多关键词时显示"按类型"
                top_kw = max(keyword_prices, key=lambda k: keyword_prices[k][1])
                top_avg = keyword_prices[top_kw][0]
                if len(keyword_prices) == 1:
                    self.card_avg_price.value_label.setText(f"¥{top_avg:.0f}")
                else:
                    self.card_avg_price.value_label.setText(f"¥{top_avg:.0f}")
                    self.card_avg_price.setToolTip(
                        "\n".join([f"{kw}: ¥{v[0]:.0f} ({v[1]}条)" for kw, v in sorted(keyword_prices.items(), key=lambda x: -x[1][1])])
                    )
            else:
                self.card_avg_price.value_label.setText("¥0")

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

    # ===== 右键菜单 =====

    def _on_task_table_context_menu(self, pos: QPoint):
        """最近任务表右键菜单"""
        row = self.recent_table.rowAt(pos.y())
        if row < 0: return
        item = self.recent_table.item(row, 0)
        if not item: return
        task_id_text = item.text()
        try:
            task_id = int(task_id_text.replace("#", ""))
        except ValueError:
            return

        menu = QMenu(self)
        del_action = menu.addAction("🗑 删除此任务及数据")
        menu.addSeparator()
        export_action = menu.addAction("📥 导出此任务Excel")
        action = menu.exec(self.recent_table.viewport().mapToGlobal(pos))

        if action == del_action:
            reply = QMessageBox.question(self, "确认删除",
                f"<h3>⚠ 确认删除</h3><p>将删除任务 #{task_id} 及其所有采集数据。</p><p style='color:{C.danger};'>此操作不可恢复！</p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_task(task_id)
                self._load_task_history()
                self._refresh_dashboard()
                self._refresh_data_view()
                self._log(f"🗑 已删除任务 #{task_id} 及其数据", "warning")
        elif action == export_action:
            self.current_task_id = task_id
            self._on_export_excel()

    def _on_data_table_context_menu(self, pos: QPoint):
        """数据预览表右键菜单"""
        row = self.data_table.rowAt(pos.y())
        if row < 0: return
        item = self.data_table.item(row, 0)
        if not item: return

        # 获取该行的item ID（通过数据库查询）
        items = self.db.get_items(task_id=self.data_task_combo.currentData(), limit=200)
        if row >= len(items): return
        item_data = items[row]

        menu = QMenu(self)
        del_action = menu.addAction("🗑 删除此条记录")
        copy_action = menu.addAction("📋 复制标题")
        open_action = menu.addAction("🔗 打开商品链接")
        action = menu.exec(self.data_table.viewport().mapToGlobal(pos))

        if action == del_action:
            reply = QMessageBox.question(self, "确认删除",
                f"<h3>⚠ 确认删除</h3><p>将删除商品「{item_data.get('title','')[:30]}」？</p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_item(item_data["id"])
                self._refresh_data_view()
                self._refresh_dashboard()
                self._log(f"🗑 已删除记录: {item_data.get('title','')[:30]}", "warning")
        elif action == copy_action:
            QApplication.clipboard().setText(item_data.get("title", ""))
            self.status_bar.showMessage("📋 标题已复制到剪贴板")
        elif action == open_action:
            url = item_data.get("item_url", "")
            if url:
                import webbrowser
                webbrowser.open(url)

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
        self.data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._on_data_table_context_menu)
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
            self.tab_widget.setCurrentIndex(4)
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

    # ===== AI 对话（v8.0 重构：自由对话为主，模板选择为辅助）=====

    def _chat_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        vl = QVBoxLayout(w)
        vl.setSpacing(6)
        vl.setContentsMargins(14, 8, 14, 8)

        # 顶部：模板选择栏（紧凑一行）
        top_bar = QFrame()
        top_bar.setStyleSheet(f"background:{C.card}; border:1px solid {C.border}; border-radius:10px;")
        top_bar.setFixedHeight(44)
        tbh = QHBoxLayout(top_bar)
        tbh.setContentsMargins(14, 0, 10, 0)
        tbh.setSpacing(8)

        tbh.addWidget(QLabel("📋 模板"))
        self.chat_scene_combo = NoWheelComboBox()
        self.chat_scene_combo.setFixedWidth(140)
        self.chat_scene_combo.setFixedHeight(30)
        self.chat_scene_combo.addItem("💡 自由对话", "自由对话")
        self.chat_scene_combo.currentIndexChanged.connect(self._on_chat_scene_changed)
        tbh.addWidget(self.chat_scene_combo)

        tbh.addSpacing(4)

        tbh.addWidget(QLabel("类型"))
        self.chat_type_combo = NoWheelComboBox()
        self.chat_type_combo.setFixedWidth(140)
        self.chat_type_combo.setFixedHeight(30)
        tbh.addWidget(self.chat_type_combo)

        self.chat_template_btn = QPushButton("▶ 使用模板")
        self.chat_template_btn.setFixedHeight(30)
        self.chat_template_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.purple}; color:white; font-weight:bold; border:none; padding:4px 14px; font-size:11px; }}
            QPushButton:hover {{ background:#5B21B6; }}
        """)
        self.chat_template_btn.clicked.connect(self._on_use_template)
        tbh.addWidget(self.chat_template_btn)

        tbh.addStretch()
        clear_btn = QPushButton("🗑 清空")
        clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._on_clear_chat)
        tbh.addWidget(clear_btn)

        vl.addWidget(top_bar)

        # 主对话区（大面积）
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Microsoft YaHei", 11))
        self.chat_display.setStyleSheet(f"QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; line-height:1.7; }}")
        self.chat_display.setPlaceholderText(
            "👋 你好！我是闲鱼运营助手，直接输入问题开始对话。\n\n"
            "💬 自由对话：输入任何问题，我会帮你解答\n"
            "📋 模板对话：顶部选择场景和类型，点击「使用模板」一键生成\n\n"
            "我可以帮你：\n"
            "• 运营策略 / 文案优化 / 定价分析 / 选品建议 / 客户沟通\n"
            "• 数据概览 / 价格分析 / 标题趋势 / 搜索建议\n"
            "• 触发采集 / 导出数据 / 生成报告 / 市场调研"
        )
        vl.addWidget(self.chat_display)

        # 底部输入栏
        ir = QHBoxLayout()
        ir.setSpacing(8)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入问题，如：蓝牙耳机怎么定价？或：帮我采集蓝牙耳机")
        self.chat_input.setFixedHeight(42)
        self.chat_input.returnPressed.connect(self._on_send_message)
        ir.addWidget(self.chat_input)
        send_btn = QPushButton("发送 📤")
        send_btn.setFixedHeight(42)
        send_btn.setFixedWidth(90)
        send_btn.setStyleSheet(f"QPushButton {{ background:{C.primary}; color:white; font-weight:bold; border:none; }} QPushButton:hover {{ background:{C.primary_hover}; }}")
        send_btn.clicked.connect(self._on_send_message)
        ir.addWidget(send_btn)
        vl.addLayout(ir)

        self.chat_status = QLabel("")
        self.chat_status.setStyleSheet(f"font-size:11px; color:{C.text_muted}; background:transparent;")
        vl.addWidget(self.chat_status)

        self._init_assistant()
        self._populate_chat_scenes()
        return w

    def _populate_chat_scenes(self):
        """填充场景和类型下拉框"""
        # 场景下拉已包含"自由对话"
        for name, info in AIAssistant.SCENARIOS.items():
            if name != "自由对话":
                self.chat_scene_combo.addItem(f"{info['icon']} {name}", name)
        # 默认选自由对话，类型下拉隐藏
        self._on_chat_scene_changed(0)

    def _on_chat_scene_changed(self, idx):
        """场景切换时更新类型下拉框"""
        scene_name = self.chat_scene_combo.currentData()
        self.chat_type_combo.clear()
        if scene_name == "自由对话":
            self.chat_type_combo.setVisible(False)
            self.chat_template_btn.setVisible(False)
            return
        self.chat_type_combo.setVisible(True)
        self.chat_template_btn.setVisible(True)
        # 根据场景给出类型选项
        type_options = {
            "运营策略": ["完整策略方案", "账号定位建议", "提升曝光技巧", "发布时间策略"],
            "文案优化": ["5种风格标题", "真诚实惠型", "专业测评型", "急售捡漏型", "故事营销型", "简单直接型"],
            "定价分析": ["行情价格分析", "定价策略建议", "价格谈判技巧", "降价涨价时机"],
            "选品建议": ["竞争分析", "细分品类推荐", "货源渠道建议", "利润空间分析"],
            "客户沟通": ["回复话术模板", "砍价应对技巧", "售后纠纷处理", "好评引导技巧"],
        }
        for opt in type_options.get(scene_name, ["默认"]):
            self.chat_type_combo.addItem(opt, opt)
        # 确保可见
        self.chat_type_combo.show()
        self.chat_template_btn.show()

    def _on_use_template(self):
        """使用模板发起对话"""
        scene_name = self.chat_scene_combo.currentData()
        type_name = self.chat_type_combo.currentData() if self.chat_type_combo.currentData() else ""
        kw = self.nav_keyword.text().strip() or ""
        if not kw:
            kw = self.chat_input.text().strip()

        if scene_name == "自由对话":
            return

        self.chat_display.append(f"\n📌 **{scene_name}** → {type_name}\n")
        QApplication.processEvents()
        self.chat_status.setText("⏳ AI 思考中...")

        # 根据类型构建更精准的prompt
        prompt = self._build_template_prompt(scene_name, type_name, kw)
        reply = self.ai_assistant.chat(prompt, kw)
        if reply:
            self.chat_display.append(f"🤖 **AI助手：**\n\n{reply}\n")
        self.chat_status.setText("✅ 就绪")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def _build_template_prompt(self, scene_name, type_name, keyword):
        """根据场景+类型构建精准prompt"""
        base = AIAssistant.SCENARIOS.get(scene_name, {}).get("prompt", "")
        if not base:
            return f"请针对「{keyword}」提供{type_name}方面的建议。"

        # 如果用户选了具体类型，在prompt后追加聚焦指令
        focus_map = {
            "完整策略方案": "\n请给出完整全面的策略，覆盖所有要点。",
            "账号定位建议": "\n请重点展开第1点：账号定位和人设打造。",
            "提升曝光技巧": "\n请重点展开第6点：如何提升曝光和转化。",
            "发布时间策略": "\n请重点展开第5点：发布时间和频率。",
            "5种风格标题": "",
            "真诚实惠型": "\n请只写真诚实惠型风格，写3个完整标题+描述。",
            "专业测评型": "\n请只写专业测评型风格，写3个完整标题+描述。",
            "急售捡漏型": "\n请只写急售捡漏型风格，写3个完整标题+描述。",
            "故事营销型": "\n请只写故事营销型风格，写3个完整标题+描述。",
            "简单直接型": "\n请只写简单直接型风格，写3个完整标题+描述。",
            "行情价格分析": "\n请重点展开第1-2点：行情价格区间和影响因素。",
            "定价策略建议": "\n请重点展开第3点：如何根据成色/配件/保修定价。",
            "价格谈判技巧": "\n请重点展开第4点：价格谈判技巧。",
            "降价涨价时机": "\n请重点展开第5点：什么时候适合降价/涨价。",
            "竞争分析": "\n请重点展开第1点：品类竞争情况。",
            "细分品类推荐": "\n请重点展开第2点：哪些细分品类更值得做。",
            "货源渠道建议": "\n请重点展开第3点：货源渠道建议。",
            "利润空间分析": "\n请重点展开第4点：利润空间分析。",
            "回复话术模板": "\n请重点展开第1点：常见客户问题及标准回复话术。",
            "砍价应对技巧": "\n请重点展开第2点：如何应对砍价。",
            "售后纠纷处理": "\n请重点展开第3点：如何处理售后纠纷。",
            "好评引导技巧": "\n请重点展开第4点：如何引导好评。",
        }
        extra = focus_map.get(type_name, "")
        return base.format(keyword=keyword) if keyword else base + extra

    def _init_assistant(self):
        """初始化AI助手并加载记忆"""
        mem_path = self.cfg.get("ui", {}).get("memory_path",
                    os.path.join(self.cfg["paths"]["data_dir"], "ai_memory"))
        self.ai_assistant = AIAssistant(config=self.researcher.config, db=self.db,
                                         memory_path=mem_path, main_window=self)
        self.ai_assistant.load_memory()

    def _on_send_message(self):
        msg = self.chat_input.text().strip()
        if not msg: return
        self.chat_input.clear()
        self.chat_display.append(f"\n🧑 **你：** {msg}\n")
        QApplication.processEvents()
        self.chat_status.setText("⏳ AI 思考中...")
        kw = self.nav_keyword.text().strip() or ""

        # 先让AI问问题明确需求（如果需要）
        need_clarify = self.ai_assistant.check_if_need_clarify(msg)
        if need_clarify:
            self.chat_display.append(f"🤖 **AI助手：**\n\n{need_clarify}\n")
            self.chat_status.setText("✅ 就绪（等待你的回复）")
            self.chat_display.moveCursor(QTextCursor.MoveOperation.End)
            return

        reply = self.ai_assistant.chat(msg, kw)
        self.chat_display.append(f"🤖 **AI助手：**\n\n{reply}\n")
        self.chat_status.setText("✅ 就绪")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    def _on_clear_chat(self):
        reply = QMessageBox.question(self, "确认清空",
            "<h3>清空对话</h3><p>是否同时清除AI记忆？</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Cancel:
            return
        if reply == QMessageBox.StandardButton.Yes:
            self.ai_assistant.clear_memory()
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
        try:
            mx = int(self.nav_count.text().strip() or "30")
        except ValueError:
            mx = 30
        di = self.cfg["collection"]["download_images"]

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
        self.tab_widget.setCurrentIndex(5)

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
            """<h2 style='color:#F5A623;'>🐟 闲鱼数据调研工具 v7.0</h2>
            <h3>📖 使用步骤</h3><ol>
            <li>点击导航栏⚙️配置AI和防封参数</li><li>输入关键词→开始采集</li>
            <li>扫码登录闲鱼→等待采集</li><li>导出Excel或生成文案报告</li></ol>
            <h3>🤖 AI功能</h3><ul>
            <li>AI助手：运营策略/文案优化/定价分析</li>
            <li>AI调研：市场热度/品类分析/采集建议</li>
            <li>AI Agent：可自主操作采集/导出/分析</li></ul>
            <h3>⚠ 注意</h3><ul><li>仅供个人学习研究</li><li>勿用于商业用途</li></ul>""")

    def closeEvent(self, e):
        if hasattr(self, 'ai_assistant') and self.ai_assistant:
            self.ai_assistant.save_memory()
        if self.worker and self.worker.isRunning():
            if QMessageBox.question(self, "确认退出", "采集进行中，确定退出？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.worker.stop(); self.worker.wait(3000); self.db.close(); e.accept()
            else: e.ignore()
        else: self.db.close(); e.accept()
