#!/bin/bash
# 闲鱼数据调研工具 - 打包脚本 (Linux/Mac)
set -e

echo "============================================"
echo "  闲鱼数据调研工具 - 打包脚本"
echo "============================================"

echo "[1/4] 安装依赖..."
pip install -r requirements.txt

echo "[2/4] 安装 Playwright 浏览器..."
python -m playwright install chromium

echo "[3/4] 清理旧构建..."
rm -rf dist build

echo "[4/4] 开始打包..."
python -m PyInstaller \
    --name="闲鱼数据调研工具" \
    --windowed \
    --onefile \
    --add-data="core:core" \
    --add-data="gui:gui" \
    --hidden-import=playwright.async_api \
    --hidden-import=playwright._impl \
    --hidden-import=openpyxl \
    --hidden-import=jieba \
    --hidden-import=pandas \
    --collect-all=playwright \
    --noconfirm \
    main.py

echo "打包完成！"
echo "可执行文件: dist/闲鱼数据调研工具"
