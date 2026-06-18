"""
闲鱼数据调研工具 - 数据库模块
使用 SQLite 本地存储所有采集数据
"""

import sqlite3
import os
from datetime import datetime
from .config import get_config


class Database:
    """SQLite 数据库管理器"""

    def __init__(self):
        cfg = get_config()
        self.db_path = cfg["paths"]["db_file"]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 采集任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                platform TEXT DEFAULT '闲鱼',
                status TEXT DEFAULT 'running',
                total_items INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)

        # 商品数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT,
                description TEXT,
                price REAL,
                original_price REAL,
                location TEXT,
                seller_name TEXT,
                seller_level TEXT,
                views INTEGER DEFAULT 0,
                wants INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                category TEXT,
                tags TEXT,
                item_url TEXT,
                main_image_url TEXT,
                local_image_path TEXT,
                extra_data TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 创建索引加速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_task_id ON items(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_keyword ON items(title)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_keyword ON tasks(keyword)
        """)

        self.conn.commit()

    # ========== 任务操作 ==========

    def create_task(self, keyword, platform="闲鱼"):
        """创建新的采集任务"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (keyword, platform, status) VALUES (?, ?, 'running')",
            (keyword, platform)
        )
        self.conn.commit()
        return cursor.lastrowid

    def finish_task(self, task_id):
        """标记任务完成"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status='finished', finished_at=CURRENT_TIMESTAMP, "
            "total_items=(SELECT COUNT(*) FROM items WHERE task_id=?) "
            "WHERE id=?",
            (task_id, task_id)
        )
        self.conn.commit()

    def get_tasks(self, limit=20):
        """获取最近的任务列表"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM items WHERE task_id=t.id) as item_count "
            "FROM tasks t ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_task(self, task_id):
        """获取单个任务详情"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========== 商品数据操作 ==========

    def insert_item(self, task_id, data):
        """插入一条商品数据"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO items (
                task_id, title, description, price, original_price,
                location, seller_name, seller_level,
                views, wants, likes, comments,
                category, tags, item_url,
                main_image_url, local_image_path, extra_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            data.get("title"),
            data.get("description"),
            data.get("price"),
            data.get("original_price"),
            data.get("location"),
            data.get("seller_name"),
            data.get("seller_level"),
            data.get("views", 0),
            data.get("wants", 0),
            data.get("likes", 0),
            data.get("comments", 0),
            data.get("category"),
            data.get("tags"),
            data.get("item_url"),
            data.get("main_image_url"),
            data.get("local_image_path"),
            data.get("extra_data"),
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_items(self, task_id=None, keyword=None, limit=500):
        """查询商品数据"""
        cursor = self.conn.cursor()
        conditions = []
        params = []

        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        if keyword:
            conditions.append("title LIKE ?")
            params.append(f"%{keyword}%")

        where = " AND ".join(conditions) if conditions else "1=1"
        cursor.execute(
            f"SELECT * FROM items WHERE {where} ORDER BY collected_at DESC LIMIT ?",
            params + [limit]
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_item_count(self, task_id=None):
        """统计商品数量"""
        cursor = self.conn.cursor()
        if task_id:
            cursor.execute("SELECT COUNT(*) FROM items WHERE task_id=?", (task_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM items")
        return cursor.fetchone()[0]

    def get_price_stats(self, task_id):
        """获取价格统计"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(wants) as avg_wants,
                AVG(views) as avg_views
            FROM items WHERE task_id=? AND price > 0
        """, (task_id,))
        return dict(cursor.fetchone())

    # ========== 工具方法 ==========

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
