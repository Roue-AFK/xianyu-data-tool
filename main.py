"""
闲鱼数据调研工具 - 主入口
零基础友好：双击运行即可启动图形界面
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 抑制 Qt 字体警告（QFont::setPointSize: Point size <= 0）
import logging
logging.getLogger("PyQt6").setLevel(logging.ERROR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """启动主程序"""
    # 高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("闲鱼数据调研工具")
    app.setOrganizationName("XianyuTool")

    # 设置全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #FAFAFA;
        }
        QGroupBox {
            font-size: 13px;
            font-weight: bold;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 20px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 8px;
        }
        QLineEdit, QSpinBox, QComboBox, QDoubleSpinBox {
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 5px 8px;
            font-size: 13px;
            min-height: 24px;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #FF6B35;
        }
        QPushButton {
            border: 1px solid #D0D0D0;
            border-radius: 4px;
            padding: 6px 16px;
            font-size: 12px;
            background-color: white;
        }
        QPushButton:hover {
            background-color: #F0F0F0;
        }
        QTableWidget {
            gridline-color: #E0E0E0;
            font-size: 12px;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QHeaderView::section {
            background-color: #F5F5F5;
            border: 1px solid #E0E0E0;
            padding: 6px;
            font-weight: bold;
        }
        QTabWidget::pane {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        QTabBar::tab {
            padding: 8px 20px;
            font-size: 12px;
        }
        QTabBar::tab:selected {
            border-bottom: 2px solid #FF6B35;
        }
        QProgressBar {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            text-align: center;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background-color: #FF6B35;
            border-radius: 3px;
        }
        QStatusBar {
            font-size: 11px;
            color: #666;
        }
    """)

    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
