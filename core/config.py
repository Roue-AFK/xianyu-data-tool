"""
闲鱼数据调研工具 - 配置管理
管理所有可调参数：防封策略、采集限制、路径配置等
"""

import os
import json

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认配置
DEFAULT_CONFIG = {
    # ========== 防封策略（重中之重）==========
    "anti_ban": {
        "min_delay": 3.0,           # 每条商品之间最小等待（秒）
        "max_delay": 8.0,           # 每条商品之间最大等待（秒）
        "page_delay_min": 5.0,      # 翻页最小等待（秒）
        "page_delay_max": 15.0,     # 翻页最大等待（秒）
        "max_items_per_session": 100,  # 单次最多采集数量
        "max_pages": 10,            # 最多翻页数
        "scroll_slowly": True,      # 是否缓慢滚动（模拟真人）
        "random_mouse_move": True,  # 是否随机移动鼠标
    },

    # ========== 采集设置 ==========
    "collection": {
        "download_images": True,     # 是否下载图片
        "max_image_size_mb": 5,      # 单张图片最大下载大小
        "image_quality": 80,         # 图片保存质量（1-100）
        "save_html_snapshot": False, # 是否保存页面快照
        "timeout_seconds": 30,       # 单个商品采集超时
    },

    # ========== 存储路径 ==========
    "paths": {
        "data_dir": os.path.join(ROOT_DIR, "data"),
        "export_dir": os.path.join(ROOT_DIR, "exports"),
        "image_dir": os.path.join(ROOT_DIR, "images"),
        "cookie_file": os.path.join(ROOT_DIR, "data", "cookies.json"),
        "db_file": os.path.join(ROOT_DIR, "data", "xianyu.db"),
    },

    # ========== 闲鱼搜索配置 ==========
    "xianyu": {
        "base_url": "https://goofish.com",  # 闲鱼网页版
        "search_url": "https://www.goofish.com/search",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport_width": 1920,
        "viewport_height": 1080,
    },

    # ========== 界面设置 ==========
    "ui": {
        "window_title": "闲鱼数据调研工具 v1.0",
        "window_width": 1100,
        "window_height": 750,
        "theme": "light",
        "font_size": 12,
    }
}


def get_config():
    """加载配置，优先使用用户自定义配置"""
    config = DEFAULT_CONFIG.copy()

    user_config_path = os.path.join(ROOT_DIR, "data", "user_config.json")
    if os.path.exists(user_config_path):
        try:
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # 深度合并
            _deep_merge(config, user_config)
        except Exception:
            pass  # 用户配置损坏则使用默认

    return config


def save_user_config(config):
    """保存用户自定义配置"""
    user_config_path = os.path.join(ROOT_DIR, "data", "user_config.json")
    os.makedirs(os.path.dirname(user_config_path), exist_ok=True)
    with open(user_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(base, override):
    """深度合并两个字典"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# 模块加载时确保必要目录存在
cfg = get_config()
for path_key in ["data_dir", "export_dir", "image_dir"]:
    os.makedirs(cfg["paths"][path_key], exist_ok=True)
