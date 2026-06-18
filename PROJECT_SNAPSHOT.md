# 🐟 闲鱼数据调研工具 - 项目快照 v14.2

## 项目路径 /workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## gui/main_window.py v14.2 ★ 思考深度+UI优化
新增:
- 思考深度选择器：底部工具栏pill按钮组 [深度思考|平衡|快速]
  - _on_depth_switch(): 切换深度并同步到assistant
  - 选中态紫色(C.purple #722ED1)，默认"平衡"
- 字体颜色修复：所有工具栏按钮文字 C.text_dim→C.text
  - 模型按钮/自动执行/技能/场景/+更多/StatusBadge
  - hover颜色统一为 C.primary 橙色

修复:
- 删除顶部重复agent_toggle(原L1131)和chat_status_badge(原L1154)
- 删除死代码：chat_scene_combo/chat_type_combo及4个废弃方法

保留:
- StreamWorker(QThread) 流式逐字输出
- Agent Mode 自动执行模式
- WorkBuddy风格底部输入卡片
- 底部完整元素：深度选择/技能▼/场景▼/+/状态/发送

## core/assistant.py v3.2
新增:
- thinking_depth属性: high/medium/low
- _call_api()和chat_stream()根据深度动态调整参数:
  - 高: temperature=0.3, max_tokens=6000 (严谨长文)
  - 中: temperature=0.7, max_tokens=3000 (平衡,默认)
  - 低: temperature=0.9, max_tokens=1500 (快速短输出)

## 配色
bg=#F5F3EE, card=#FFFFFF, primary=#F5A623, purple=#722ED1

## 启动
python main.py
