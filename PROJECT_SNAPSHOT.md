# 🐟 闲鱼数据调研工具 - 项目快照 v14.4

## 项目路径 /workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## gui/main_window.py v14.4 ★ 紧凑工具栏 + 一键更新
改动:
- 底部工具栏全面压缩(WorkBuddy紧凑风格):
  输入框 52→36px, 按钮 26→22px, 深度按钮 22→20px, 发送按钮 32→28px
  卡片圆角 16→12px, 所有边距/间距缩小
  工具栏顺序: [Agnes▼] [自动] [深度思考|平衡|快速] [⚡技能▼] [场景▼] [+] ...状态... [↑]
- 设置面板新增 "🔄 检查更新" 按钮:
  一键 git fetch + reset --hard origin/master
  成功/失败/超时均有弹窗提示

保留:
- StreamWorker(QThread) 流式逐字输出
- Agent Mode 自动执行模式
- 思考深度三档联动API参数
- 模型下拉菜单切换

## core/assistant.py v3.2
- thinking_depth属性联动temperature/max_tokens

## 配色
bg=#F5F3EE, card=#FFFFFF, primary=#F5A623, purple=#722ED1

## 启动
python main.py
