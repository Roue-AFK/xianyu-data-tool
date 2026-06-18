"""
多平台数据调研集合站 - 主窗口 v15.0
闲鱼 + 抖音 + 小红书 三平台数据调研工具
左侧平台导航 + 标签页工作区 + AI深度集成
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
    QDialog, QDialogButtonBox, QMenu, QFileDialog, QScrollBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QPauseAnimation, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QAction, QWheelEvent, QIcon, QPainter, QBrush, QPen, QLinearGradient, QTextDocument

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter
from core.researcher import MarketResearcher
from core.assistant import AIAssistant


# ========== 配色系统 v15.0 (Slate Professional + 暖橙) ==========

class C:
    """全局配色 - 默认暗色主题 (Slate Professional)"""

    # 核心背景
    bg              = "#0F172A"  # 午夜板岩 - 主背景
    sidebar         = "#0C1422"  # 侧边栏更深
    card            = "#1E293B"  # 卡片/面板
    card_hover      = "#273449"  # 卡片悬停
    border          = "#334155"  # 边框
    border_hover    = "#475569"  # 边框悬停

    # 文字
    text            = "#F1F5F9"  # 主文字 - 亮白
    text_dim        = "#94A3B8"  # 次要文字 - 灰蓝
    text_muted      = "#64748B"  # 禁用文字 - 暗灰

    # 强调色（暖橙系 - 闲鱼品牌关联）
    primary         = "#F59E0B"  # 暖橙
    primary_hover   = "#FBBF24"  # 暖橙悬停
    primary_bg      = "#F59E0B18" # 暖橙背景

    # 平台色
    xianyu_color    = "#F59E0B"  # 闲鱼橙
    douyin_color    = "#111111"  # 抖音黑(用亮色替代)
    douyin_accent   = "#FE2C55"  # 抖音红
    xiaohongshu     = "#FE2C55"  # 小红书红

    # 功能色
    success         = "#10B981"  # 翡翠绿
    warning         = "#F59E0B"  # 琥珀色
    danger          = "#EF4444"  # 红色
    info            = "#38BDF8"  # 天空蓝
    info_bg         = "#38BDF818"

    # 特殊色
    purple          = "#A78BFA"  # 紫色
    cyan            = "#22D3EE"  # 青色
    white           = "#F1F5F9"

    # 输入框
    input_bg        = "#1E293B"
    input_border    = "#334155"
    input_focus     = "#F59E0B"

    # 表格
    table_header    = "#1E293B"
    table_row_alt   = "#1A2538"

    # 日志
    log_bg          = "#0C1422"

    # 滚动条
    scrollbar       = "#334155"
    scrollbar_hover = "#475569"

    # 导航
    navbar_bg       = "#1E293B"
    stat_value      = "#F1F5F9"
    panel_bg        = "#1E293B"

    # 侧边栏导航专用
    nav_item        = "#94A3B8"
    nav_item_active = "#F59E0B"
    nav_item_bg     = "transparent"
    nav_item_bg_active = "#F59E0B15"
    nav_section     = "#64748B"

    # 消息气泡
    bubble_user     = "#F59E0B20"
    bubble_ai       = "#1E293B"
    bubble_border   = "#334155"


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


# ========== AI状态指示器 / 加载动画 ==========

class TypingIndicator(QWidget):
    """Codex风格跳动点动画 — 3个渐显渐隐的圆点"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 14)
        self._opacity = [0.3, 0.3, 0.3]
        self._target = [0.3, 0.3, 0.3]
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._phase = 0
        self._timer.start(80)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        import math
        t = self._phase * 0.15
        for i in range(3):
            offset = i * 2.1
            v = (math.sin(t + offset) + 1) / 2
            self._opacity[i] = 0.2 + v * 0.8
        self._phase += 1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        for i in range(3):
            alpha = int(self._opacity[i] * 255)
            p.setBrush(QBrush(QColor(C.primary).darker(120 - i * 30)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setOpacity(self._opacity[i])
            p.drawEllipse(cx - 18 + i * 14, cy - 4, 8, 8)
        p.end()


class StatusBadge(QFrame):
    """AI状态徽章 — 带颜色指示点 + 文字"""
    def __init__(self, text="就绪", color=C.success):
        super().__init__()
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 1, 10, 1)
        layout.setSpacing(4)
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{color}; font-size:10px; border:none; background:transparent;")
        layout.addWidget(self._dot)
        self._label = QLabel(text)
        self._label.setStyleSheet(f"font-size:11px; color:{C.text}; border:none; background:transparent;")
        layout.addWidget(self._label)
        self.setStyleSheet(f"""
            StatusBadge {{ background:{C.card}; border:1px solid {C.border}; border-radius:13px; }}
            StatusBadge:hover {{ border-color:{C.primary}60; }}
        """)

    def set_state(self, text, color):
        self._label.setText(text)
        self._dot.setStyleSheet(f"color:{color}; font-size:10px; border:none; background:transparent;")


# ========== 流式AI线程 ==========

class StreamWorker(QThread):
    """流式AI调用线程，逐字返回"""
    chunk_signal = pyqtSignal(str)    # 每次返回当前累积文本
    done_signal = pyqtSignal(str)     # 完成时返回完整文本
    error_signal = pyqtSignal(str)

    def __init__(self, assistant, message, keyword=""):
        super().__init__()
        self.assistant = assistant
        self.message = message
        self.keyword = keyword

    def run(self):
        try:
            for text in self.assistant.chat_stream(self.message, self.keyword):
                if self.isInterruptionRequested():
                    self.done_signal.emit(text)
                    return
                self.chunk_signal.emit(text)
            self.done_signal.emit(text if 'text' in dir() else "")
        except Exception as e:
            self.error_signal.emit(str(e))


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
        update_btn = QPushButton("🔄 检查更新")
        update_btn.setStyleSheet(f"QPushButton {{ background:{C.info_bg}; color:{C.info}; font-weight:bold; border:1px solid {C.info}40; padding:10px 20px; border-radius:8px; }} QPushButton:hover {{ background:{C.info}20; }}")
        update_btn.clicked.connect(self._on_check_update)
        btn_box.addButton(update_btn, QDialogButtonBox.ButtonRole.ActionRole)
        btn_box.addButton(save_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(btn_box)

    def _on_check_update(self):
        """检查GitHub更新"""
        import subprocess, os
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            result = subprocess.run(
                "git fetch origin && git reset --hard origin/master",
                shell=True, cwd=project_dir, capture_output=True, timeout=30
            )
            out = result.stdout.decode("utf-8", errors="replace").strip()
            err = result.stderr.decode("utf-8", errors="replace").strip()
            if result.returncode == 0:
                QMessageBox.information(self, "✅ 更新完成",
                    f"代码已同步到最新版本！\n\n{out or '已是最新版本'}\n\n请重启应用以生效。")
            else:
                QMessageBox.warning(self, "⚠ 更新失败",
                    f"Git 操作失败：\n{err}")
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "⚠ 更新超时", "网络连接超时，请检查网络后重试。")
        except Exception as e:
            QMessageBox.warning(self, "⚠ 更新失败", f"发生错误：{e}")

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


# ========== 主窗口 v15.0 ==========

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
        self.current_platform = "xianyu"  # 当前激活的平台
        self._init_ui()
        self._load_task_history()
        # _refresh_dashboard 在 _build_platform_tabs 内部调用

    def _init_ui(self):
        self.setWindowTitle("DataResearch Hub - 多平台数据调研集合站")
        self.setMinimumSize(1280, 820)
        self.resize(1440, 920)

        # 全局样式
        self.setStyleSheet(f"""
            QMainWindow {{ background:{C.bg}; }}
            QTabWidget::pane {{ border:none; background:{C.bg}; }}
            QTabBar::tab {{
                background:{C.card}; color:{C.text_dim}; padding:8px 18px;
                font-size:12px; border:1px solid {C.border}; border-bottom:none;
                border-top-left-radius:6px; border-top-right-radius:6px; margin-right:2px;
            }}
            QTabBar::tab:selected {{ background:{C.bg}; color:{C.primary}; font-weight:bold; border-bottom:2px solid {C.primary}; }}
            QTabBar::tab:hover:!selected {{ background:{C.card_hover}; color:{C.text}; }}
            QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {{
                border:1px solid {C.input_border}; border-radius:6px;
                padding:8px 12px; font-size:13px; background:{C.input_bg}; color:{C.text};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color:{C.input_focus}; }}
            QLineEdit::placeholder {{ color:{C.text_muted}; }}
            QComboBox::drop-down {{ border:none; padding-right:8px; }}
            QComboBox QAbstractItemView {{
                background:{C.card}; color:{C.text}; border:1px solid {C.border};
                selection-background-color:{C.primary_bg};
            }}
            QPushButton {{ border-radius:6px; padding:6px 16px; font-size:12px; color:{C.text}; background:{C.card}; border:1px solid {C.border}; }}
            QPushButton:hover {{ background:{C.card_hover}; border-color:{C.primary}; }}
            QTableWidget {{ gridline-color:{C.border}; font-size:12px; border:1px solid {C.border}; border-radius:8px; background:{C.card}; color:{C.text}; alternate-background-color:{C.table_row_alt}; }}
            QTableWidget::item {{ padding:6px; border-bottom:1px solid {C.border}; }}
            QTableWidget::item:selected {{ background:{C.primary_bg}; color:{C.text}; }}
            QHeaderView::section {{ background:{C.table_header}; border:none; border-bottom:2px solid {C.border}; padding:8px 6px; font-weight:bold; color:{C.text_dim}; }}
            QProgressBar {{ border:none; border-radius:8px; background:{C.border}; height:4px; }}
            QProgressBar::chunk {{ border-radius:8px; background:{C.primary}; }}
            QScrollArea {{ border:none; background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:6px; }}
            QScrollBar::handle:vertical {{ background:{C.scrollbar}; border-radius:3px; min-height:30px; }}
            QScrollBar::handle:vertical:hover {{ background:{C.scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QGroupBox {{ font-weight:bold; color:{C.text}; border:1px solid {C.border}; border-radius:8px; margin-top:12px; padding:16px 12px 12px 12px; background:{C.card}; }}
            QGroupBox::title {{ subcontrol-origin:margin; left:12px; padding:0 4px; color:{C.primary}; }}
            QCheckBox {{ color:{C.text}; spacing:6px; }}
            QCheckBox::indicator {{ width:16px; height:16px; border:2px solid {C.border}; border-radius:3px; background:{C.card}; }}
            QCheckBox::indicator:checked {{ background:{C.primary}; border-color:{C.primary}; }}
            QLabel {{ color:{C.text}; }}
            QStatusBar {{ background:{C.sidebar}; border-top:1px solid {C.border}; padding:2px 12px; font-size:11px; color:{C.text_dim}; }}
            QListWidget {{ background:transparent; border:none; }}
            QListWidget::item {{ padding:8px 10px; border-radius:6px; margin:1px 0; color:{C.text}; }}
            QListWidget::item:hover {{ background:{C.primary_bg}; }}
            QListWidget::item:selected {{ background:{C.primary_bg}; color:{C.primary}; font-weight:bold; }}
            QMenu {{ background:{C.card}; border:1px solid {C.border}; border-radius:8px; padding:4px; }}
            QMenu::item {{ padding:8px 24px; border-radius:4px; color:{C.text}; }}
            QMenu::item:selected {{ background:{C.primary_bg}; color:{C.primary}; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ═══════ 左侧平台导航 ═══════
        self._build_sidebar(main_layout)

        # ═══════ 右侧主内容区 ═══════
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background:{C.bg};")
        rl = QVBoxLayout(right_panel)
        rl.setSpacing(0)
        rl.setContentsMargins(0, 0, 0, 0)

        # 顶部快捷操作栏
        self._build_topbar(rl)

        # 标签页工作区
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self._build_platform_tabs()
        rl.addWidget(self.tab_widget)

        # 底部状态栏
        self._build_statusbar(rl)

        main_layout.addWidget(right_panel)

    # ═══════ 左侧侧边栏 ═══════
    def _build_sidebar(self, parent):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background:{C.sidebar};
                border-right:1px solid {C.border};
            }}
        """)
        sl = QVBoxLayout(sidebar)
        sl.setSpacing(0)
        sl.setContentsMargins(0, 0, 0, 0)

        # Logo区域
        logo_area = QFrame()
        logo_area.setFixedHeight(56)
        logo_area.setStyleSheet(f"background:transparent; border-bottom:1px solid {C.border};")
        ll = QHBoxLayout(logo_area)
        ll.setContentsMargins(16, 0, 12, 0)
        logo = QLabel("🔬 DataResearch")
        logo.setStyleSheet(f"font-size:14px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        ll.addWidget(logo)
        ll.addStretch()
        ver = QLabel("v15")
        ver.setStyleSheet(f"font-size:9px; color:{C.primary}; background:{C.primary_bg}; border-radius:3px; padding:1px 5px;")
        ll.addWidget(ver)
        sl.addWidget(logo_area)

        # 平台导航列表
        self.platform_list = QListWidget()
        self.platform_list.setObjectName("platformNav")
        self.platform_list.setStyleSheet(f"""
            QListWidget#platformNav {{
                background:transparent; border:none; padding:8px 8px;
            }}
            QListWidget#platformNav::item {{
                padding:10px 12px; border-radius:8px; margin:2px 0;
                color:{C.nav_item}; font-size:13px; font-weight:500;
            }}
            QListWidget#platformNav::item:hover {{
                background:{C.card_hover}; color:{C.text};
            }}
            QListWidget#platformNav::item:selected {{
                background:{C.nav_item_bg_active}; color:{C.nav_item_active};
                font-weight:bold; border-left:3px solid {C.nav_item_active};
            }}
        """)

        platforms = [
            ("🐟 闲鱼", "xianyu"),
            ("🎵 抖音", "douyin"),
            ("📕 小红书", "xiaohongshu"),
        ]
        self._platform_items = {}
        for icon_text, key in platforms:
            item = QListWidgetItem(icon_text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.platform_list.addItem(item)
            self._platform_items[key] = item

        self.platform_list.setCurrentRow(0)
        self.platform_list.currentRowChanged.connect(self._on_platform_switch)
        sl.addWidget(self.platform_list)

        # 平台子菜单
        self.platform_sub_list = QListWidget()
        self.platform_sub_list.setObjectName("platformSub")
        self.platform_sub_list.setStyleSheet(f"""
            QListWidget#platformSub {{
                background:transparent; border:none; padding:4px 8px 4px 20px;
            }}
            QListWidget#platformSub::item {{
                padding:7px 10px; border-radius:6px; margin:1px 0;
                color:{C.text_dim}; font-size:11px;
            }}
            QListWidget#platformSub::item:hover {{
                background:{C.card_hover}; color:{C.text};
            }}
            QListWidget#platformSub::item:selected {{
                background:{C.nav_item_bg_active}; color:{C.nav_item_active};
                font-weight:bold;
            }}
        """)
        self.platform_sub_list.currentRowChanged.connect(self._on_sub_nav)
        sl.addWidget(self.platform_sub_list)

        sl.addStretch()

        # 底部设置按钮
        settings_btn = QPushButton("⚙️  设置")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{C.text_dim}; border:none;
                border-top:1px solid {C.border}; border-radius:0;
                padding:12px; font-size:12px; text-align:left;
            }}
            QPushButton:hover {{ background:{C.card_hover}; color:{C.text}; }}
        """)
        settings_btn.clicked.connect(self._on_open_settings)
        sl.addWidget(settings_btn)

        parent.addWidget(sidebar)

        # 默认加载闲鱼子菜单
        self._update_sub_nav("xianyu")

    def _update_sub_nav(self, platform_key):
        """更新子导航菜单"""
        self.platform_sub_list.clear()
        self._sub_items = []

        sub_menus = {
            "xianyu": [
                ("📊 数据采集", "collect"),
                ("💬 AI对话", "chat"),
                ("📈 数据分析", "analysis"),
                ("📋 调研报告", "research"),
            ],
            "douyin": [
                ("🔥 热门话题", "topics"),
                ("💬 AI调研", "chat"),
                ("✍️ 拟稿话术", "draft"),
            ],
            "xiaohongshu": [
                ("📝 笔记分析", "notes"),
                ("🔑 关键词追踪", "keywords"),
                ("💬 AI调研", "chat"),
            ],
        }

        for label, key in sub_menus.get(platform_key, []):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.platform_sub_list.addItem(item)
            self._sub_items.append(item)

        if self._sub_items:
            self.platform_sub_list.setCurrentRow(0)

    def _on_platform_switch(self, row):
        """切换平台"""
        item = self.platform_list.item(row)
        if not item: return
        platform_key = item.data(Qt.ItemDataRole.UserRole)
        self.current_platform = platform_key
        self._update_sub_nav(platform_key)
        self._update_platform_tabs()

        # 更新顶部标题
        titles = {"xianyu": "🐟 闲鱼", "douyin": "🎵 抖音", "xiaohongshu": "📕 小红书"}
        self.topbar_title.setText(titles.get(platform_key, ""))

        # 更新开始按钮
        btn_texts = {"xianyu": "🚀 开始采集", "douyin": "🔥 追踪话题", "xiaohongshu": "🔍 分析笔记"}
        self.nav_start_btn.setText(btn_texts.get(platform_key, "🚀 开始"))

        # 更新placeholder
        placeholders = {"xianyu": "输入商品关键词...", "douyin": "输入话题关键词...", "xiaohongshu": "输入搜索关键词..."}
        self.nav_keyword.setPlaceholderText(placeholders.get(platform_key, "输入关键词..."))

        # 更新状态栏
        self.status_platform.setText(titles.get(platform_key, ""))

    def _on_sub_nav(self, row):
        """子导航切换"""
        if row < 0 or not hasattr(self, '_sub_items') or row >= len(self._sub_items):
            return
        if not hasattr(self, 'tab_widget') or self.tab_widget.count() == 0:
            return  # tab_widget 尚未初始化
        item = self._sub_items[row]
        key = item.data(Qt.ItemDataRole.UserRole)
        # 映射到tab索引
        tab_map = {
            "collect": 0, "chat": 1, "analysis": 2, "research": 3,
            "topics": 0, "draft": 2,
            "notes": 0, "keywords": 1,
        }
        idx = tab_map.get(key, 0)
        if idx < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(idx)

    # ═══════ 顶部快捷栏 ═══════
    def _build_topbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"background:{C.card}; border-bottom:1px solid {C.border};")
        tl = QHBoxLayout(bar)
        tl.setContentsMargins(16, 0, 12, 0)
        tl.setSpacing(8)

        self.topbar_title = QLabel("🐟 闲鱼")
        self.topbar_title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        tl.addWidget(self.topbar_title)

        tl.addStretch()

        self.nav_keyword = QLineEdit()
        self.nav_keyword.setPlaceholderText("输入关键词...")
        self.nav_keyword.setFixedWidth(200)
        self.nav_keyword.setFixedHeight(32)
        self.nav_keyword.returnPressed.connect(self._on_start)
        tl.addWidget(self.nav_keyword)

        self.nav_count = QLineEdit("30")
        self.nav_count.setPlaceholderText("条数")
        self.nav_count.setFixedWidth(48)
        self.nav_count.setFixedHeight(32)
        self.nav_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.addWidget(self.nav_count)

        self.nav_start_btn = QPushButton("🚀 开始采集")
        self.nav_start_btn.setFixedHeight(32)
        self.nav_start_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:{C.sidebar}; font-weight:bold; border:none; padding:6px 16px; font-size:12px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
            QPushButton:disabled {{ background:{C.border}; color:{C.text_muted}; }}
        """)
        self.nav_start_btn.clicked.connect(self._on_start)
        tl.addWidget(self.nav_start_btn)

        parent.addWidget(bar)

    # ═══════ 底部状态栏 ═══════
    def _build_statusbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(28)
        bar.setStyleSheet(f"background:{C.sidebar}; border-top:1px solid {C.border};")
        sl = QHBoxLayout(bar)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(16)

        self.status_platform = QLabel("🐟 闲鱼")
        self.status_platform.setStyleSheet(f"color:{C.primary}; font-size:11px; border:none; background:transparent; font-weight:bold;")
        sl.addWidget(self.status_platform)

        self.status_info = QLabel("🟢 就绪")
        self.status_info.setStyleSheet(f"color:{C.text_dim}; font-size:11px; border:none; background:transparent;")
        sl.addWidget(self.status_info)

        sl.addStretch()

        self.status_version = QLabel("v15.0")
        self.status_version.setStyleSheet(f"color:{C.text_muted}; font-size:10px; border:none; background:transparent;")
        sl.addWidget(self.status_version)

        parent.addWidget(bar)

    # ═══════ 平台标签页 ═══════
    def _build_platform_tabs(self):
        """构建平台相关的标签页（初始为闲鱼）"""
        self.tab_widget.clear()
        self._xianyu_collect_tab = self._data_tab()
        self._xianyu_chat_tab = self._chat_tab()
        self._xianyu_analysis_tab = self._analysis_tab()
        self._xianyu_research_tab = self._research_tab()

        self.tab_widget.addTab(self._xianyu_collect_tab, "📊 数据采集")
        self.tab_widget.addTab(self._xianyu_chat_tab, "💬 AI对话")
        self.tab_widget.addTab(self._xianyu_analysis_tab, "📈 数据分析")
        self.tab_widget.addTab(self._xianyu_research_tab, "📋 调研报告")

        # 延迟刷新仪表盘数据
        QTimer.singleShot(100, self._refresh_dashboard)

    def _update_platform_tabs(self):
        """根据当前平台更新标签页"""
        self.tab_widget.clear()
        platform = self.current_platform

        if platform == "xianyu":
            self.tab_widget.addTab(self._xianyu_collect_tab, "📊 数据采集")
            self.tab_widget.addTab(self._xianyu_chat_tab, "💬 AI对话")
            self.tab_widget.addTab(self._xianyu_analysis_tab, "📈 数据分析")
            self.tab_widget.addTab(self._xianyu_research_tab, "📋 调研报告")
        elif platform == "douyin":
            self.tab_widget.addTab(self._douyin_topics_tab(), "🔥 热门话题")
            self.tab_widget.addTab(self._xianyu_chat_tab, "💬 AI调研对话")
            self.tab_widget.addTab(self._douyin_draft_tab(), "✍️ 拟稿话术")
        elif platform == "xiaohongshu":
            self.tab_widget.addTab(self._xhs_notes_tab(), "📝 笔记分析")
            self.tab_widget.addTab(self._xhs_keywords_tab(), "🔑 关键词追踪")
            self.tab_widget.addTab(self._xianyu_chat_tab, "💬 AI调研对话")

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
        # 安全检查：如果仪表盘卡片还未创建则跳过
        if not hasattr(self, 'card_total'):
            return
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
        if hasattr(self, 'recent_table'):
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
            self.status_info.setText("📋 标题已复制到剪贴板")
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
        self.status_info.setText(f"📊 共 {len(items)} 条数据")

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

    # ===== AI 对话（v12.0 CodeBuddy风格：ScrollArea + 消息气泡Widget）=====

    def _chat_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        vl = QVBoxLayout(w)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)

        # ═══════ 顶部简洁标题栏 ═══════
        top = QFrame()
        top.setFixedHeight(48)
        top.setStyleSheet(f"background:{C.card}; border-bottom:1px solid {C.border};")
        th = QHBoxLayout(top)
        th.setContentsMargins(16, 0, 12, 0)

        title = QLabel("💬 AI 对话")
        title.setStyleSheet(f"font-size:14px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        th.addWidget(title)

        th.addStretch()

        vl.addWidget(top)

        # ═══════ 消息列表（ScrollArea） ═══════
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet(f"""
            QScrollArea {{ background:{C.bg}; border:none; }}
            QScrollBar:vertical {{ background:transparent; width:6px; margin:2px; }}
            QScrollBar::handle:vertical {{ background:{C.scrollbar}; border-radius:3px; min-height:30px; }}
            QScrollBar::handle:vertical:hover {{ background:{C.scrollbar_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        self.chat_msg_container = QWidget()
        self.chat_msg_container.setStyleSheet(f"background:transparent;")
        self.chat_msg_layout = QVBoxLayout(self.chat_msg_container)
        self.chat_msg_layout.setSpacing(8)
        self.chat_msg_layout.setContentsMargins(20, 16, 20, 16)
        self.chat_msg_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_msg_container)
        vl.addWidget(self.chat_scroll)

        # ═══════ 底部输入卡片 (WorkBuddy风格) ═══════
        bottom = QFrame()
        bottom.setStyleSheet(f"background:transparent; border:none;")
        bl = QVBoxLayout(bottom)
        bl.setSpacing(0)
        bl.setContentsMargins(12, 0, 12, 8)

        # 输入卡片主体
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame#inputCard {{
                background: {C.card};
                border: 1px solid {C.border};
                border-radius: 12px;
            }}
            QFrame#inputCard:hover {{ border-color: {C.primary}60; }}
        """)
        card.setObjectName("inputCard")
        cl = QVBoxLayout(card)
        cl.setSpacing(0)
        cl.setContentsMargins(2, 2, 2, 4)

        # ── 输入区 ──
        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("输入消息... (Enter发送，Shift+Enter换行)")
        self.chat_input.setFixedHeight(36)
        self.chat_input.setAcceptRichText(False)
        self.chat_input.setStyleSheet(f"""
            QTextEdit#chatInput {{
                border: none; border-radius: 0; padding: 4px 16px 0px 16px;
                font-size: 13px; background: transparent; color: {C.text};
            }}
            QTextEdit#chatInput:focus {{ border: none; }}
        """)
        self.chat_input.installEventFilter(self)
        cl.addWidget(self.chat_input)

        # ── 底部工具栏 ──
        tool_row = QHBoxLayout()
        tool_row.setContentsMargins(4, 0, 4, 4)
        tool_row.setSpacing(2)

        # 模型选择下拉按钮
        model_btn = QPushButton("Agnes")
        model_btn.setFixedHeight(22)
        model_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        model_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.text}; font-weight: bold;
                border: none; border-radius: 8px; padding: 2px 6px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {C.bg}; color: {C.primary}; }}
        """)
        self._model_menu_btn = model_btn  # 保存引用用于切换时更新文字
        model_menu = QMenu(self)
        model_configs = [("agnes", "Agnes"), ("deepseek", "DS"), ("qwen", "通义")]
        for key, label in model_configs:
            action = model_menu.addAction(f"{'●' if key == 'agnes' else '○'} {label}")
            action.triggered.connect(lambda checked, k=key, l=label: self._on_model_menu_select(k, l))
        model_btn.setMenu(model_menu)
        tool_row.addWidget(model_btn)

        # 自动执行开关
        auto_pill = QFrame()
        auto_pill.setObjectName("autoPill")
        auto_pill.setStyleSheet(f"QFrame#autoPill {{ background:{C.bg}; border-radius:6px; border:1px solid {C.border}; }}")
        auto_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        apl = QHBoxLayout(auto_pill)
        apl.setContentsMargins(6, 0, 8, 0)
        apl.setSpacing(2)
        self.agent_toggle = QCheckBox("自动")
        self.agent_toggle.setStyleSheet(f"QCheckBox {{ font-size:10px; color:{C.text}; spacing:2px; border:none; background:transparent; }}")
        self.agent_toggle.toggled.connect(self._on_agent_mode_toggled)
        apl.addWidget(self.agent_toggle)
        tool_row.addWidget(auto_pill)

        # 思考深度选择器（pill风格）
        self.depth_btn_group = QFrame()
        self.depth_btn_group.setObjectName("depthGroup")
        self.depth_btn_group.setStyleSheet(
            f"QFrame#depthGroup {{ background:{C.bg}; border-radius:6px; border:1px solid {C.border}; }}"
        )
        dg = QHBoxLayout(self.depth_btn_group)
        dg.setContentsMargins(2, 2, 2, 2)
        dg.setSpacing(1)

        self._depth_btns = {}
        depth_configs = [
            ("high", "深度思考"),
            ("medium", "平衡"),
            ("low", "快速"),
        ]
        for key, label in depth_configs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 6px;
                    padding: 1px 6px; font-size: 10px; color: {C.text};
                }}
                QPushButton:hover {{ color: {C.purple}; background: {C.card}; }}
                QPushButton:checked {{
                    color: {C.purple}; font-weight: bold; background: {C.card};
                }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._on_depth_switch(k))
            dg.addWidget(btn)
            self._depth_btns[key] = btn

        self._depth_btns["medium"].setChecked(True)  # 默认"平衡"
        tool_row.addWidget(self.depth_btn_group)

        # 技能按钮
        skill_btn = QPushButton("⚡技能")
        skill_btn.setFixedHeight(22)
        skill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skill_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.text};
                border: none; border-radius: 8px; padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {C.bg}; color: {C.primary}; }}
        """)
        skill_menu = QMenu(self)
        for name in ["运营策略", "文案优化", "定价分析", "选品建议", "客户沟通"]:
            action = skill_menu.addAction(f"{AIAssistant.SCENARIOS[name]['icon']} {name}")
            action.triggered.connect(lambda checked, n=name: self._on_quick_tag(n))
        skill_btn.setMenu(skill_menu)
        tool_row.addWidget(skill_btn)

        # 场景按钮
        scene_btn = QPushButton("场景")
        scene_btn.setFixedHeight(22)
        scene_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scene_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.text};
                border: none; border-radius: 8px; padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {C.bg}; color: {C.primary}; }}
        """)
        scene_menu = QMenu(self)
        for name in ["自由对话", "运营策略", "文案优化", "定价分析", "选品建议", "客户沟通"]:
            icon = AIAssistant.SCENARIOS.get(name, {}).get("icon", "💡")
            action = scene_menu.addAction(f"{icon} {name}")
            action.triggered.connect(lambda checked, n=name: self._on_scene_menu_select(n))
        scene_btn.setMenu(scene_menu)
        tool_row.addWidget(scene_btn)

        # + 更多按钮
        more_btn = QPushButton("+")
        more_btn.setFixedSize(22, 22)
        more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        more_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.text}; font-size: 14px; font-weight: bold;
                border: none; border-radius: 8px;
            }}
            QPushButton:hover {{ background: {C.bg}; color: {C.primary}; }}
        """)
        more_menu = QMenu(self)
        more_menu.addAction("📊 数据概览", lambda: self._on_agent_data_overview())
        more_menu.addAction("📥 导出Excel", lambda: self._on_agent_export())
        more_menu.addAction("📈 生成报告", lambda: self._on_agent_report())
        more_menu.addAction("🔍 市场调研", lambda: self._on_agent_research())
        more_menu.addSeparator()
        more_menu.addAction("🗑 清空对话", self._on_clear_chat)
        more_btn.setMenu(more_menu)
        tool_row.addWidget(more_btn)

        tool_row.addStretch()

        # 状态徽章
        self.chat_status_badge = StatusBadge("就绪", C.success)
        tool_row.addWidget(self.chat_status_badge)

        tool_row.addSpacing(4)

        # 发送圆形按钮
        send_btn = QPushButton("↑")
        send_btn.setFixedSize(28, 28)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.primary}; color: white; font-size: 13px; font-weight: bold;
                border: none; border-radius: 14px;
            }}
            QPushButton:hover {{ background: {C.primary_hover}; }}
            QPushButton:pressed {{ background: #E8951E; }}
            QPushButton:disabled {{ background: {C.border}; color: {C.text_muted}; }}
        """)
        send_btn.clicked.connect(self._on_send_message)
        tool_row.addWidget(send_btn)

        cl.addLayout(tool_row)
        bl.addWidget(card)
        vl.addWidget(bottom)

        self._init_assistant()
        self._add_welcome_message()
        return w

    def _on_model_menu_select(self, key, label):
        """通过下拉菜单切换AI模型"""
        info = MarketResearcher.API_PROVIDERS.get(key, {})
        if not info: return
        self.researcher.config["provider"] = key
        self.researcher.config["api_url"] = info.get("url", "")
        self.researcher.config["model"] = info.get("default_model", "")
        self.ai_assistant.config = self.researcher.config
        # 更新按钮文字 + 菜单勾选标记
        self._model_menu_btn.setText(label)
        menu = self._model_menu_btn.menu()
        if menu:
            for action in menu.actions():
                txt = action.text()
                action.setText(txt.replace("●", "○"))
            sender = self.sender()
            if sender:
                sender.setText(sender.text().replace("○", "●"))

    def _on_model_switch(self, key):
        """切换AI模型（兼容旧接口）"""
        info = MarketResearcher.API_PROVIDERS.get(key, {})
        if not info: return
        self.researcher.config["provider"] = key
        self.researcher.config["api_url"] = info.get("url", "")
        self.researcher.config["model"] = info.get("default_model", "")
        self.ai_assistant.config = self.researcher.config

    def _on_depth_switch(self, key):
        """切换思考深度"""
        self.thinking_depth = key
        # 同步到 assistant 配置
        if hasattr(self, 'ai_assistant'):
            self.ai_assistant.thinking_depth = key
        # 更新按钮状态
        for k, btn in self._depth_btns.items():
            btn.setChecked(k == key)

    def _on_scene_menu_select(self, name):
        """场景菜单选择"""
        if name == "自由对话": return
        kw = self.nav_keyword.text().strip() or ""
        if not kw:
            self._append_message("ai", f"📌 请先在导航栏输入关键词，再使用「{name}」场景。")
            return
        self._append_message("user", f"{name}")
        QApplication.processEvents()
        prompt = AIAssistant.SCENARIOS.get(name, {}).get("prompt", "").format(keyword=kw)
        self._start_stream(prompt, kw)

    def _on_agent_data_overview(self):
        result = self.ai_assistant._tool_get_data()
        self._append_message("ai", result)

    def _on_agent_export(self):
        try:
            from core.exporter import Exporter
            exporter = Exporter(self.db)
            path = exporter.export_to_excel()
            self._log(f"导出: {path}", "success")
            self._append_message("ai", f"✅ **导出成功！**\n\n`{path}`")
        except Exception as e:
            self._append_message("ai", f"❌ 导出失败: {e}")

    def _on_agent_report(self):
        try:
            from core.analyzer import Analyzer
            analyzer = Analyzer(self.db)
            md = analyzer.generate_markdown_report(None, "全部")
            self.analysis_text.setMarkdown(md)
            self.tab_widget.setCurrentIndex(4)
            self._append_message("ai", "✅ **分析报告已生成！** 切换到「文案分析」标签页查看。")
        except Exception as e:
            self._append_message("ai", f"❌ 生成失败: {e}")

    def _on_agent_research(self):
        kw = self.nav_keyword.text().strip() or self.chat_input.toPlainText().strip()
        if not kw:
            self._append_message("ai", "请先在导航栏输入调研关键词。")
            return
        try:
            from core.researcher import MarketResearcher
            mr = MarketResearcher()
            md = mr.generate_markdown_report(kw)
            self.research_text.setMarkdown(md)
            self.tab_widget.setCurrentIndex(2)
            self._append_message("ai", f"✅ **市场调研「{kw}」已完成！** 切换到「AI调研」标签页查看。")
        except Exception as e:
            self._append_message("ai", f"❌ 调研失败: {e}")

    def eventFilter(self, obj, event):
        """拦截Enter发送消息"""
        from PyQt6.QtCore import QEvent
        if obj == self.chat_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._on_send_message()
                return True
        return super().eventFilter(obj, event)

    def _add_welcome_message(self):
        """添加欢迎消息气泡"""
        welcome = (
            "👋 你好！我是**闲鱼运营AI助手**\n\n"
            "我可以帮你：\n"
            "- 制定运营策略、优化文案标题\n"
            "- 分析价格趋势、提供选品建议\n"
            "- 客户沟通话术、数据分析报告\n\n"
            "💡 勾选「**自动执行**」后，我还能帮你操作软件：\n"
            "「采集蓝牙耳机30条」「导出数据」「分析价格」"
        )
        self._append_message("ai", welcome)

    def _append_message(self, role, text):
        """核心：添加一条消息气泡Widget"""
        bubble = QFrame()
        bubble.setMaximumWidth(int(self.width() * 0.82) if self.width() > 200 else 600)

        bl = QHBoxLayout(bubble)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        if role == "user":
            bl.addStretch()
            # 用户气泡：橙色右对齐
            content = QLabel(text)
            content.setWordWrap(True)
            content.setTextFormat(Qt.TextFormat.MarkdownText)
            content.setStyleSheet(f"""
                QLabel {{
                    background: {C.primary}; color: white;
                    padding: 10px 16px; border-radius: 16px 4px 16px 16px;
                    font-size: 13px; line-height: 1.6;
                }}
            """)
            bl.addWidget(content)
            bubble.setStyleSheet("background:transparent;")
        else:
            # AI气泡：浅灰左对齐
            content = QLabel(text)
            content.setWordWrap(True)
            content.setTextFormat(Qt.TextFormat.MarkdownText)
            content.setStyleSheet(f"""
                QLabel {{
                    background: {C.card}; color: {C.text};
                    padding: 12px 18px; border-radius: 4px 16px 16px 16px;
                    font-size: 13px; line-height: 1.7;
                    border: 1px solid {C.border};
                }}
            """)
            bl.addWidget(content)
            bl.addStretch()
            bubble.setStyleSheet("background:transparent;")

        # 插入到 stretch 之前（倒数第一个是stretch）
        idx = self.chat_msg_layout.count() - 1
        self.chat_msg_layout.insertWidget(max(0, idx), bubble)

        # 滚动到底部
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def _show_typing(self):
        self.chat_status_badge.set_state("思考中...", C.warning)
        self.typing_indicator.start()

    def _hide_typing(self):
        self.typing_indicator.stop()
        self.chat_status_badge.set_state("就绪", C.success)

    def _on_quick_tag(self, tag_name):
        kw = self.nav_keyword.text().strip() or ""
        if not kw:
            self._append_message("ai", f"📌 **{tag_name}** — 请先在导航栏输入关键词。")
            return
        self._append_message("user", f"帮我做{tag_name}")
        QApplication.processEvents()
        prompt = AIAssistant.SCENARIOS.get(tag_name, {}).get("prompt", "").format(keyword=kw)
        self._start_stream(prompt, kw)

    def _init_assistant(self):
        mem_path = self.cfg.get("ui", {}).get("memory_path", os.path.join(self.cfg["paths"]["data_dir"], "ai_memory"))
        self.ai_assistant = AIAssistant(config=self.researcher.config, db=self.db, memory_path=mem_path, main_window=self)
        self.ai_assistant.load_memory()
        self.agent_mode = False
        self.thinking_depth = "medium"
        self.ai_assistant.thinking_depth = self.thinking_depth

    def _on_agent_mode_toggled(self, checked):
        self.agent_mode = checked
        if checked:
            self.chat_status_badge.set_state("自动执行", C.info)
            self._append_message("ai",
                "⚡ **自动执行模式已开启**\n\n"
                "我现在是你的操作Agent。请告诉我要做什么：\n\n"
                "• 📥 「采集蓝牙耳机30条」— 开始采集\n"
                "• 📊 「导出数据」— 导出Excel\n"
                "• 📈 「分析价格」— 价格分析报告\n"
                "• 🔍 「调研市场」— 市场调研报告\n\n"
                "请告诉我你要执行什么操作？"
            )
            self.ai_assistant.set_agent_mode(True)
        else:
            self.chat_status_badge.set_state("就绪", C.success)
            self._append_message("ai", "💬 **已切换回自由对话模式**")
            self.ai_assistant.set_agent_mode(False)

    def _on_send_message(self):
        msg = self.chat_input.toPlainText().strip()
        if not msg: return
        self.chat_input.clear()
        self._append_message("user", msg)
        QApplication.processEvents()
        kw = self.nav_keyword.text().strip() or ""

        if self.agent_mode:
            self._show_typing()
            self.chat_status_badge.set_state("分析中...", C.warning)
            QApplication.processEvents()
            action = self.ai_assistant.parse_agent_action(msg, kw)
            if action.get("need_clarify"):
                self._hide_typing(); self.chat_status_badge.set_state("等待确认", C.info)
                self._append_message("ai", action["clarify_msg"]); return
            if action.get("action") == "exec":
                self.chat_status_badge.set_state("执行中...", C.warning)
                QApplication.processEvents()
                result = self._execute_agent_action(action, msg)
                self._hide_typing(); self.chat_status_badge.set_state("自动执行", C.info)
                self._append_message("ai", result); return
            if action.get("action") == "confirm":
                self._hide_typing(); self.chat_status_badge.set_state("等待确认", C.info)
                self._pending_action = action
                self._append_message("ai", f"{action['confirm_msg']}\n\n回复「确认」执行。"); return
            # Agent模式非操作对话 → 走流式
            self._start_stream(msg, kw, is_agent=True)
            return

        # 普通模式先检查是否需要澄清
        need_clarify = self.ai_assistant.check_if_need_clarify(msg)
        if need_clarify:
            self._append_message("ai", need_clarify)
            self.chat_status_badge.set_state("等待回复", C.info)
            return

        self._start_stream(msg, kw)

    def _start_stream(self, msg, kw, is_agent=False):
        """启动流式AI调用"""
        self._show_typing()
        self.chat_status_badge.set_state("思考中...", C.warning)
        QApplication.processEvents()

        # 外层容器：状态标签 + 气泡
        wrapper = QWidget()
        wrapper.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(4)

        # 状态标签（思考中）
        self._stream_status = QLabel("● 思考中...")
        self._stream_status.setStyleSheet(f"font-size:11px; color:{C.warning}; background:transparent; border:none; padding-left:4px;")
        wl.addWidget(self._stream_status)

        # 气泡内容
        bubble = QFrame()
        bubble.setMaximumWidth(int(self.width() * 0.82) if self.width() > 200 else 600)
        bl = QHBoxLayout(bubble)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(8)

        self._stream_label = QLabel("")
        self._stream_label.setWordWrap(True)
        self._stream_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self._stream_label.setStyleSheet(f"""
            QLabel {{
                background: {C.card}; color: {C.text};
                padding: 12px 18px; border-radius: 4px 16px 16px 16px;
                font-size: 13px; line-height: 1.7;
                border: 1px solid {C.border};
            }}
        """)
        bl.addWidget(self._stream_label)
        bl.addStretch()
        bubble.setStyleSheet("background:transparent;")
        wl.addWidget(bubble)

        idx = self.chat_msg_layout.count() - 1
        self.chat_msg_layout.insertWidget(max(0, idx), wrapper)
        self._scroll_down()

        # 启动流式线程
        self._stream_worker = StreamWorker(self.ai_assistant, msg, kw)
        self._stream_worker.chunk_signal.connect(self._on_stream_chunk)
        self._stream_worker.done_signal.connect(lambda text: self._on_stream_done(text, is_agent))
        self._stream_worker.error_signal.connect(self._on_stream_error)
        self._stream_worker.start()

    def _on_stream_chunk(self, text):
        """流式逐字更新"""
        self._stream_label.setText(text)
        self._stream_status.setText("● 生成中...")
        self._scroll_down()

    def _on_stream_done(self, text, is_agent=False):
        self._hide_typing()
        if is_agent:
            self.chat_status_badge.set_state("自动执行", C.info)
        # 状态切换：完成 → 2秒后消失
        self._stream_status.setText("● 已完成")
        self._stream_status.setStyleSheet(f"font-size:11px; color:{C.success}; background:transparent; border:none; padding-left:4px;")
        QTimer.singleShot(2000, lambda: self._stream_status.hide())
        self._stream_label = None

    def _on_stream_error(self, err):
        self._hide_typing()
        self._stream_label.setText(f"❌ {err}")
        self._stream_status.setText("● 出错了")
        self._stream_status.setStyleSheet(f"font-size:11px; color:{C.danger}; background:transparent; border:none; padding-left:4px;")
        self._stream_label = None

    def _scroll_down(self):
        QTimer.singleShot(20, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def _on_clear_chat(self):
        reply = QMessageBox.question(self, "确认清空",
            "<h3>清空对话</h3><p>是否同时清除AI记忆？</p>",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if reply == QMessageBox.StandardButton.Cancel: return
        if reply == QMessageBox.StandardButton.Yes: self.ai_assistant.clear_memory()
        self.ai_assistant.clear_history()
        # 清空所有消息气泡（保留stretch）
        while self.chat_msg_layout.count() > 1:
            item = self.chat_msg_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _execute_agent_action(self, action, original_msg):
        """Agent自动执行操作"""
        act_type = action.get("type", "")
        kw = action.get("keyword", "")
        count = action.get("count", 30)

        try:
            if act_type == "collect":
                self.nav_keyword.setText(kw)
                self.nav_count.setText(str(count))
                QApplication.processEvents()
                self._on_start()
                return f"✅ **已开始采集「{kw}」**\n\n采集数量: {count} 条\n浏览器将自动打开，请扫码登录闲鱼。\n\n采集完成后会自动保存数据。"

            elif act_type == "export":
                from core.exporter import Exporter
                exporter = Exporter(self.db)
                path = exporter.export_to_excel(keyword=kw if kw else None)
                self._log(f"✅ AI Agent 导出: {path}", "success")
                self._refresh_data_view()
                return f"✅ **导出成功！**\n\n文件: `{path}`\n\n数据已导出为 Excel 格式。"

            elif act_type == "price_analysis":
                return self.ai_assistant._tool_price_analysis(kw)

            elif act_type == "title_analysis":
                return self.ai_assistant._tool_title_trends(kw)

            elif act_type == "data_overview":
                return self.ai_assistant._tool_get_data()

            elif act_type == "research":
                from core.researcher import MarketResearcher
                mr = MarketResearcher()
                md = mr.generate_markdown_report(kw)
                self.research_keyword.setText(kw)
                self.research_text.setMarkdown(md)
                self.tab_widget.setCurrentIndex(2)
                return f"✅ **市场调研「{kw}」已完成！**\n\n已切换到「AI调研」标签页查看完整报告。"

            elif act_type == "analyze_report":
                from core.analyzer import Analyzer
                analyzer = Analyzer(self.db)
                md = analyzer.generate_markdown_report(None, kw or "全部")
                self.analysis_text.setMarkdown(md)
                self.tab_widget.setCurrentIndex(4)
                return f"✅ **文案分析报告已生成！**\n\n已切换到「文案分析」标签页查看。"

            elif act_type == "delete_confirm":
                tasks = self.db.get_tasks(limit=100)
                deleted = 0
                for t in tasks:
                    if kw in t.get("keyword", ""):
                        self.db.delete_task(t["id"])
                        deleted += 1
                self._load_task_history()
                self._refresh_dashboard()
                self._refresh_data_view()
                return f"✅ **已删除 {deleted} 个任务**（关键词「{kw}」）及其所有数据。"

            elif act_type == "chat":
                reply = self.ai_assistant.chat(original_msg, kw)
                return reply

            else:
                return f"❓ 无法识别操作「{act_type}」。可执行: 采集/导出/分析价格/分析文案/调研/数据概览/删除"

        except Exception as e:
            import traceback
            self._log(f"Agent执行失败: {traceback.format_exc()}", "error")
            return f"❌ **执行失败**: {str(e)}"

    # ===== 抖音话题追踪 =====

    def _douyin_topics_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        # 标题区
        header = QLabel("🔥 抖音热门话题追踪")
        header.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        lay.addWidget(header)

        desc = QLabel("输入话题关键词，AI 将为你分析抖音上的热门内容趋势，并生成调研总结和话术建议。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        lay.addWidget(desc)

        # 输入区
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background:{C.card}; border:1px solid {C.border}; border-radius:10px;")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(10)

        self.douyin_topic_input = QLineEdit()
        self.douyin_topic_input.setPlaceholderText("输入抖音话题关键词，如：美妆、穿搭、数码...")
        self.douyin_topic_input.setFixedHeight(40)
        il.addWidget(self.douyin_topic_input)

        self.douyin_search_btn = QPushButton("🔍 AI调研")
        self.douyin_search_btn.setFixedHeight(40)
        self.douyin_search_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:{C.sidebar}; font-weight:bold; border:none; padding:8px 20px; font-size:13px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        self.douyin_search_btn.clicked.connect(self._on_douyin_research)
        il.addWidget(self.douyin_search_btn)
        lay.addWidget(input_frame)

        # 结果展示区
        self.douyin_result = QTextEdit()
        self.douyin_result.setReadOnly(True)
        self.douyin_result.setStyleSheet(f"""
            QTextEdit {{
                background:{C.card}; color:{C.text}; border:1px solid {C.border};
                border-radius:10px; padding:16px; font-size:13px;
            }}
        """)
        self.douyin_result.setMarkdown(
            "### 🎵 抖音话题追踪\n\n"
            "输入话题关键词后，AI 将分析：\n\n"
            "- **话题热度趋势** — 当前热门程度和增长趋势\n"
            "- **热门内容模式** — 爆款视频的共性特征\n"
            "- **受众画像** — 核心用户群体分析\n"
            "- **话术建议** — 可用于创作的文案灵感\n\n"
            "> 💡 提示：输入具体话题词可获得更精准的分析"
        )
        lay.addWidget(self.douyin_result)

        return w

    def _on_douyin_research(self):
        keyword = self.douyin_topic_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入话题关键词")
            return
        self.status_info.setText(f"🔍 正在调研抖音话题: {keyword}...")
        self._append_message("user", f"调研抖音话题: {keyword}")
        prompt = f"请对抖音平台上的「{keyword}」话题进行深入调研分析，包括：1.当前热门趋势 2.爆款内容模式 3.受众画像 4.可借鉴的创作话术。请用Markdown格式输出。"
        self._start_stream(prompt, keyword)

    # ===== 抖音拟稿话术 =====

    def _douyin_draft_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        header = QLabel("✍️ 抖音拟稿话术")
        header.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        lay.addWidget(header)

        desc = QLabel("根据话题调研结果，AI 帮你生成抖音视频文案、标题和口播话术。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        lay.addWidget(desc)

        # 输入区
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background:{C.card}; border:1px solid {C.border}; border-radius:10px;")
        il = QVBoxLayout(input_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("话题:"))
        self.draft_topic = QLineEdit()
        self.draft_topic.setPlaceholderText("如：美妆教程")
        row1.addWidget(self.draft_topic)

        style_combo = NoWheelComboBox()
        style_combo.addItems(["口播脚本", "剧情脚本", "产品测评", "知识科普", "Vlog文案"])
        row1.addWidget(QLabel("风格:"))
        row1.addWidget(style_combo)
        self.draft_style = style_combo
        il.addLayout(row1)

        generate_btn = QPushButton("✍️ 生成话术")
        generate_btn.setFixedHeight(36)
        generate_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:{C.sidebar}; font-weight:bold; border:none; padding:8px 20px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        generate_btn.clicked.connect(self._on_generate_draft)
        il.addWidget(generate_btn)
        lay.addWidget(input_frame)

        self.draft_result = QTextEdit()
        self.draft_result.setReadOnly(True)
        self.draft_result.setStyleSheet(f"""
            QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; font-size:13px; }}
        """)
        self.draft_result.setMarkdown("### ✍️ AI 话术生成\n\n选择话题和风格后，AI 将为你生成抖音创作话术。")
        lay.addWidget(self.draft_result)

        return w

    def _on_generate_draft(self):
        topic = self.draft_topic.text().strip()
        style = self.draft_style.currentText()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入话题")
            return
        self.status_info.setText("✍️ 正在生成话术...")
        prompt = f"请为抖音平台生成关于「{topic}」的{style}文案。要求：1.吸引人的标题 2.完整口播/脚本文案 3.3-5个话题标签 4.发布建议。用Markdown格式。"
        self._append_message("user", f"生成话术: {topic} ({style})")
        self._start_stream(prompt, topic)

    # ===== 小红书笔记分析 =====

    def _xhs_notes_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        header = QLabel("📝 小红书笔记分析")
        header.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        lay.addWidget(header)

        desc = QLabel("输入搜索关键词，AI 分析小红书上的爆款笔记模式、标题套路和内容趋势。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        lay.addWidget(desc)

        input_frame = QFrame()
        input_frame.setStyleSheet(f"background:{C.card}; border:1px solid {C.border}; border-radius:10px;")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(10)

        self.xhs_notes_input = QLineEdit()
        self.xhs_notes_input.setPlaceholderText("输入小红书搜索关键词，如：护肤、旅行、美食...")
        self.xhs_notes_input.setFixedHeight(40)
        il.addWidget(self.xhs_notes_input)

        self.xhs_notes_btn = QPushButton("🔍 AI分析")
        self.xhs_notes_btn.setFixedHeight(40)
        self.xhs_notes_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:{C.sidebar}; font-weight:bold; border:none; padding:8px 20px; font-size:13px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        self.xhs_notes_btn.clicked.connect(self._on_xhs_notes_analysis)
        il.addWidget(self.xhs_notes_btn)
        lay.addWidget(input_frame)

        self.xhs_notes_result = QTextEdit()
        self.xhs_notes_result.setReadOnly(True)
        self.xhs_notes_result.setStyleSheet(f"""
            QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; font-size:13px; }}
        """)
        self.xhs_notes_result.setMarkdown(
            "### 📝 小红书爆文分析\n\n"
            "输入关键词后，AI 将分析：\n\n"
            "- **爆文标题模式** — 高互动笔记的标题套路\n"
            "- **内容趋势** — 当前热门的笔记类型和风格\n"
            "- **封面策略** — 高点击率封面的设计要点\n"
            "- **互动数据** — 点赞/收藏/评论的行业基准\n\n"
            "> 💡 提示：输入具体的品类关键词获取更精准分析"
        )
        lay.addWidget(self.xhs_notes_result)

        return w

    def _on_xhs_notes_analysis(self):
        keyword = self.xhs_notes_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        self.status_info.setText(f"🔍 正在分析小红书: {keyword}...")
        self._append_message("user", f"分析小红书笔记: {keyword}")
        prompt = f"请对小红书平台上「{keyword}」相关的笔记进行深入分析，包括：1.爆文标题模式和套路 2.当前内容趋势和热门笔记类型 3.高互动笔记的共性特征 4.创作建议和选题方向。用Markdown格式。"
        self._start_stream(prompt, keyword)

    # ===== 小红书关键词追踪 =====

    def _xhs_keywords_tab(self):
        w = QWidget()
        w.setStyleSheet(f"background:{C.bg};")
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        header = QLabel("🔑 小红书关键词趋势")
        header.setStyleSheet(f"font-size:18px; font-weight:bold; color:{C.text}; border:none; background:transparent;")
        lay.addWidget(header)

        desc = QLabel("追踪小红书搜索关键词的热度趋势、竞争程度和内容供需分析。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C.text_dim}; font-size:12px; border:none; background:transparent;")
        lay.addWidget(desc)

        input_frame = QFrame()
        input_frame.setStyleSheet(f"background:{C.card}; border:1px solid {C.border}; border-radius:10px;")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(10)

        self.xhs_kw_input = QLineEdit()
        self.xhs_kw_input.setPlaceholderText("输入要追踪的关键词，如：早C晚A、露营装备...")
        self.xhs_kw_input.setFixedHeight(40)
        il.addWidget(self.xhs_kw_input)

        self.xhs_kw_btn = QPushButton("📈 追踪趋势")
        self.xhs_kw_btn.setFixedHeight(40)
        self.xhs_kw_btn.setStyleSheet(f"""
            QPushButton {{ background:{C.primary}; color:{C.sidebar}; font-weight:bold; border:none; padding:8px 20px; font-size:13px; }}
            QPushButton:hover {{ background:{C.primary_hover}; }}
        """)
        self.xhs_kw_btn.clicked.connect(self._on_xhs_keyword_track)
        il.addWidget(self.xhs_kw_btn)
        lay.addWidget(input_frame)

        self.xhs_kw_result = QTextEdit()
        self.xhs_kw_result.setReadOnly(True)
        self.xhs_kw_result.setStyleSheet(f"""
            QTextEdit {{ background:{C.card}; color:{C.text}; border:1px solid {C.border}; border-radius:10px; padding:16px; font-size:13px; }}
        """)
        self.xhs_kw_result.setMarkdown(
            "### 🔑 关键词趋势追踪\n\n"
            "输入关键词后，AI 将分析：\n\n"
            "- **搜索热度** — 关键词的搜索量趋势\n"
            "- **竞争程度** — 相关笔记数量和竞争分析\n"
            "- **内容缺口** — 用户需求未被满足的方向\n"
            "- **关联词推荐** — 长尾关键词和关联热词\n\n"
            "> 💡 提示：可同时追踪多个关键词进行对比"
        )
        lay.addWidget(self.xhs_kw_result)

        return w

    def _on_xhs_keyword_track(self):
        keyword = self.xhs_kw_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return
        self.status_info.setText(f"📈 正在追踪关键词: {keyword}...")
        self._append_message("user", f"追踪小红书关键词: {keyword}")
        prompt = f"请对小红书平台上「{keyword}」关键词进行趋势分析，包括：1.搜索热度评估 2.竞争程度分析 3.内容缺口和机会 4.长尾关键词和关联热词推荐 5.内容创作建议。用Markdown格式。"
        self._start_stream(prompt, keyword)

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
        self.status_info.setText(f"🔄 {msg}")
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
            self.status_info.setText(f"✅ 采集完成 - 任务 #{tid}")
            self._log(f"🎉 采集任务 #{tid} 完成！", "success")
            self._load_task_history()
            self._refresh_data_view()
            self._refresh_dashboard()
            if QMessageBox.question(self, "采集完成", "<h3>🎉 采集完成！</h3><p>是否立即导出 Excel？</p>") == QMessageBox.StandardButton.Yes:
                self._on_export_excel()
        else:
            self.status_info.setText("⚠ 采集中断或失败")

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
