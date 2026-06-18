"""
闲鱼数据调研工具 - 主窗口 GUI
基于 PyQt6 构建的图形界面，零基础友好
"""

import os
import sys
import json
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QTextEdit, QProgressBar, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QSplitter, QFrame, QComboBox, QStatusBar, QMenuBar, QMenu,
    QFileDialog, QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCursor, QAction

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import get_config, save_user_config
from core.database import Database
from core.analyzer import Analyzer
from core.exporter import Exporter


# ========== 爬虫工作线程 ==========

class CrawlerWorker(QThread):
    """后台爬虫线程，避免阻塞 GUI"""
    log_signal = pyqtSignal(str, str)       # (message, level)
    progress_signal = pyqtSignal(int, int, str)  # (current, total, message)
    finished_signal = pyqtSignal(object)     # task_id or None
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
            # 登录
            login_ok = await self.crawler.login()
            self.login_status_signal.emit(login_ok)
            if not login_ok:
                return None

            # 采集
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
    """闲鱼数据调研工具 - 主窗口"""

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

    def _init_ui(self):
        """初始化界面"""
        self.setWindowTitle(self.cfg["ui"]["window_title"])
        self.setMinimumSize(
            self.cfg["ui"]["window_width"],
            self.cfg["ui"]["window_height"]
        )

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ===== 顶部：搜索区域 =====
        search_group = QGroupBox("🔍 搜索采集")
        search_group.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        search_layout = QVBoxLayout(search_group)

        # 第一行：关键词 + 数量 + 图片选项
        row1 = QHBoxLayout()

        row1.addWidget(QLabel("关键词:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入商品关键词，如：蓝牙耳机、机械键盘...")
        self.keyword_input.setMinimumWidth(250)
        self.keyword_input.returnPressed.connect(self._on_start)
        row1.addWidget(self.keyword_input)

        row1.addWidget(QLabel("采集数量:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(5, 100)
        self.count_spin.setValue(30)
        self.count_spin.setSuffix(" 条")
        self.count_spin.setToolTip("建议30-50条，最多100条")
        row1.addWidget(self.count_spin)

        self.download_img_check = QCheckBox("下载图片")
        self.download_img_check.setChecked(True)
        self.download_img_check.setToolTip("是否同时下载商品主图到本地")
        row1.addWidget(self.download_img_check)

        row1.addStretch()
        search_layout.addLayout(row1)

        # 第二行：按钮
        row2 = QHBoxLayout()

        self.start_btn = QPushButton("▶ 开始采集")
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 24px;
            }
            QPushButton:hover {
                background-color: #FF8C5A;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        row2.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #E8505B;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        row2.addWidget(self.stop_btn)

        # 防封提示
        self.anti_ban_label = QLabel(
            f"🛡 防封保护：间隔 {self.cfg['anti_ban']['min_delay']}-{self.cfg['anti_ban']['max_delay']} 秒 | "
            f"单次最多 {self.cfg['anti_ban']['max_items_per_session']} 条"
        )
        self.anti_ban_label.setStyleSheet("color: #666; font-size: 11px;")
        row2.addWidget(self.anti_ban_label)
        row2.addStretch()

        search_layout.addLayout(row2)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(20)
        search_layout.addWidget(self.progress_bar)

        # 当前状态标签
        self.status_label = QLabel("就绪 - 请输入关键词开始采集")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        search_layout.addWidget(self.status_label)

        main_layout.addWidget(search_group)

        # ===== 中部：标签页（日志 + 数据 + 分析） =====
        self.tab_widget = QTabWidget()

        # --- 日志页 ---
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("background-color: #1E1E1E; color: #D4D4D4;")
        self.log_text.setPlaceholderText("运行日志将显示在这里...")
        log_layout.addWidget(self.log_text)

        log_btn_row = QHBoxLayout()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_btn_row.addWidget(self.clear_log_btn)
        log_btn_row.addStretch()
        log_layout.addLayout(log_btn_row)

        self.tab_widget.addTab(self.log_tab, "📋 运行日志")

        # --- 数据预览页 ---
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            "序号", "标题", "价格", "所在地", "卖家",
            "浏览量", "想要数", "采集时间"
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        data_layout.addWidget(self.data_table)

        # 数据操作按钮
        data_btn_row = QHBoxLayout()
        self.export_excel_btn = QPushButton("📥 导出 Excel")
        self.export_excel_btn.clicked.connect(self._on_export_excel)
        data_btn_row.addWidget(self.export_excel_btn)

        self.export_csv_btn = QPushButton("📥 导出 CSV")
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        data_btn_row.addWidget(self.export_csv_btn)

        self.analyze_btn = QPushButton("📊 生成分析报告")
        self.analyze_btn.clicked.connect(self._on_analyze)
        data_btn_row.addWidget(self.analyze_btn)

        data_btn_row.addStretch()

        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(300)
        self.task_combo.setToolTip("选择要查看的采集任务")
        self.task_combo.currentIndexChanged.connect(self._on_task_selected)
        data_btn_row.addWidget(QLabel("任务:"))
        data_btn_row.addWidget(self.task_combo)

        self.refresh_data_btn = QPushButton("刷新")
        self.refresh_data_btn.clicked.connect(self._refresh_data_view)
        data_btn_row.addWidget(self.refresh_data_btn)

        data_layout.addLayout(data_btn_row)
        self.tab_widget.addTab(self.data_tab, "📊 数据预览")

        # --- 分析页 ---
        self.analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(self.analysis_tab)
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setFont(QFont("Microsoft YaHei", 10))
        self.analysis_text.setPlaceholderText("采集完成后，点击「生成分析报告」查看文案分析...")
        analysis_layout.addWidget(self.analysis_text)
        self.tab_widget.addTab(self.analysis_tab, "📈 文案分析")

        main_layout.addWidget(self.tab_widget)

        # ===== 底部状态栏 =====
        self.statusBar().showMessage("就绪")

        # 菜单栏
        self._init_menu()

    def _init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        open_dir_action = QAction("打开数据目录", self)
        open_dir_action.triggered.connect(lambda: os.startfile(self.cfg["paths"]["data_dir"]))
        file_menu.addAction(open_dir_action)

        open_export_action = QAction("打开导出目录", self)
        open_export_action.triggered.connect(lambda: os.startfile(self.cfg["paths"]["export_dir"]))
        file_menu.addAction(open_export_action)

        file_menu.addSeparator()
        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")

        config_action = QAction("防封策略设置", self)
        config_action.triggered.connect(self._on_config_dialog)
        settings_menu.addAction(config_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("使用说明", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ========== 事件处理 ==========

    def _on_start(self):
        """点击开始采集"""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return

        max_items = self.count_spin.value()
        download_images = self.download_img_check.isChecked()

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认开始采集",
            f"即将开始采集：\n\n"
            f"关键词：{keyword}\n"
            f"数量：最多 {max_items} 条\n"
            f"下载图片：{'是' if download_images else '否'}\n\n"
            f"⚠ 采集过程会自动打开浏览器窗口，请保持浏览器可见。\n"
            f"⚠ 如果未登录，请在弹出的浏览器中扫码登录。\n"
            f"⚠ 采集过程中请勿手动操作浏览器。\n\n"
            f"是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 更新 UI 状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, max_items)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"正在初始化浏览器...")
        self.log_text.clear()
        self._log("=" * 60, "info")
        self._log(f"开始采集任务：{keyword}", "info")
        self._log(f"目标数量：{max_items} 条", "info")
        self._log("=" * 60, "info")

        # 启动后台线程
        self.worker = CrawlerWorker(keyword, max_items, download_images)
        self.worker.log_signal.connect(self._on_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.login_status_signal.connect(self._on_login_status)
        self.worker.start()

    def _on_stop(self):
        """点击停止采集"""
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止当前采集任务吗？已采集的数据会保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes and self.worker:
            self.worker.stop()
            self._log("用户手动停止采集", "warning")

    def _on_log(self, message, level="info"):
        """接收日志信号"""
        self._log(message, level)

    def _on_progress(self, current, total, message):
        """接收进度信号"""
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_login_status(self, success):
        """接收登录状态"""
        if success:
            self._log("登录状态：已登录 ✅", "success")
        else:
            self._log("等待用户扫码登录...", "warning")

    def _on_finished(self, task_id):
        """采集完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.worker = None

        if task_id:
            self.current_task_id = task_id
            self.status_label.setText(f"采集完成 ✅ 任务ID: {task_id}")
            self._log("=" * 60, "success")
            self._log(f"采集任务 #{task_id} 完成！", "success")
            self._log("=" * 60, "success")

            # 自动刷新数据
            self._load_task_history()
            self._refresh_data_view()

            # 询问是否导出
            reply = QMessageBox.question(
                self, "采集完成",
                f"采集完成！共采集了商品数据。\n\n是否立即导出 Excel？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_export_excel()
        else:
            self.status_label.setText("采集中断或失败")

    def _log(self, message, level="info"):
        """写入日志"""
        colors = {
            "info": "#D4D4D4",
            "success": "#4EC9B0",
            "warning": "#CE9178",
            "error": "#F44747",
            "debug": "#808080",
        }
        color = colors.get(level, "#D4D4D4")

        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.setTextColor(QColor(color))
        self.log_text.insertPlainText(message + "\n")
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    # ========== 数据操作 ==========

    def _load_task_history(self):
        """加载任务历史到下拉框"""
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("全部任务", None)

        tasks = self.db.get_tasks(limit=50)
        for task in tasks:
            label = f"#{task['id']} - {task['keyword']} ({task['item_count']}条) - {task['created_at'][:16]}"
            self.task_combo.addItem(label, task["id"])

        self.task_combo.blockSignals(False)

    def _on_task_selected(self, index):
        """选择任务时刷新数据"""
        task_id = self.task_combo.currentData()
        self.current_task_id = task_id
        self._refresh_data_view()

    def _refresh_data_view(self):
        """刷新数据预览表格"""
        task_id = self.task_combo.currentData()
        items = self.db.get_items(task_id=task_id, limit=200)

        self.data_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.data_table.setItem(i, 1, QTableWidgetItem(item.get("title", "")))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"¥{item.get('price', 0):.2f}"))
            self.data_table.setItem(i, 3, QTableWidgetItem(item.get("location", "")))
            self.data_table.setItem(i, 4, QTableWidgetItem(item.get("seller_name", "")))
            self.data_table.setItem(i, 5, QTableWidgetItem(str(item.get("views", 0))))
            self.data_table.setItem(i, 6, QTableWidgetItem(str(item.get("wants", 0))))
            self.data_table.setItem(i, 7, QTableWidgetItem(str(item.get("collected_at", "")[:16])))

        self.statusBar().showMessage(f"共 {len(items)} 条数据")

    def _on_export_excel(self):
        """导出 Excel"""
        task_id = self.task_combo.currentData()
        keyword = self.keyword_input.text().strip() or "全部"

        try:
            path = self.exporter.export_to_excel(task_id=task_id, keyword=keyword)
            self._log(f"Excel 导出成功: {path}", "success")
            QMessageBox.information(self, "导出成功",
                                    f"Excel 文件已保存到：\n\n{path}\n\n"
                                    "包含三个工作表：商品数据、统计分析、文案汇总")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出时发生错误：\n{e}")

    def _on_export_csv(self):
        """导出 CSV"""
        task_id = self.task_combo.currentData()
        keyword = self.keyword_input.text().strip() or "全部"

        try:
            path = self.exporter.export_to_csv(task_id=task_id, keyword=keyword)
            self._log(f"CSV 导出成功: {path}", "success")
            QMessageBox.information(self, "导出成功", f"CSV 文件已保存到：\n\n{path}")
        except ValueError as e:
            QMessageBox.warning(self, "导出失败", str(e))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出时发生错误：\n{e}")

    def _on_analyze(self):
        """生成分析报告"""
        task_id = self.task_combo.currentData()
        keyword = self.keyword_input.text().strip() or "全部"

        try:
            report_md = self.analyzer.generate_markdown_report(task_id, keyword)
            self.analysis_text.setMarkdown(report_md)
            self.tab_widget.setCurrentIndex(2)  # 切换到分析页
            self._log("分析报告生成完成", "success")

            # 同时保存到文件
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.cfg["paths"]["export_dir"], f"分析报告_{timestamp}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            self._log(f"报告已保存: {report_path}", "info")

        except Exception as e:
            QMessageBox.critical(self, "分析失败", f"生成分析报告时出错：\n{e}")

    # ========== 设置对话框 ==========

    def _on_config_dialog(self):
        """防封策略设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("防封策略设置")
        dialog.setMinimumWidth(450)

        layout = QFormLayout(dialog)

        min_delay = QDoubleSpinBox()
        min_delay.setRange(1.0, 30.0)
        min_delay.setValue(self.cfg["anti_ban"]["min_delay"])
        min_delay.setSuffix(" 秒")
        min_delay.setToolTip("每条商品之间的最小等待时间")
        layout.addRow("最小间隔:", min_delay)

        max_delay = QDoubleSpinBox()
        max_delay.setRange(1.0, 60.0)
        max_delay.setValue(self.cfg["anti_ban"]["max_delay"])
        max_delay.setSuffix(" 秒")
        max_delay.setToolTip("每条商品之间的最大等待时间")
        layout.addRow("最大间隔:", max_delay)

        page_min = QDoubleSpinBox()
        page_min.setRange(2.0, 30.0)
        page_min.setValue(self.cfg["anti_ban"]["page_delay_min"])
        page_min.setSuffix(" 秒")
        page_min.setToolTip("翻页最小等待时间")
        layout.addRow("翻页最小间隔:", page_min)

        page_max = QDoubleSpinBox()
        page_max.setRange(2.0, 60.0)
        page_max.setValue(self.cfg["anti_ban"]["page_delay_max"])
        page_max.setSuffix(" 秒")
        page_max.setToolTip("翻页最大等待时间")
        layout.addRow("翻页最大间隔:", page_max)

        max_items = QSpinBox()
        max_items.setRange(10, 200)
        max_items.setValue(self.cfg["anti_ban"]["max_items_per_session"])
        max_items.setToolTip("单次采集最多商品数")
        layout.addRow("单次最大采集:", max_items)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self._save_config_and_close(
            dialog, min_delay.value(), max_delay.value(),
            page_min.value(), page_max.value(), max_items.value()
        ))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.exec()

    def _save_config_and_close(self, dialog, min_d, max_d, p_min, p_max, m_items):
        """保存配置"""
        self.cfg["anti_ban"]["min_delay"] = min_d
        self.cfg["anti_ban"]["max_delay"] = max_d
        self.cfg["anti_ban"]["page_delay_min"] = p_min
        self.cfg["anti_ban"]["page_delay_max"] = p_max
        self.cfg["anti_ban"]["max_items_per_session"] = m_items

        save_user_config({"anti_ban": self.cfg["anti_ban"]})

        self.anti_ban_label.setText(
            f"🛡 防封保护：间隔 {min_d}-{max_d} 秒 | 单次最多 {m_items} 条"
        )
        dialog.accept()

    # ========== 关于 ==========

    def _on_about(self):
        """显示使用说明"""
        QMessageBox.about(self, "使用说明",
                          """<h2>闲鱼数据调研工具 v1.0</h2>

<p><b>使用步骤：</b></p>
<ol>
<li>输入搜索关键词（如：蓝牙耳机）</li>
<li>设置采集数量（建议30-50条）</li>
<li>点击「开始采集」</li>
<li>在弹出的浏览器中扫码登录闲鱼（仅首次需要）</li>
<li>等待自动采集完成</li>
<li>查看数据并导出 Excel</li>
</ol>

<p><b>🔒 防封说明：</b></p>
<ul>
<li>模拟真人浏览节奏，每条商品间隔3-8秒</li>
<li>单次最多采集100条，不进行大规模批量爬取</li>
<li>Cookie 本地保存，不反复登录</li>
<li>建议每次采集间隔10分钟以上</li>
</ul>

<p><b>⚠ 注意事项：</b></p>
<ul>
<li>仅供个人学习研究使用</li>
<li>请勿用于商业用途或大规模数据采集</li>
<li>采集频率过高可能导致账号被限制</li>
<li>采集过程中请勿手动操作浏览器</li>
</ul>

<p><b>数据存储位置：</b></p>
<ul>
<li>数据库：项目目录/data/xianyu.db</li>
<li>图片：项目目录/images/</li>
<li>导出：项目目录/exports/</li>
</ul>
                          """)

    def closeEvent(self, event):
        """关闭窗口时清理资源"""
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
