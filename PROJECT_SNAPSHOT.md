# 🐟 闲鱼数据调研工具 - 项目快照 v10.0

## 项目路径
/workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## 文件结构

### core/config.py / database.py / crawler.py / analyzer.py / exporter.py / researcher.py / assistant.py
(同v9.0，无变更)

### gui/main_window.py v10.0 ★
新增组件:
- TypingIndicator: Codex风格3点跳动动画(QPainter自绘，正弦波渐显渐隐)
- StatusBadge: AI状态徽章(●颜色点+文字，思考中=黄/就绪=绿/等待=蓝)
- _append_user_bubble(): 用户消息气泡(橙色右对齐，圆角18/4/18/18)
- _append_ai_bubble(): AI消息气泡(黄色背景左对齐，圆角4/18/18/18，带边框)
- _show_typing()/_hide_typing(): 控制动画+状态切换+提供商标签

AI助手UI结构:
- 顶部: 渐变头像+AI名称+StatusBadge+提供商标签+5个快捷标签
- 中部: 消息气泡对话区(HTML渲染)
- 底部: 输入卡片(圆角输入框+TypingIndicator动画+发送按钮)+场景/类型选择器+清空按钮

## 配色
bg=#F5F3EE, card=#FFFFFF, border=#E8E3D9, text=#3D3929, primary=#F5A623, purple=#722ED1

## API Key
Agnes AI: sk-N3fjtDAVQlh2q2FGvbAjxTeqWt0unHUDGRkIKxLKPi4ZQ3q1 (免费)

## 启动
python main.py
