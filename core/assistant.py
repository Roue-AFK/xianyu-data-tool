"""
闲鱼数据调研工具 - AI对话助手 v1.0
支持多轮对话、预设场景、MCP工具调用
"""

import json
import re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError


class AIAssistant:
    """AI 对话助手 - 支持运营咨询、MCP工具调用"""

    # 预设场景模板
    SCENARIOS = {
        "运营策略": {
            "prompt": "你是一个闲鱼电商运营专家。请针对「{keyword}」这个品类，给出完整的闲鱼运营策略建议，包括：\n1. 账号定位和人设打造\n2. 标题和描述文案技巧\n3. 定价策略\n4. 图片拍摄建议\n5. 发布时间和频率\n6. 如何提升曝光和转化",
            "icon": "📈",
        },
        "文案优化": {
            "prompt": "你是一个顶级电商文案写手。请为闲鱼商品「{keyword}」写5个不同风格的标题模板和对应的描述文案，风格包括：\n1. 真诚实惠型\n2. 专业测评型\n3. 急售捡漏型\n4. 故事营销型\n5. 简单直接型",
            "icon": "✍️",
        },
        "定价分析": {
            "prompt": "你是一个二手市场定价专家。请分析闲鱼上「{keyword}」的定价策略：\n1. 当前市场行情价格区间\n2. 影响价格的关键因素\n3. 如何根据成色/配件/保修定价\n4. 价格谈判技巧\n5. 什么时候适合降价/涨价",
            "icon": "💰",
        },
        "选品建议": {
            "prompt": "你是一个电商选品顾问。请基于「{keyword}」这个方向，给出：\n1. 这个品类在闲鱼的竞争情况\n2. 哪些细分品类更值得做\n3. 货源渠道建议\n4. 利润空间分析\n5. 风险提示和避坑指南",
            "icon": "🎯",
        },
        "客户沟通": {
            "prompt": "你是一个闲鱼客服专家。请针对「{keyword}」商品，给出：\n1. 常见客户问题及标准回复话术\n2. 如何应对砍价\n3. 如何处理售后纠纷\n4. 如何引导好评\n5. 沟通禁忌和注意事项",
            "icon": "💬",
        },
        "自由对话": {
            "prompt": "",
            "icon": "💡",
        },
    }

    # MCP 工具定义（基础版）
    MCP_TOOLS = [
        {
            "name": "get_collected_data",
            "description": "获取已采集的商品数据概览，包括数量、平均价格、热门关键词",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_price_analysis",
            "description": "获取指定关键词的价格分析，包括价格区间、均价、中位数",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "要分析的关键词"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "get_title_trends",
            "description": "获取热门标题文案趋势和常用词汇",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "要分析的关键词"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "search_suggestions",
            "description": "获取建议的搜索关键词组合",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "基础关键词"}},
                "required": ["keyword"],
            },
        },
    ]

    def __init__(self, config=None, db=None):
        self.config = config or {"enabled": False}
        self.db = db
        self.history = []  # 对话历史

    def chat(self, user_message, keyword=""):
        """
        发送消息并获取AI回复

        Returns:
            str: AI 回复内容
        """
        if not self.config.get("enabled") or not self.config.get("api_key"):
            return "⚠ AI助手未配置。请在「设置」→「AI设置」中配置 API Key。\n\n推荐使用免费的 Agnes AI：https://platform.agnes-ai.com"

        # 检查是否需要调用MCP工具
        tool_result = self._check_tool_call(user_message, keyword)
        if tool_result:
            return tool_result

        # 构建消息
        system_prompt = self._build_system_prompt(keyword)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # 添加历史（最近10轮）
        for h in self.history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        # 调用API
        try:
            reply = self._call_api(messages)

            # 保存历史
            self.history.append({"role": "user", "content": user_message, "time": datetime.now().strftime("%H:%M")})
            self.history.append({"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")})

            return reply
        except Exception as e:
            return f"❌ AI调用失败: {str(e)}\n\n请检查API配置或稍后重试。"

    def chat_with_scenario(self, scenario_name, keyword=""):
        """使用预设场景对话"""
        scenario = self.SCENARIOS.get(scenario_name)
        if not scenario:
            return f"未找到场景: {scenario_name}"

        if scenario_name == "自由对话":
            return None  # 返回None表示等待用户输入

        prompt = scenario["prompt"].format(keyword=keyword) if keyword else scenario["prompt"]
        return self.chat(prompt, keyword)

    def clear_history(self):
        """清空对话历史"""
        self.history = []

    def _build_system_prompt(self, keyword):
        """构建系统提示词"""
        tools_desc = "\n".join([
            f"- {t['name']}: {t['description']}"
            for t in self.MCP_TOOLS
        ])

        return f"""你是闲鱼电商运营助手，专门帮助用户在闲鱼平台上更好地运营和销售。

当前分析关键词：{keyword if keyword else "未指定"}

你可以帮助用户：
1. 制定闲鱼运营策略
2. 优化商品标题和描述文案
3. 分析定价策略
4. 提供选品建议
5. 客户沟通话术
6. 分析已采集的数据

可用工具：
{tools_desc}

请用友好、专业的语气回复，给出具体可操作的建议。回复使用 Markdown 格式。"""

    def _call_api(self, messages):
        """调用大模型API"""
        url = self.config.get("api_url", "")
        if not url:
            raise ValueError("API地址未配置")

        data = json.dumps({
            "model": self.config.get("model", "agnes-2.0-flash"),
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 3000,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
        }

        import time
        last_error = None
        for attempt in range(3):
            try:
                req = Request(url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    return result["choices"][0]["message"]["content"]
            except URLError as e:
                last_error = e
                if hasattr(e, 'code') and e.code == 429:
                    time.sleep((attempt + 1) * 5)
                    continue
                elif attempt < 2:
                    time.sleep(2)
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(2)

        raise Exception(f"API请求失败: {last_error}")

    def _check_tool_call(self, message, keyword):
        """检查用户消息是否需要调用MCP工具"""
        if not self.db:
            return None

        msg_lower = message.lower()

        # 数据概览
        if any(w in msg_lower for w in ["数据概览", "采集了", "有多少数据", "数据统计"]):
            return self._tool_get_data()

        # 价格分析
        if any(w in msg_lower for w in ["价格分析", "均价", "价格区间"]) and keyword:
            return self._tool_price_analysis(keyword)

        # 标题趋势
        if any(w in msg_lower for w in ["标题趋势", "文案趋势", "热门词"]) and keyword:
            return self._tool_title_trends(keyword)

        # 搜索建议
        if any(w in msg_lower for w in ["搜索建议", "关键词建议", "怎么搜"]):
            kw = keyword or self._extract_keyword(message)
            if kw:
                return self._tool_search_suggestions(kw)

        return None

    def _extract_keyword(self, text):
        """从文本中提取关键词"""
        patterns = [
            r'["「「]([^"」」]+)["」」]',
            r'[关于对针对]\s*[「「]?([^「」」\s,，。]{2,10})[」」]?',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return ""

    # ========== MCP 工具实现 ==========

    def _tool_get_data(self):
        """获取数据概览"""
        try:
            total = self.db.get_item_count()
            tasks = self.db.get_tasks(limit=20)

            if total == 0:
                return "📊 **数据概览**\n\n还没有采集任何数据。请先在「数据预览」页进行采集。"

            keyword_counts = {}
            for t in tasks:
                kw = t.get("keyword", "")
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + t.get("item_count", 0)

            top_keywords = sorted(keyword_counts.items(), key=lambda x: -x[1])[:5]

            md = f"""📊 **数据概览**

| 指标 | 数值 |
|------|------|
| 总采集商品 | **{total}** 条 |
| 采集任务数 | **{len(tasks)}** 个 |

**热门关键词 TOP5：**
"""
            for i, (kw, cnt) in enumerate(top_keywords, 1):
                md += f"{i}. **{kw}** — {cnt}条\n"

            return md
        except Exception as e:
            return f"获取数据失败: {e}"

    def _tool_price_analysis(self, keyword):
        """价格分析"""
        try:
            from core.analyzer import Analyzer
            analyzer = Analyzer(self.db)

            # 查找匹配的任务
            tasks = self.db.get_tasks(limit=50)
            target_task = None
            for t in tasks:
                if keyword in t.get("keyword", ""):
                    target_task = t
                    break

            if not target_task:
                return f"📊 未找到「{keyword}」的采集数据。请先采集该关键词的商品。"

            price = analyzer.analyze_price(target_task["id"])
            if "error" in price:
                return f"📊 {price['error']}"

            md = f"""💰 **「{keyword}」价格分析**

| 指标 | 数值 |
|------|------|
| 商品总数 | {price['total']} 个 |
| 平均价格 | **¥{price['avg']}** |
| 中位数 | ¥{price['median']} |
| 最低价 | ¥{price['min']} |
| 最高价 | ¥{price['max']} |

**价格分布：**
"""
            for d in price.get("distribution", []):
                bar = "█" * (int(d["rate"].replace("%", "")) // 5)
                md += f"- {d['range']}元: {d['count']}个 ({d['rate']}) {bar}\n"

            return md
        except Exception as e:
            return f"价格分析失败: {e}"

    def _tool_title_trends(self, keyword):
        """标题趋势分析"""
        try:
            from core.analyzer import Analyzer
            analyzer = Analyzer(self.db)

            tasks = self.db.get_tasks(limit=50)
            target_task = None
            for t in tasks:
                if keyword in t.get("keyword", ""):
                    target_task = t
                    break

            if not target_task:
                return f"📊 未找到「{keyword}」的采集数据。"

            titles = analyzer.analyze_titles(target_task["id"])
            patterns = analyzer.analyze_title_patterns(target_task["id"])

            if "error" in titles:
                return f"📊 {titles['error']}"

            md = f"""📝 **「{keyword}」标题趋势**

**高频词 TOP10：**
"""
            for i, w in enumerate(titles.get("words", [])[:10], 1):
                md += f"{i}. **{w['word']}** — {w['count']}次\n"

            md += f"\n**标题特征统计：**\n"
            md += f"- 平均长度: **{titles['avg_title_length']}** 字\n"

            if "error" not in patterns:
                for p in patterns.get("patterns", []):
                    md += f"- {p['name']}: {p['count']}条 ({p['rate']})\n"

            return md
        except Exception as e:
            return f"标题分析失败: {e}"

    def _tool_search_suggestions(self, keyword):
        """搜索建议"""
        try:
            from core.researcher import MarketResearcher
            mr = MarketResearcher()
            suggestions = mr._gen_suggestions(keyword, mr._guess_category(keyword))

            md = f"""🔍 **「{keyword}」搜索建议**

以下关键词组合可提高搜索效率：
"""
            for i, s in enumerate(suggestions, 1):
                md += f"{i}. `{s}`\n"

            md += f"\n💡 提示：尝试不同的关键词组合可以发现更多商品。"
            return md
        except Exception as e:
            return f"获取建议失败: {e}"
