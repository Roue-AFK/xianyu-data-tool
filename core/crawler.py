"""
闲鱼数据调研工具 - 爬虫引擎
基于 Playwright 实现浏览器自动化，内置完整防封策略
"""

import asyncio
import random
import time
import os
import re
import json
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

from .config import get_config
from .database import Database


class XianyuCrawler:
    """闲鱼爬虫引擎 - 模拟真人浏览行为"""

    def __init__(self, db=None, progress_callback=None, log_callback=None):
        """
        Args:
            db: Database 实例
            progress_callback: 进度回调 (current, total, message)
            log_callback: 日志回调 (message, level)
        """
        self.cfg = get_config()
        self.db = db or Database()
        self.progress_callback = progress_callback or (lambda c, t, m: None)
        self.log_callback = log_callback or (lambda m, l="info": None)
        self.browser = None
        self.context = None
        self.page = None
        self.is_running = False
        self.current_task_id = None

    def log(self, message, level="info"):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_callback(f"[{timestamp}] {message}", level)

    def progress(self, current, total, message=""):
        """更新进度"""
        self.progress_callback(current, total, message)

    # ========== 防封策略：随机延迟 ==========

    def _random_delay(self, min_sec=None, max_sec=None):
        """随机等待，模拟真人操作节奏"""
        if min_sec is None:
            min_sec = self.cfg["anti_ban"]["min_delay"]
        if max_sec is None:
            max_sec = self.cfg["anti_ban"]["max_delay"]
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    def _random_scroll(self):
        """随机滚动页面，模拟真人浏览"""
        if not self.page:
            return
        try:
            scroll_distance = random.randint(200, 800)
            self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            time.sleep(random.uniform(0.5, 2.0))
        except Exception:
            pass

    def _random_mouse_move(self):
        """随机移动鼠标"""
        if not self.page or not self.cfg["anti_ban"]["random_mouse_move"]:
            return
        try:
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            self.page.mouse.move(x, y)
            time.sleep(random.uniform(0.3, 1.0))
        except Exception:
            pass

    # ========== 浏览器管理 ==========

    async def _init_browser(self):
        """初始化浏览器 - 使用 launch() 避免 user_data_dir 锁定"""
        from playwright.async_api import async_playwright

        self.log("正在启动浏览器...", "info")

        self.playwright = await async_playwright().start()

        # 启动浏览器（不用持久化上下文，避免锁定问题）
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ],
        )

        # 尝试加载已保存的登录状态
        cookie_file = self.cfg["paths"]["cookie_file"]
        storage_state = None
        if os.path.exists(cookie_file):
            try:
                storage_state = cookie_file
                self.log("已加载上次登录状态", "info")
            except Exception:
                pass

        # 创建上下文
        self.context = await self.browser.new_context(
            viewport={
                "width": self.cfg["xianyu"]["viewport_width"],
                "height": self.cfg["xianyu"]["viewport_height"],
            },
            user_agent=self.cfg["xianyu"]["user_agent"],
            storage_state=storage_state,
        )

        self.page = await self.context.new_page()

        # 注入反检测脚本
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        self.log("浏览器启动成功", "success")

    async def _close_browser(self):
        """关闭浏览器并保存登录状态"""
        try:
            if self.context:
                # 保存 Cookie 到文件
                cookie_file = self.cfg["paths"]["cookie_file"]
                os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                await self.context.storage_state(path=cookie_file)
                self.log("登录状态已保存", "info")

            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            self.log(f"关闭浏览器异常: {e}", "warning")

    # ========== 登录 ==========

    async def login(self):
        """打开闲鱼页面，引导用户登录"""
        await self._init_browser()

        # 先尝试打开闲鱼首页
        self.log("正在打开闲鱼首页...", "info")
        try:
            await self.page.goto(
                self.cfg["xianyu"]["base_url"],
                wait_until="domcontentloaded",
                timeout=30000
            )
        except Exception:
            # 如果 goofish.com 打不开，尝试其他域名
            self.log("主域名加载失败，尝试备用域名...", "warning")
            await self.page.goto(
                "https://www.goofish.com",
                wait_until="domcontentloaded",
                timeout=30000
            )
        await asyncio.sleep(3)

        # 检查是否已登录（通过Cookie）
        is_logged_in = await self._check_login_status()

        if is_logged_in:
            self.log("检测到已登录状态 ✅", "success")
            return True

        # ===== 未登录，引导用户登录 =====
        self.log("", "info")
        self.log("╔══════════════════════════════════════════╗", "warning")
        self.log("║  ⚠ 未检测到登录状态                        ║", "warning")
        self.log("║                                          ║", "warning")
        self.log("║  请在弹出的浏览器中完成以下操作：          ║", "warning")
        self.log("║  1. 点击页面上的「登录」按钮              ║", "warning")
        self.log("║  2. 使用手机闲鱼APP扫码登录               ║", "warning")
        self.log("║  3. 登录成功后程序会自动继续              ║", "warning")
        self.log("╚══════════════════════════════════════════╝", "warning")
        self.log("", "info")

        # 尝试自动跳转到登录页面
        try:
            login_clicked = False
            # 尝试点击页面上的登录按钮
            login_selectors = [
                'a:has-text("登录")',
                'button:has-text("登录")',
                'span:has-text("登录")',
                '[class*="login"]',
                '[class*="Login"]',
            ]
            for sel in login_selectors:
                try:
                    el = self.page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        login_clicked = True
                        self.log("已自动点击登录按钮", "info")
                        break
                except Exception:
                    continue

            if not login_clicked:
                # 直接跳转到登录页面
                self.log("正在跳转到登录页面...", "info")
                await self.page.goto(
                    "https://login.taobao.com/member/login.jhtml?style=mini&from=goofish&full_redirect=true",
                    wait_until="domcontentloaded",
                    timeout=30000
                )
        except Exception:
            pass

        await asyncio.sleep(2)

        # 等待用户登录（最多等 180 秒 = 3分钟）
        self.log("⏳ 等待扫码登录中...（最多等待3分钟）", "warning")

        for i in range(90):
            await asyncio.sleep(2)
            is_logged_in = await self._check_login_status()

            if is_logged_in:
                self.log("登录成功 ✅ 正在保存登录状态...", "success")
                # 立即保存登录状态
                cookie_file = self.cfg["paths"]["cookie_file"]
                os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                await self.context.storage_state(path=cookie_file)
                self.log("登录状态已保存，下次无需重新登录", "info")
                await asyncio.sleep(2)
                return True

            # 每30秒提醒一次
            if i > 0 and i % 15 == 0:
                remaining = 180 - (i * 2)
                self.log(f"⏳ 仍在等待登录... 剩余 {remaining} 秒", "warning")

        self.log("❌ 登录超时（3分钟），请重新尝试", "error")
        return False

    async def _check_login_status(self):
        """检查是否已登录 - 多重检测确保准确性"""
        try:
            current_url = self.page.url

            # 如果还在登录页面，肯定没登录
            if "login" in current_url.lower() or "signin" in current_url.lower():
                return False

            # 检测方式1：查找登录按钮（如果有登录按钮说明没登录）
            try:
                login_btns = await self.page.query_selector_all(
                    'a:has-text("登录"), button:has-text("登录"), [class*="login-btn"], [class*="LoginBtn"]'
                )
                # 如果能找到可见的登录按钮，说明没登录
                for btn in login_btns:
                    if await btn.is_visible():
                        return False
            except Exception:
                pass

            # 检测方式2：查找用户头像/昵称等登录态元素
            try:
                user_elements = await self.page.query_selector_all(
                    '[class*="avatar"], [class*="Avatar"], [class*="user-name"], [class*="userName"], [class*="nick"]'
                )
                if len(user_elements) > 0:
                    # 进一步检查是否有 cookie 中的登录态
                    cookies = await self.context.cookies()
                    has_login_cookie = any(
                        c.get("name") in ["_m_h5_tk", "cookie17", "unb", "sgcookie", "csg"]
                        for c in cookies
                    )
                    if has_login_cookie:
                        return True
            except Exception:
                pass

            # 检测方式3：直接检查关键 Cookie
            try:
                cookies = await self.context.cookies()
                for c in cookies:
                    if c.get("name") in ["unb", "cookie17", "_m_h5_tk"] and c.get("value"):
                        return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    # ========== 核心：搜索与采集 ==========

    async def search_and_collect(self, keyword, max_items=50, download_images=True):
        """
        搜索关键词并采集商品数据

        Args:
            keyword: 搜索关键词
            max_items: 最大采集数量
            download_images: 是否下载图片

        Returns:
            task_id: 任务ID
        """
        if self.is_running:
            self.log("已有采集任务在运行中", "warning")
            return None

        self.is_running = True
        collected = 0
        page_num = 1
        max_pages = self.cfg["anti_ban"]["max_pages"]

        # 确保浏览器已启动
        if not self.page:
            await self._init_browser()

        # 检查登录状态
        if not await self._check_login_status():
            self.log("未检测到登录状态，请先登录", "error")
            self.is_running = False
            return None

        # 创建任务记录
        self.current_task_id = self.db.create_task(keyword)
        self.log(f"开始采集任务 #{self.current_task_id}，关键词: {keyword}", "info")
        self.log(f"防封策略已启用：间隔 {self.cfg['anti_ban']['min_delay']}-{self.cfg['anti_ban']['max_delay']} 秒", "info")

        try:
            while collected < max_items and page_num <= max_pages:
                if not self.is_running:
                    break

                # 构建搜索URL（翻页）
                if page_num == 1:
                    search_url = f"{self.cfg['xianyu']['search_url']}?q={quote(keyword)}"
                else:
                    search_url = f"{self.cfg['xianyu']['search_url']}?q={quote(keyword)}&page={page_num}"

                self.log(f"正在加载第 {page_num} 页...", "info")

                try:
                    await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    self.log(f"第 {page_num} 页加载超时，跳过", "warning")
                    page_num += 1
                    continue

                # 等待列表加载
                await asyncio.sleep(random.uniform(2, 4))
                self._random_scroll()
                self._random_mouse_move()

                # 提取商品列表
                items_on_page = await self._extract_item_list()
                self.log(f"第 {page_num} 页发现 {len(items_on_page)} 个商品", "info")

                if not items_on_page:
                    self.log("未找到更多商品，搜索结束", "info")
                    break

                # 逐个采集商品详情
                for i, item_brief in enumerate(items_on_page):
                    if collected >= max_items or not self.is_running:
                        break

                    try:
                        # 点击进入商品详情页
                        item_data = await self._collect_item_detail(item_brief, download_images)

                        if item_data:
                            self.db.insert_item(self.current_task_id, item_data)
                            collected += 1
                            self.progress(collected, max_items,
                                          f"正在采集: {item_data.get('title', '')[:30]}...")
                            self.log(f"[{collected}/{max_items}] {item_data.get('title', '')[:50]}", "info")
                        else:
                            self.log(f"跳过第 {i+1} 个商品（数据不完整）", "warning")

                    except Exception as e:
                        self.log(f"采集商品异常: {e}", "warning")
                        continue

                    # 防封：每条商品之间随机等待
                    if collected < max_items and self.is_running:
                        delay = self._random_delay()
                        self.log(f"等待 {delay:.1f} 秒后继续...（防封策略）", "debug")

                    # 回到搜索结果页
                    try:
                        await self.page.go_back(wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2, 3))
                    except Exception:
                        # 如果回退失败，重新加载搜索页
                        await self.page.goto(search_url, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2, 4))

                # 翻页前等待
                if collected < max_items and page_num < max_pages:
                    page_delay = random.uniform(
                        self.cfg["anti_ban"]["page_delay_min"],
                        self.cfg["anti_ban"]["page_delay_max"]
                    )
                    self.log(f"翻页等待 {page_delay:.1f} 秒...", "debug")
                    time.sleep(page_delay)

                page_num += 1

            # 完成任务
            self.db.finish_task(self.current_task_id)
            self.log(f"采集完成！共采集 {collected} 条商品数据 ✅", "success")

        except Exception as e:
            self.log(f"采集过程异常: {e}", "error")
        finally:
            self.is_running = False
            # 不关闭浏览器，保持登录态
            # await self._close_browser()

        return self.current_task_id

    async def _extract_item_list(self):
        """从搜索结果页提取商品列表"""
        items = []

        try:
            # 等待列表加载
            await self.page.wait_for_timeout(2000)

            # 尝试多种选择器（闲鱼页面结构可能变化）
            selectors = [
                '[class*="searchItem"]',
                '[class*="item"]',
                '[class*="card"]',
                'a[href*="item"]',
                '[class*="SearchItem"]',
                '[class*="list"] > div',
            ]

            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if len(elements) > 3:  # 找到足够多的元素
                    for el in elements:
                        try:
                            href = await el.get_attribute("href")
                            text = await el.inner_text()
                            if href and "item" in href.lower() and text.strip():
                                items.append({
                                    "url": href if href.startswith("http") else f"https://goofish.com{href}",
                                    "text_preview": text.strip()[:200]
                                })
                        except Exception:
                            continue
                    if items:
                        break

            # 如果上面都没找到，用通用方法提取所有链接
            if not items:
                all_links = await self.page.query_selector_all("a[href]")
                for link in all_links:
                    try:
                        href = await link.get_attribute("href")
                        text = await link.inner_text()
                        if href and "item" in href.lower() and len(text.strip()) > 5:
                            items.append({
                                "url": href if href.startswith("http") else f"https://goofish.com{href}",
                                "text_preview": text.strip()[:200]
                            })
                    except Exception:
                        continue

        except Exception as e:
            self.log(f"提取商品列表异常: {e}", "warning")

        return items[:self.cfg["anti_ban"]["max_items_per_session"]]

    async def _collect_item_detail(self, item_brief, download_images=True):
        """进入商品详情页采集详细数据"""
        url = item_brief.get("url", "")
        if not url:
            return None

        try:
            # 打开详情页
            await self.page.goto(url, wait_until="domcontentloaded", timeout=self.cfg["collection"]["timeout_seconds"] * 1000)
            await asyncio.sleep(random.uniform(2, 4))

            # 模拟真人浏览
            self._random_scroll()
            self._random_mouse_move()
            await asyncio.sleep(random.uniform(1, 2))
            self._random_scroll()

            # 提取数据
            data = {}

            # 标题
            data["title"] = await self._extract_text([
                '[class*="title"]', 'h1', '[class*="Title"]',
                '[class*="name"]', '[data-testid="title"]'
            ])

            # 描述
            data["description"] = await self._extract_text([
                '[class*="desc"]', '[class*="description"]',
                '[class*="content"]', '[class*="detail"]',
                '[class*="Desc"]', 'article'
            ])

            # 价格
            price_text = await self._extract_text([
                '[class*="price"]', '[class*="Price"]',
                '[class*="amount"]', 'span[class*="money"]'
            ])
            data["price"] = self._parse_price(price_text)

            # 原价
            orig_price_text = await self._extract_text([
                '[class*="original"]', '[class*="originPrice"]',
                'del', 's'
            ])
            data["original_price"] = self._parse_price(orig_price_text)

            # 位置
            data["location"] = await self._extract_text([
                '[class*="location"]', '[class*="address"]',
                '[class*="city"]', '[class*="Location"]'
            ])

            # 卖家信息
            data["seller_name"] = await self._extract_text([
                '[class*="seller"]', '[class*="Seller"]',
                '[class*="userName"]', '[class*="nick"]'
            ])

            data["seller_level"] = await self._extract_text([
                '[class*="level"]', '[class*="Level"]',
                '[class*="credit"]'
            ])

            # 浏览/想要数
            data["views"] = self._parse_number(await self._extract_text([
                '[class*="view"]', '[class*="browse"]', '[class*="read"]'
            ]))
            data["wants"] = self._parse_number(await self._extract_text([
                '[class*="want"]', '[class*="like"]', '[class*="favor"]',
                '[class*="Want"]', '[class*="Like"]'
            ]))

            # URL
            data["item_url"] = url

            # 主图
            data["main_image_url"] = await self._extract_image()

            # 下载图片
            if download_images and data["main_image_url"]:
                data["local_image_path"] = await self._download_image(
                    data["main_image_url"], data.get("title", "unknown")
                )
            else:
                data["local_image_path"] = ""

            # 额外数据（JSON 格式保存所有未分类信息）
            data["extra_data"] = json.dumps({
                "collected_from": "搜索结果列表",
                "collected_at": datetime.now().isoformat(),
            }, ensure_ascii=False)

            return data

        except Exception as e:
            self.log(f"采集详情页异常 ({url}): {e}", "warning")
            return None

    async def _extract_text(self, selectors):
        """尝试多个选择器提取文本"""
        for selector in selectors:
            try:
                el = await self.page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        return ""

    def _parse_price(self, text):
        """从文本中解析价格"""
        if not text:
            return 0.0
        # 匹配数字（支持 ¥、￥、元等）
        match = re.search(r'[\d,]+\.?\d*', text.replace(",", ""))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return 0.0
        return 0.0

    def _parse_number(self, text):
        """从文本中解析数字（浏览量、想要数等）"""
        if not text:
            return 0
        # 处理"1.2万"这种格式
        match = re.search(r'([\d.]+)\s*(万|w|W)?', text)
        if match:
            num = float(match.group(1))
            if match.group(2):
                num *= 10000
            return int(num)
        return 0

    async def _extract_image(self):
        """提取商品主图 URL"""
        selectors = [
            'img[class*="main"]', 'img[class*="cover"]',
            'img[class*="Main"]', 'img[class*="pic"]',
            '[class*="swiper"] img', '[class*="carousel"] img',
            'img[src*="alicdn"]', 'img[src*="img.alicdn.com"]',
            'img[src*="goofish"]',
        ]

        for selector in selectors:
            try:
                el = await self.page.query_selector(selector)
                if el:
                    src = await el.get_attribute("src")
                    if src and src.startswith("http") and not src.endswith(".gif"):
                        return src
            except Exception:
                continue

        # 兜底：取页面第一个大图
        try:
            all_imgs = await self.page.query_selector_all("img")
            for img in all_imgs:
                src = await img.get_attribute("src")
                if src and src.startswith("http") and not src.endswith(".gif"):
                    # 检查图片尺寸
                    width = await img.get_attribute("width")
                    if width and int(width) > 100:
                        return src
        except Exception:
            pass

        return ""

    async def _download_image(self, url, title):
        """下载图片到本地"""
        try:
            import aiohttp

            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".jpg"
            if ".png" in url.lower():
                ext = ".png"
            elif ".webp" in url.lower():
                ext = ".webp"

            filename = f"{safe_title}_{timestamp}{ext}"
            filepath = os.path.join(self.cfg["paths"]["image_dir"], filename)

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        # 检查大小
                        max_size = self.cfg["collection"]["max_image_size_mb"] * 1024 * 1024
                        if len(content) <= max_size:
                            with open(filepath, "wb") as f:
                                f.write(content)
                            return filepath

            return ""
        except Exception as e:
            self.log(f"下载图片失败: {e}", "debug")
            return ""

    # ========== 停止采集 ==========

    def stop(self):
        """停止当前采集任务"""
        self.is_running = False
        self.log("正在停止采集...", "warning")


# ========== 便捷函数：在同步环境中调用异步爬虫 ==========

def run_crawler(keyword, max_items=50, download_images=True,
                progress_callback=None, log_callback=None, db=None):
    """
    同步入口：在 GUI 线程中调用爬虫

    Returns:
        task_id: 任务ID
    """
    crawler = XianyuCrawler(
        db=db,
        progress_callback=progress_callback,
        log_callback=log_callback
    )

    async def _run():
        # 登录
        login_success = await crawler.login()
        if not login_success:
            return None
        # 采集
        task_id = await crawler.search_and_collect(
            keyword=keyword,
            max_items=max_items,
            download_images=download_images
        )
        return task_id

    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        crawler.stop()
        return None
    except Exception as e:
        if log_callback:
            log_callback(f"运行异常: {e}", "error")
        return None
