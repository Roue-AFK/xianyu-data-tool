"""
闲鱼数据调研工具 - 爬虫引擎 v2.0
修复：精确选择器、内容过滤、登录流程优化
"""

import asyncio
import random
import time
import os
import re
import json
from urllib.parse import quote
from datetime import datetime

from .config import get_config
from .database import Database


class XianyuCrawler:
    """闲鱼爬虫引擎 v2.0 - 精确采集，过滤推荐内容"""

    # 无效标题关键词（过滤掉推荐区域的内容）
    INVALID_TITLES = [
        "为你推荐", "猜你喜欢", "相关推荐", "看了又看",
        "大家都在看", "热门推荐", "你可能喜欢",
    ]

    def __init__(self, db=None, progress_callback=None, log_callback=None):
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
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_callback(f"[{timestamp}] {message}", level)

    def progress(self, current, total, message=""):
        self.progress_callback(current, total, message)

    # ========== 防封策略 ==========

    def _random_delay(self, min_sec=None, max_sec=None):
        if min_sec is None:
            min_sec = self.cfg["anti_ban"]["min_delay"]
        if max_sec is None:
            max_sec = self.cfg["anti_ban"]["max_delay"]
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    def _random_scroll(self):
        if not self.page:
            return
        try:
            self.page.evaluate(f"window.scrollBy(0, {random.randint(200, 800)})")
            time.sleep(random.uniform(0.5, 2.0))
        except Exception:
            pass

    def _random_mouse_move(self):
        if not self.page:
            return
        try:
            self.page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            time.sleep(random.uniform(0.3, 1.0))
        except Exception:
            pass

    # ========== 浏览器管理 ==========

    async def _init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        self.log("正在启动浏览器...", "info")
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ],
        )

        # 加载已保存的登录状态
        cookie_file = self.cfg["paths"]["cookie_file"]
        storage_state = cookie_file if os.path.exists(cookie_file) else None
        if storage_state:
            self.log("已加载上次登录状态", "info")

        self.context = await self.browser.new_context(
            viewport={
                "width": self.cfg["xianyu"]["viewport_width"],
                "height": self.cfg["xianyu"]["viewport_height"],
            },
            user_agent=self.cfg["xianyu"]["user_agent"],
            storage_state=storage_state,
        )

        self.page = await self.context.new_page()

        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        self.log("浏览器启动成功", "success")

    async def _close_browser(self):
        try:
            if self.context:
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
        """打开闲鱼，引导用户登录"""
        await self._init_browser()

        self.log("正在打开闲鱼...", "info")
        try:
            await self.page.goto(
                "https://www.goofish.com",
                wait_until="domcontentloaded",
                timeout=30000
            )
        except Exception:
            await self.page.goto(
                "https://goofish.com",
                wait_until="domcontentloaded",
                timeout=30000
            )
        await asyncio.sleep(3)

        # 检查是否已登录
        if await self._check_login_status():
            self.log("检测到已登录状态 ✅", "success")
            return True

        # ===== 未登录，引导用户登录 =====
        self.log("", "info")
        self.log("╔══════════════════════════════════════════════╗", "warning")
        self.log("║  ⚠ 未检测到登录状态                            ║", "warning")
        self.log("║                                              ║", "warning")
        self.log("║  请在弹出的浏览器窗口中操作：                   ║", "warning")
        self.log("║  1. 点击页面右上角的「登录」                   ║", "warning")
        self.log("║  2. 会跳转到淘宝/支付宝登录页                  ║", "warning")
        self.log("║  3. 用手机扫码或账号密码登录                   ║", "warning")
        self.log("║  4. 登录成功后会自动跳回闲鱼                   ║", "warning")
        self.log("║  5. 程序会自动检测到登录并继续                 ║", "warning")
        self.log("╚══════════════════════════════════════════════╝", "warning")
        self.log("", "info")

        # 尝试自动点击登录按钮
        try:
            for sel in [
                'a:has-text("登录")', 'button:has-text("登录")',
                'span:has-text("登录")', 'div:has-text("登录") >> nth=0',
            ]:
                try:
                    el = self.page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        self.log("已自动点击登录按钮", "info")
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # 等待用户登录（最多 180 秒）
        self.log("⏳ 等待登录中...（跳转淘宝登录是正常的，登录后会自动跳回闲鱼）", "warning")

        for i in range(90):
            await asyncio.sleep(2)
            if await self._check_login_status():
                self.log("登录成功 ✅ 正在保存登录状态...", "success")
                cookie_file = self.cfg["paths"]["cookie_file"]
                os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                await self.context.storage_state(path=cookie_file)
                self.log("登录状态已保存，下次无需重新登录", "info")
                await asyncio.sleep(2)
                return True

            # 如果当前在淘宝登录页，检查是否需要跳回
            current_url = self.page.url
            if "goofish.com" in current_url and "login" not in current_url.lower():
                # 已经跳回闲鱼了，再检测一次
                await asyncio.sleep(2)
                if await self._check_login_status():
                    self.log("登录成功 ✅", "success")
                    cookie_file = self.cfg["paths"]["cookie_file"]
                    os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
                    await self.context.storage_state(path=cookie_file)
                    return True

            if i > 0 and i % 15 == 0:
                remaining = 180 - (i * 2)
                self.log(f"⏳ 仍在等待登录... 剩余 {remaining} 秒", "warning")

        self.log("❌ 登录超时（3分钟），请重新尝试", "error")
        return False

    async def _check_login_status(self):
        """检查是否已登录 - 通过Cookie判断"""
        try:
            cookies = await self.context.cookies()
            # 闲鱼/淘宝的关键登录Cookie
            login_cookie_names = ["unb", "cookie17", "_m_h5_tk", "csg", "sgcookie", "mtop_partitioned_detect"]
            has_login_cookie = any(
                c.get("name") in login_cookie_names and c.get("value")
                for c in cookies
            )
            return has_login_cookie
        except Exception:
            return False

    # ========== 核心：搜索与采集 ==========

    async def search_and_collect(self, keyword, max_items=50, download_images=True):
        """搜索关键词并采集商品数据"""
        if self.is_running:
            self.log("已有采集任务在运行中", "warning")
            return None

        self.is_running = True
        collected = 0
        page_num = 1
        max_pages = self.cfg["anti_ban"]["max_pages"]

        if not self.page:
            await self._init_browser()

        if not await self._check_login_status():
            self.log("未检测到登录状态，请先登录", "error")
            self.is_running = False
            return None

        self.current_task_id = self.db.create_task(keyword)
        self.log(f"开始采集任务 #{self.current_task_id}，关键词: {keyword}", "info")
        self.log(f"防封策略已启用：间隔 {self.cfg['anti_ban']['min_delay']}-{self.cfg['anti_ban']['max_delay']} 秒", "info")

        try:
            while collected < max_items and page_num <= max_pages:
                if not self.is_running:
                    break

                # 构建搜索URL
                search_url = f"https://www.goofish.com/search?q={quote(keyword)}"
                if page_num > 1:
                    search_url += f"&page={page_num}"

                self.log(f"正在加载第 {page_num} 页...", "info")

                try:
                    await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    self.log(f"第 {page_num} 页加载超时，重试...", "warning")
                    await asyncio.sleep(3)
                    try:
                        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    except Exception:
                        self.log(f"第 {page_num} 页加载失败，跳过", "warning")
                        page_num += 1
                        continue

                # 等待页面动态渲染
                await asyncio.sleep(random.uniform(3, 5))
                self._random_scroll()
                await asyncio.sleep(1)
                self._random_scroll()
                self._random_mouse_move()

                # 提取商品列表
                items_on_page = await self._extract_item_list()
                self.log(f"第 {page_num} 页发现 {len(items_on_page)} 个有效商品", "info")

                if not items_on_page:
                    self.log("未找到更多商品，搜索结束", "info")
                    break

                # 逐个采集
                for i, item_brief in enumerate(items_on_page):
                    if collected >= max_items or not self.is_running:
                        break

                    try:
                        item_data = await self._collect_item_detail(item_brief, download_images)

                        if item_data and self._is_valid_item(item_data):
                            self.db.insert_item(self.current_task_id, item_data)
                            collected += 1
                            self.progress(collected, max_items,
                                          f"正在采集: {item_data.get('title', '')[:30]}...")
                            self.log(f"[{collected}/{max_items}] {item_data.get('title', '')[:50]}", "info")
                        else:
                            self.log(f"跳过第 {i+1} 个商品（无效数据或推荐内容）", "debug")

                    except Exception as e:
                        self.log(f"采集商品异常: {e}", "warning")
                        continue

                    # 防封等待
                    if collected < max_items and self.is_running:
                        delay = self._random_delay()
                        self.log(f"等待 {delay:.1f} 秒...（防封策略）", "debug")

                    # 返回搜索页
                    try:
                        await self.page.go_back(wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2, 3))
                    except Exception:
                        await self.page.goto(search_url, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(2, 4))

                if collected < max_items and page_num < max_pages:
                    page_delay = random.uniform(
                        self.cfg["anti_ban"]["page_delay_min"],
                        self.cfg["anti_ban"]["page_delay_max"]
                    )
                    self.log(f"翻页等待 {page_delay:.1f} 秒...", "debug")
                    time.sleep(page_delay)

                page_num += 1

            self.db.finish_task(self.current_task_id)
            self.log(f"采集完成！共采集 {collected} 条商品数据 ✅", "success")

        except Exception as e:
            self.log(f"采集过程异常: {e}", "error")
        finally:
            self.is_running = False

        return self.current_task_id

    def _is_valid_item(self, data):
        """过滤无效商品和推荐内容"""
        title = data.get("title", "")
        if not title or len(title) < 3:
            return False
        # 过滤推荐区域的标题
        for invalid in self.INVALID_TITLES:
            if invalid in title:
                return False
        # 标题不能全是数字或符号
        if re.match(r'^[\d\s\W]+$', title):
            return False
        return True

    async def _extract_item_list(self):
        """从搜索结果页精确提取商品列表"""
        items = []

        try:
            await self.page.wait_for_timeout(3000)

            # 方式1：通过 JavaScript 直接提取商品数据（最可靠）
            js_result = await self.page.evaluate("""
                () => {
                    const items = [];

                    // 闲鱼商品链接格式：/item?id=xxx 或包含 goofish.com/item
                    const allLinks = document.querySelectorAll('a[href*="item"]');

                    allLinks.forEach(link => {
                        const href = link.getAttribute('href') || '';
                        // 只保留商品详情链接
                        if (!href.includes('/item') && !href.includes('item?id=')) return;

                        // 获取链接所在的商品卡片容器
                        let card = link;
                        for (let i = 0; i < 5; i++) {
                            if (card.parentElement) card = card.parentElement;
                            const text = card.innerText || '';
                            // 找到包含价格信息的容器
                            if (text.includes('¥') || text.includes('元') || text.length > 20) break;
                        }

                        const text = (card.innerText || '').trim();
                        const title = (link.innerText || '').trim();

                        // 过滤推荐区域
                        if (text.includes('为你推荐') || text.includes('猜你喜欢')) return;
                        if (title.includes('为你推荐') || title.includes('猜你喜欢')) return;
                        if (title.length < 3) return;

                        const fullUrl = href.startsWith('http') ? href :
                                       href.startsWith('//') ? 'https:' + href :
                                       'https://www.goofish.com' + href;

                        // 提取价格
                        const priceMatch = text.match(/[¥￥]\\s*([\\d,]+\\.?\\d*)/);
                        const price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : 0;

                        items.push({
                            url: fullUrl,
                            title: title.substring(0, 200),
                            price: price,
                            text_preview: text.substring(0, 300)
                        });
                    });

                    // 去重
                    const seen = new Set();
                    return items.filter(item => {
                        if (seen.has(item.url)) return false;
                        seen.add(item.url);
                        return true;
                    });
                }
            """)

            if js_result and len(js_result) > 0:
                self.log(f"JS提取到 {len(js_result)} 个商品", "debug")
                return js_result[:self.cfg["anti_ban"]["max_items_per_session"]]

            # 方式2：CSS选择器兜底
            selectors = [
                'a[href*="/item?id="]',
                'a[href*="goofish.com/item"]',
                '[class*="search-item"]',
                '[class*="SearchItem"]',
                '[class*="feeds-item"]',
                '[class*="item-card"]',
            ]

            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if len(elements) > 2:
                    for el in elements:
                        try:
                            href = await el.get_attribute("href")
                            text = await el.inner_text()
                            if href and "/item" in href and text.strip():
                                # 过滤推荐
                                if any(inv in text for inv in self.INVALID_TITLES):
                                    continue
                                full_url = href if href.startswith("http") else f"https://www.goofish.com{href}"
                                items.append({
                                    "url": full_url,
                                    "title": text.strip()[:200],
                                    "text_preview": text.strip()[:300]
                                })
                        except Exception:
                            continue
                    if items:
                        break

        except Exception as e:
            self.log(f"提取商品列表异常: {e}", "warning")

        # 去重
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        return unique[:self.cfg["anti_ban"]["max_items_per_session"]]

    async def _collect_item_detail(self, item_brief, download_images=True):
        """采集商品详情页数据"""
        url = item_brief.get("url", "")
        if not url:
            return None

        try:
            await self.page.goto(url, wait_until="domcontentloaded",
                                 timeout=self.cfg["collection"]["timeout_seconds"] * 1000)
            await asyncio.sleep(random.uniform(2, 4))

            self._random_scroll()
            self._random_mouse_move()
            await asyncio.sleep(random.uniform(1, 2))
            self._random_scroll()

            # 使用 JS 一次性提取所有数据
            data = await self.page.evaluate("""
                () => {
                    const result = {};

                    // 标题：优先取 h1，其次取 class 包含 title 的元素
                    const titleEl = document.querySelector('h1') ||
                                   document.querySelector('[class*="title"]') ||
                                   document.querySelector('[class*="Title"]');
                    // 过滤掉推荐标题
                    const titleText = titleEl ? titleEl.innerText.trim() : '';
                    const invalidTitles = ['为你推荐', '猜你喜欢', '相关推荐', '看了又看'];
                    result.title = invalidTitles.some(t => titleText.includes(t)) ? '' : titleText;

                    // 描述
                    const descEl = document.querySelector('[class*="desc"]') ||
                                  document.querySelector('[class*="Desc"]') ||
                                  document.querySelector('[class*="content"]') ||
                                  document.querySelector('[class*="detail"]') ||
                                  document.querySelector('article');
                    result.description = descEl ? descEl.innerText.trim() : '';

                    // 价格
                    const priceEl = document.querySelector('[class*="price"]') ||
                                   document.querySelector('[class*="Price"]');
                    const priceText = priceEl ? priceEl.innerText : '';
                    const priceMatch = priceText.match(/[¥￥]?\\s*([\\d,]+\\.?\\d*)/);
                    result.price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : 0;

                    // 原价
                    const origEl = document.querySelector('[class*="original"]') ||
                                  document.querySelector('[class*="originPrice"]') ||
                                  document.querySelector('del') ||
                                  document.querySelector('s');
                    const origText = origEl ? origEl.innerText : '';
                    const origMatch = origText.match(/[\\d,]+\\.?\\d*/);
                    result.original_price = origMatch ? parseFloat(origMatch[0].replace(',', '')) : 0;

                    // 位置
                    const locEl = document.querySelector('[class*="location"]') ||
                                 document.querySelector('[class*="address"]') ||
                                 document.querySelector('[class*="city"]');
                    result.location = locEl ? locEl.innerText.trim() : '';

                    // 卖家
                    const sellerEl = document.querySelector('[class*="seller"]') ||
                                    document.querySelector('[class*="Seller"]') ||
                                    document.querySelector('[class*="userName"]');
                    result.seller_name = sellerEl ? sellerEl.innerText.trim() : '';

                    // 卖家等级
                    const levelEl = document.querySelector('[class*="level"]') ||
                                   document.querySelector('[class*="credit"]');
                    result.seller_level = levelEl ? levelEl.innerText.trim() : '';

                    // 浏览/想要数
                    const allText = document.body.innerText;
                    const viewMatch = allText.match(/(?:浏览|看过|阅读)[\\s:：]*(\\d+)/);
                    result.views = viewMatch ? parseInt(viewMatch[1]) : 0;

                    const wantMatch = allText.match(/(?:想要|收藏|喜欢|赞)[\\s:：]*(\\d+)/);
                    result.wants = wantMatch ? parseInt(wantMatch[1]) : 0;

                    // 主图
                    const imgEl = document.querySelector('img[class*="main"]') ||
                                 document.querySelector('img[class*="cover"]') ||
                                 document.querySelector('img[class*="pic"]') ||
                                 document.querySelector('[class*="swiper"] img') ||
                                 document.querySelector('img[src*="alicdn"]');
                    result.main_image_url = imgEl ? (imgEl.getAttribute('src') || '') : '';

                    return result;
                }
            """)

            if not data:
                data = {}

            # 补充信息
            data["item_url"] = url

            # 如果列表页已经提取到标题，用它补充
            if not data.get("title") and item_brief.get("title"):
                data["title"] = item_brief["title"]
            if not data.get("price") and item_brief.get("price"):
                data["price"] = item_brief["price"]

            # 下载图片
            if download_images and data.get("main_image_url"):
                data["local_image_path"] = await self._download_image(
                    data["main_image_url"], data.get("title", "unknown")
                )
            else:
                data["local_image_path"] = ""

            data["extra_data"] = json.dumps({
                "collected_from": "搜索结果列表",
                "collected_at": datetime.now().isoformat(),
            }, ensure_ascii=False)

            return data

        except Exception as e:
            self.log(f"采集详情页异常 ({url}): {e}", "warning")
            return None

    async def _download_image(self, url, title):
        """下载图片 - 使用浏览器上下文绕过防盗链"""
        if not url or not url.startswith("http"):
            return ""

        try:
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:50]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".jpg"
            if ".png" in url.lower(): ext = ".png"
            elif ".webp" in url.lower(): ext = ".webp"

            filename = f"{safe_title}_{timestamp}{ext}"
            filepath = os.path.join(self.cfg["paths"]["image_dir"], filename)

            # 方式1：浏览器上下文请求
            try:
                response = await self.context.request.get(url, timeout=15000, headers={
                    "Referer": "https://www.goofish.com/",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                })
                if response.ok:
                    content = await response.body()
                    if content and len(content) > 100:
                        max_size = self.cfg["collection"]["max_image_size_mb"] * 1024 * 1024
                        if len(content) <= max_size:
                            with open(filepath, "wb") as f:
                                f.write(content)
                            return filepath
            except Exception:
                pass

            # 方式2：截图方式
            try:
                img_page = await self.context.new_page()
                await img_page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1)
                img_el = await img_page.query_selector("img")
                if img_el:
                    await img_el.screenshot(path=filepath)
                    await img_page.close()
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
                        return filepath
                await img_page.close()
            except Exception:
                pass

            return ""
        except Exception as e:
            self.log(f"下载图片失败: {e}", "debug")
            return ""

    def stop(self):
        self.is_running = False
        self.log("正在停止采集...", "warning")
