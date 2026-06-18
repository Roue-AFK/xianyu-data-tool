# 🐟 闲鱼数据调研工具 - 项目快照 v13.0

## 项目路径 /workspace/xianyu-tool/
GitHub: https://github.com/Roue-AFK/xianyu-data-tool

## 技术栈
Python 3.11 + PyQt6 + Playwright + SQLite + openpyxl + jieba + Agnes AI API

## gui/main_window.py v13.0 ★ 流式逐字输出
新增:
- StreamWorker(QThread): 流式AI调用线程，chunk_signal逐字发射
- _start_stream(): 创建空气泡+启动流式线程
- _on_stream_chunk(): 实时更新QLabel文本(Markdown)
- _on_stream_done(): 完成时恢复状态
- _scroll_down(): 自动滚动到底部
- 所有对话入口(发送/快捷标签/模板)统一走流式

## core/assistant.py v3.1
新增:
- chat_stream(): 流式对话方法
  用http.client逐字节读取SSE(data: [JSON])
  每个delta.content立即yield
  自动保存历史+记忆

## 效果
AI回复像CodeBuddy一样逐字出现，不是突然弹出整段文字

## 配色
bg=#F5F3EE, card=#FFFFFF, primary=#F5A623

## 启动
python main.py
