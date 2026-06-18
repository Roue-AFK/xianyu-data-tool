# 🐟 闲鱼数据调研工具 - 项目快照 v11.0

## 项目路径
/workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## 文件结构

### gui/main_window.py v11.0 ★
AI助手新增:
- agent_toggle: 「自动执行」复选框开关(顶部状态栏)
- _on_agent_mode_toggled(): 切换Agent/对话模式
- _execute_agent_action(): 执行Agent操作(collect/export/price_analysis/title_analysis/research/analyze_report/data_overview/delete_confirm)
- _on_send_message(): 重写，Agent模式先解析意图再执行

Agent模式流程:
1. 用户勾选「自动执行」→ AI提示可执行的操作
2. 用户说「采集蓝牙耳机30条」→ AI解析意图
3. 危险操作(采集/删除/导出) → AI先确认再执行
4. 安全操作(分析/调研/概览) → 直接执行并返回结果
5. 模糊指令 → AI追问具体需求

### core/assistant.py v3.0
新增:
- set_agent_mode(enabled): 切换Agent模式
- parse_agent_action(msg, kw): 解析用户指令返回action dict
  支持: collect/export/price_analysis/title_analysis/research/analyze_report/data_overview/delete_confirm/chat

## 配色
bg=#F5F3EE, card=#FFFFFF, border=#E8E3D9, text=#3D3929, primary=#F5A623, purple=#722ED1

## 启动
python main.py
