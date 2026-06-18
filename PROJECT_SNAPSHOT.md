# 🐟 闲鱼数据调研工具 - 项目快照 v8.0

## 项目路径
/workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## 文件结构

### core/config.py
DEFAULT_CONFIG: anti_ban/collection/paths/xianyu/ui
get_config()/save_user_config()/_deep_merge()

### core/database.py
表: tasks(id,keyword,platform,status,total_items,created_at,finished_at)
表: items(id,task_id,title,description,price,original_price,location,seller_name,seller_level,views,wants,likes,comments,category,tags,item_url,main_image_url,local_image_path,extra_data,collected_at)
方法: create_task/finish_task/get_tasks/get_task/insert_item/get_items/get_item_count/get_price_stats/delete_item/delete_task

### core/crawler.py
XianyuCrawler: launch()+new_context()+storage_state, JS精确提取, 图片三重兜底

### core/analyzer.py
analyze_price/analyze_titles/analyze_title_patterns/generate_markdown_report()

### core/exporter.py
_safe_str/_safe_float/_safe_int, 三工作表Excel导出

### core/researcher.py
MarketResearcher: 多提供商(agnes/deepseek/qwen/openai/custom), AI优先+本地兜底

### core/assistant.py v2.0
AIAssistant: 6场景+8 MCP工具+需求澄清+本地记忆(chat_memory.json)

### gui/main_window.py v8.0 ★
配色C类, NoWheel*控件, StatCard/QuickCard, CrawlerWorker, SettingsDialog
MainWindow:
- 导航栏: logo+版本+关键词输入+数量(纯QLineEdit无按钮)+AI调研按钮+开始采集+⚙️齿轮
- 6标签页: 仪表盘/AI助手/AI调研/数据预览/文案分析/运行日志
- 仪表盘: 4统计卡片(平均价格按类型分类+ToolTip)+5快捷操作+最近任务表(右键菜单)
- AI助手(v8.0重构): 顶部模板栏(场景Combo+类型Combo+使用模板按钮+清空按钮)+大面积对话区+底部输入栏
  - 自由对话模式: 类型和模板按钮隐藏
  - 模板模式: 选场景→选具体类型→点「使用模板」一键生成
- 数据预览: 任务选择+表格(右键删除/复制/打开)
- 设置弹窗: AI配置+防封+采集+界面+记忆路径+配置套件

## v8.0关键改动
1. AI助手UI重构: 自由对话为主，模板用Combo下拉(先场景后类型)，移除左侧面板
2. 采集数量改为纯QLineEdit输入框，无上下按钮
3. 仪表盘平均价格按任务关键词分类显示，鼠标悬停ToolTip看各类型均价

## 配色
bg=#F5F3EE, card=#FFFFFF, border=#E8E3D9, text=#3D3929, primary=#F5A623, success=#52C41A, danger=#FF4D4F, info=#1890FF, purple=#722ED1

## API Key
Agnes AI: sk-N3fjtDAVQlh2q2FGvbAjxTeqWt0unHUDGRkIKxLKPi4ZQ3q1 (免费)

## 数据路径
数据库: data/xianyu.db | 配置: data/user_config.json | Cookie: data/cookies.json | 导出: exports/ | 图片: images/ | AI记忆: data/ai_memory/

## 启动
python main.py 或 pyinstaller main.py --onefile --windowed
