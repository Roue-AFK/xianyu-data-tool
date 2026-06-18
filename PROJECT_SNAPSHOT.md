# 🐟 闲鱼数据调研工具 - 项目快照 v12.0

## 项目路径 /workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## gui/main_window.py v12.0 ★ CodeBuddy风格UI
AI助手核心改动:
- QScrollArea + QWidget消息气泡 (替代QTextEdit HTML)
- 每条消息是独立QLabel Widget，支持Markdown渲染
- 用户气泡: 橙色右对齐 (border-radius:16px/4px/16px/16px)
- AI气泡: 白色左对齐带边框 (border-radius:4px/16px/16px/16px)
- 输入框: QTextEdit多行输入 (Enter发送, Shift+Enter换行)
- 自动滚动到底部
- 清空对话: 逐个删除Widget
- 顶部简洁标题栏: 标题+自动执行开关+场景选择+状态徽章

## 其他文件
core/config.py / database.py / crawler.py / analyzer.py / exporter.py / researcher.py / assistant.py (同v11.0)

## 配色
bg=#F5F3EE, card=#FFFFFF, border=#E8E3D9, text=#3D3929, primary=#F5A623, purple=#722ED1

## 启动
python main.py
