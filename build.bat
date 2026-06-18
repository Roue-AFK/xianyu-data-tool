@echo off
chcp 65001 >nul
echo ============================================
echo   闲鱼数据调研工具 - Windows 打包脚本
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] 安装依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [2/5] 安装 Playwright 浏览器...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [错误] Playwright 浏览器安装失败
    pause
    exit /b 1
)

echo [3/5] 清理旧构建...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [4/5] 开始打包（这可能需要几分钟）...
python -m PyInstaller ^
    --name="闲鱼数据调研工具" ^
    --windowed ^
    --onefile ^
    --icon=NONE ^
    --add-data="core;core" ^
    --add-data="gui;gui" ^
    --hidden-import=playwright.async_api ^
    --hidden-import=playwright._impl ^
    --hidden-import=openpyxl ^
    --hidden-import=jieba ^
    --hidden-import=pandas ^
    --collect-all=playwright ^
    --noconfirm ^
    main.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo [5/5] 打包完成！
echo.
echo 可执行文件位置: dist\闲鱼数据调研工具.exe
echo.
echo ============================================
echo   使用说明:
echo   1. 将 dist\闲鱼数据调研工具.exe 复制到任意目录
echo   2. 双击运行即可
echo   3. 首次运行会在同级目录创建 data/ exports/ images/ 文件夹
echo ============================================

pause
