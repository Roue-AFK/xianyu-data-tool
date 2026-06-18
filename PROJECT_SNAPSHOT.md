# 🐟 闲鱼数据调研工具 - 项目快照 v9.0

## 项目路径
/workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## 文件结构

### core/config.py
DEFAULT_CONFIG: anti_ban/collection/paths/xianyu/ui, get_config()/save_user_config()

### core/database.py
表: tasks + items, 含 delete_task/delete_item 级联删除

### core/crawler.py
XianyuCrawler: launch()+new_context()+storage_state, JS提取, 图片三重兜底

### core/analyzer.py
analyze_price/titles/patterns + generate_markdown_report()

### core/exporter.py
_safe_str/float/int, 三工作表Excel

### core/researcher.py
MarketResearcher: 5提供商(agnes/deepseek/qwen/openai/custom)

### core/assistant.py v2.0
AIAssistant: 6场景+8 MCP工具+需求澄清+本地记忆

### gui/main_window.py v9.0 ★
- 导航栏: logo+版本+关键词+数量(QLineEdit)+AI调研+开始采集+⚙️齿轮
- 6标签页: 仪表盘/AI助手/AI调研/数据预览/文案分析/运行日志
- 仪表盘: 4卡片(均价按类型+ToolTip)+5快捷操作+任务表(右键)
- AI助手(v9.0): 欢迎横幅(渐变背景+头像+5个快捷标签)+大面积对话区+底部输入卡片(圆角输入框+圆角发送按钮+底部场景/类型选择器+清空按钮)
- 快捷标签: 运营策略/文案优化/定价分析/选品建议/客户沟通(点击直接发起)
- 数据预览: 任务选择+表格(右键)
- 设置弹窗: AI配置+防封+采集+界面+记忆路径+配置套件

## 配色
bg=#F5F3EE, card=#FFFFFF, border=#E8E3D9, text=#3D3929, primary=#F5A623, purple=#722ED1

## API Key
Agnes AI: sk-N3fjtDAVQlh2q2FGvbAjxTeqWt0unHUDGRkIKxLKPi4ZQ3q1 (免费)

## 数据路径
数据库: data/xianyu.db | 配置: data/user_config.json | Cookie: data/cookies.json | 导出: exports/ | 图片: images/ | AI记忆: data/ai_memory/

## 启动
python main.py
