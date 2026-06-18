# 🐟 闲鱼数据调研工具 - 项目快照 v14.3

## 项目路径 /workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## gui/main_window.py v14.3 ★ 底部工具栏重构
改动:
- 模型选择从pill按钮组 → 下拉菜单按钮(Agnes▼)，与技能/场景统一风格
- 自动执行从顶部行 → 底部工具栏pill，紧挨模型选择
- 删除输入卡片顶部的top_row整行（更简洁）
- 工具栏顺序: [模型▼] [自动] [深度思考|平衡|快速] [⚡技能▼] [场景▼] [+] ...状态... [↑]

修复:
- QMenu::item 添加 color:{C.text} 修复下拉菜单文字不可见
- 所有工具栏按钮默认色 C.text(#3D3929)，hover C.primary(#F5A623)

保留:
- StreamWorker(QThread) 流式逐字输出
- Agent Mode 自动执行模式
- 思考深度三档: 深度思考/平衡/快速 (紫色选中)
- StatusBadge 状态徽章

## core/assistant.py v3.2
- thinking_depth属性联动temperature/max_tokens参数

## 配色
bg=#F5F3EE, card=#FFFFFF, primary=#F5A623, purple=#722ED1

## 启动
python main.py
