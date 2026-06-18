"""
闲鱼数据调研工具 - AI对话助手 v2.0
支持：多轮对话、预设场景、MCP工具调用、AI Agent自主操作、本地记忆
"""

import json
import os
import re
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError


class AIAssistant:
    """AI 对话助手 + Agent - 支持运营咨询、MCP工具、自主操作"""

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

    # MCP 工具定义（完整版 - AI Agent可自主调用）
    MCP_TOOLS = [
        {
            "name": "get_collected_data",
            "description": "获取已采集的商品数据概览，包括总数量、平均价格、热门关键词、任务列表",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_price_analysis",
            "description": "获取指定关键词的价格分析，包括均价、中位数、最高/最低价、价格分布",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "要分析的关键词"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "get_title_trends",
            "description": "获取热门标题文案趋势、高频词统计、标题模式分布",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "要分析的关键词"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "search_suggestions",
            "description": "获取建议的搜索关键词组合，用于发现更多商品",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "基础关键词"}},
                "required": ["keyword"],
            },
        },
        {
            "name": "start_collection",
            "description": "触发采集任务 - 需要用户确认后执行。输入关键词和数量来采集闲鱼商品数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "采集关键词"},
                    "max_items": {"type": "integer", "description": "最大采集数量，默认30"},
                },
                "required": ["keyword"],
            },
        },
        {
            "name": "export_data",
            "description": "导出已采集数据为Excel文件",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "可选：指定关键词过滤"}},
                "required": [],
            },
        },
        {
            "name": "generate_analysis_report",
            "description": "生成完整的文案分析报告（Markdown格式）",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "可选：指定关键词"}},
                "required": [],
            },
        },
        {
            "name": "get_market_research",
            "description": "执行AI市场调研，分析市场热度、品类分布、价格区间、采集建议",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "调研关键词"}},
                "required": ["keyword"],
            },
        },
    ]

    def __init__(self, config=None, db=None, memory_path=None, main_window=None):
        self.config = config or {"enabled": False}
        self.db = db
        self.history = []  # 对话历史（内存）
        self.memory_path = memory_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "ai_memory"
        )
        self.main_window = main_window  # 用于调用GUI功能
        self.thinking_depth = "medium"  # 思考深度: high / medium / low

    # ========== 记忆管理 ==========

    def set_memory_path(self, path):
        """修改记忆保存路径"""
        self.memory_path = path
        os.makedirs(self.memory_path, exist_ok=True)

    def load_memory(self):
        """从本地加载记忆"""
        try:
            mem_file = os.path.join(self.memory_path, "chat_memory.json")
            if os.path.exists(mem_file):
                with open(mem_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
                    return len(self.history)
        except Exception:
            self.history = []
        return 0

    def save_memory(self):
        """保存记忆到本地"""
        try:
            os.makedirs(self.memory_path, exist_ok=True)
            mem_file = os.path.join(self.memory_path, "chat_memory.json")
            data = {
                "updated_at": datetime.now().isoformat(),
                "history": self.history[-50:],  # 最多保存50轮
            }
            with open(mem_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def clear_memory(self):
        """清空本地记忆文件"""
        try:
            mem_file = os.path.join(self.memory_path, "chat_memory.json")
            if os.path.exists(mem_file):
                os.remove(mem_file)
        except Exception:
            pass

    # ========== 需求澄清 ==========

    def check_if_need_clarify(self, message):
        """
        检查用户消息是否需要澄清需求。
        如果消息太模糊或是操作类请求，AI先问问题明确需求。
        返回 None 表示不需要澄清，返回字符串则为澄清问题。
        """
        msg_lower = message.lower().strip()

        # 模糊的采集/操作请求
        fuzzy_patterns = [
            (["采集", "爬", "抓取"], "采集"),
            (["导出", "下载数据"], "导出"),
            (["分析", "报告"], "分析"),
            (["调研", "研究市场"], "调研"),
        ]

        for keywords, action_type in fuzzy_patterns:
            if any(kw in msg_lower for kw in keywords):
                # 检查是否有关键词
                kw = self._extract_keyword(message)
                if not kw:
                    return self._gen_clarify_question(action_type)
                break

        return None

    def _gen_clarify_question(self, action_type):
        """生成需求澄清问题"""
        questions = {
            "采集": "好的，你想采集数据！在开始之前，我需要确认几个信息：\n\n1. **关键词是什么？** 比如「蓝牙耳机」「iPhone 15」\n2. **采集多少条？** 建议30-50条比较合适\n3. **需要下载图片吗？** 图片会占用存储空间\n\n请告诉我关键词，我来帮你开始采集 😊",
            "导出": "你想导出数据！请确认：\n\n1. **导出哪个关键词的数据？** 比如「蓝牙耳机」\n2. **格式偏好？** Excel(.xlsx)还是CSV？\n\n或者直接说「导出全部数据」导出所有采集结果。",
            "分析": "你想分析数据！请问：\n\n1. **分析哪个关键词？** 比如「蓝牙耳机」\n2. **分析什么？** 价格分析、标题趋势、还是完整报告？\n\n或者直接说「分析全部数据」生成完整分析报告。",
            "调研": "好的，让我来做市场调研！请告诉我：\n\n1. **调研什么品类？** 比如「蓝牙耳机」「二手手机」\n2. **关注什么方面？** 价格/竞争/选品建议？\n\n输入关键词我就开始调研 🔍",
        }
        return questions.get(action_type, "请提供更多细节，我好帮你更好地完成任务！")

    # ========== Agent 自动执行模式 ==========

    def set_agent_mode(self, enabled):
        """切换Agent模式"""
        self._agent_mode = enabled

    def parse_agent_action(self, message, keyword=""):
        """
        Agent模式：解析用户消息，返回操作指令。
        返回格式: {
            "action": "exec"|"confirm"|"chat",
            "type": "collect"|"export"|"price_analysis"|"title_analysis"|"research"|"analyze_report"|"data_overview"|"delete",
            "keyword": "...",
            "count": 30,
            "need_clarify": True/False,
            "clarify_msg": "...",
            "confirm_msg": "..."
        }
        """
        msg = message.strip()
        kw = keyword or self._extract_keyword(msg)

        # 提取数量
        count_match = re.search(r'(\d+)\s*[条个]', msg)
        count = int(count_match.group(1)) if count_match else 30

        # ═══ 采集 ═══
        if any(w in msg for w in ["采集", "爬取", "爬", "抓取"]):
            if not kw:
                return {"action": "exec", "need_clarify": True,
                        "clarify_msg": "好的，你想采集数据！请告诉我：\n\n1. **采集什么关键词？** 比如「蓝牙耳机」「iPhone 15」\n2. **采集多少条？** 默认30条\n\n直接说「采集蓝牙耳机30条」就行。"}
            return {"action": "confirm", "type": "collect", "keyword": kw, "count": count,
                    "confirm_msg": f"📥 **确认采集**\n\n• 关键词: **{kw}**\n• 数量: **{count}** 条\n• 将自动打开浏览器\n\n执行吗？"}

        # ═══ 导出 ═══
        if any(w in msg for w in ["导出", "导出数据", "导出excel", "导出表格"]):
            return {"action": "confirm", "type": "export", "keyword": kw,
                    "confirm_msg": f"📊 **确认导出**\n\n• {'关键词: **' + kw + '**' if kw else '**全部数据**'}\n• 格式: Excel (.xlsx)\n\n执行吗？"}

        # ═══ 价格分析 ═══
        if any(w in msg for w in ["价格分析", "分析价格", "价格分布", "均价"]):
            if not kw:
                return {"action": "exec", "need_clarify": True,
                        "clarify_msg": "你想分析哪个关键词的价格？请告诉我关键词，比如「分析蓝牙耳机价格」。"}
            return {"action": "exec", "type": "price_analysis", "keyword": kw}

        # ═══ 标题/文案分析 ═══
        if any(w in msg for w in ["标题分析", "文案分析", "标题趋势", "高频词", "文案趋势"]):
            if not kw:
                return {"action": "exec", "need_clarify": True,
                        "clarify_msg": "你想分析哪个关键词的文案？请告诉我关键词。"}
            return {"action": "exec", "type": "title_analysis", "keyword": kw}

        # ═══ 数据概览 ═══
        if any(w in msg for w in ["数据概览", "数据总览", "有多少数据", "数据统计", "查看数据"]):
            return {"action": "exec", "type": "data_overview"}

        # ═══ 市场调研 ═══
        if any(w in msg for w in ["调研", "市场调研", "市场分析", "研究市场"]):
            if not kw:
                return {"action": "exec", "need_clarify": True,
                        "clarify_msg": "你想调研什么品类？请告诉我关键词，比如「调研蓝牙耳机市场」。"}
            return {"action": "exec", "type": "research", "keyword": kw}

        # ═══ 生成分析报告 ═══
        if any(w in msg for w in ["生成报告", "分析报告", "完整报告", "文案报告"]):
            return {"action": "exec", "type": "analyze_report", "keyword": kw}

        # ═══ 删除 ═══
        if any(w in msg for w in ["删除", "清除数据"]):
            if not kw:
                return {"action": "exec", "need_clarify": True,
                        "clarify_msg": "你想删除哪个关键词的数据？请告诉我关键词。\n\n⚠ 此操作不可恢复！"}
            return {"action": "confirm", "type": "delete_confirm", "keyword": kw,
                    "confirm_msg": f"⚠ **确认删除**\n\n将删除「{kw}」的所有采集数据。\n\n**此操作不可恢复！**\n\n确认吗？回复「确认」执行。"}

        # ═══ 确认/是 ═══
        if msg.strip() in ["确认", "是", "好的", "执行", "确认删除", "ok", "OK", "yes", "Yes"]:
            if hasattr(self.main_window, '_pending_action') and self.main_window._pending_action:
                action = self.main_window._pending_action
                self.main_window._pending_action = None
                return action  # 返回待确认的action直接执行

        # ═══ 取消 ═══
        if msg.strip() in ["取消", "不", "否", "no", "No", "算了"]:
            if hasattr(self.main_window, '_pending_action'):
                self.main_window._pending_action = None
            return {"action": "exec", "type": "chat",
                    "keyword": kw, "original_msg": "已取消操作。还有什么需要？"}

        # ═══ 无法识别 → 普通对话 ═══
        return {"action": "exec", "type": "chat", "keyword": kw}

    # ========== 对话入口 ==========

    def chat(self, user_message, keyword=""):
        """
        发送消息并获取AI回复
        """
        if not self.config.get("enabled") or not self.config.get("api_key"):
            return "⚠ AI助手未配置。请点击导航栏⚙️齿轮按钮 → AI配置中设置 API Key。\n\n推荐使用免费的 Agnes AI：https://platform.agnes-ai.com"

        # 检查是否需要调用MCP工具
        tool_result = self._check_tool_call(user_message, keyword)
        if tool_result:
            return tool_result

        # 构建消息
        system_prompt = self._build_system_prompt(keyword)
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # 添加历史（最近15轮）
        for h in self.history[-15:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        # 调用API
        try:
            reply = self._call_api(messages)

            # 保存历史
            self.history.append({"role": "user", "content": user_message, "time": datetime.now().strftime("%H:%M")})
            self.history.append({"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")})

            # 自动保存记忆
            self.save_memory()

            return reply
        except Exception as e:
            return f"❌ AI调用失败: {str(e)}\n\n请检查API配置或稍后重试。"

    def chat_with_scenario(self, scenario_name, keyword=""):
        """使用预设场景对话"""
        scenario = self.SCENARIOS.get(scenario_name)
        if not scenario:
            return f"未找到场景: {scenario_name}"

        if scenario_name == "自由对话":
            return None

        prompt = scenario["prompt"].format(keyword=keyword) if keyword else scenario["prompt"]
        return self.chat(prompt, keyword)

    def clear_history(self):
        """清空对话历史（内存）"""
        self.history = []

    # ========== 系统提示 ==========

    def _build_system_prompt(self, keyword):
        """构建系统提示词"""
        tools_desc = "\n".join([
            f"- **{t['name']}**: {t['description']}"
            for t in self.MCP_TOOLS
        ])

        return f"""你是闲鱼电商运营助手，也是本软件的AI Agent。你可以帮助用户运营闲鱼店铺，也可以直接操作本软件完成采集、导出、分析等任务。

当前分析关键词：{keyword if keyword else "未指定"}

## 你的能力

### 运营咨询
1. 制定闲鱼运营策略
2. 优化商品标题和描述文案
3. 分析定价策略
4. 提供选品建议
5. 客户沟通话术
6. 分析已采集的数据

### 软件操作（通过MCP工具）
{tools_desc}

## 行为准则
1. **操作前先确认**：当用户请求操作（采集/导出等），如果信息不完整，先问清楚再执行
2. **提供有价值建议**：基于数据和经验给出具体可操作的建议
3. **友好专业**：语气友好但专业，回复使用Markdown格式
4. **安全提醒**：涉及数据删除等操作时提醒用户

## 记忆
你有对话记忆，会记住之前的对话内容。你可以在回复中引用之前讨论过的内容。"""

    # ========== API 调用 ==========

    def _call_api(self, messages):
        """调用大模型API"""
        url = self.config.get("api_url", "")
        if not url:
            raise ValueError("API地址未配置")

        depth_params = {
            "high":   {"temperature": 0.3, "max_tokens": 6000},
            "medium": {"temperature": 0.7, "max_tokens": 3000},
            "low":    {"temperature": 0.9, "max_tokens": 1500},
        }
        dp = depth_params.get(self.thinking_depth, depth_params["medium"])
        data = json.dumps({
            "model": self.config.get("model", "agnes-2.0-flash"),
            "messages": messages,
            "temperature": dp["temperature"],
            "max_tokens": dp["max_tokens"],
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
        }

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

    def chat_stream(self, user_message, keyword=""):
        """流式对话：yield 逐字输出"""
        if not self.config.get("enabled") or not self.config.get("api_key"):
            yield "⚠ AI助手未配置。请点击导航栏⚙️齿轮按钮 → AI配置中设置 API Key。"
            return

        system_prompt = self._build_system_prompt(keyword)
        messages = [{"role": "system", "content": system_prompt}]
        for h in self.history[-15:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        url = self.config.get("api_url", "")
        if not url:
            yield "❌ API地址未配置"
            return

        depth_params = {
            "high":   {"temperature": 0.3, "max_tokens": 6000},
            "medium": {"temperature": 0.7, "max_tokens": 3000},
            "low":    {"temperature": 0.9, "max_tokens": 1500},
        }
        dp = depth_params.get(self.thinking_depth, depth_params["medium"])
        data = json.dumps({
            "model": self.config.get("model", "agnes-2.0-flash"),
            "messages": messages,
            "temperature": dp["temperature"],
            "max_tokens": dp["max_tokens"],
            "stream": True,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
        }

        full_reply = ""
        try:
            import http.client
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(parsed.netloc, timeout=120)
            else:
                conn = http.client.HTTPConnection(parsed.netloc, timeout=120)
            conn.request("POST", parsed.path, body=data, headers=headers)
            resp = conn.getresponse()

            if resp.status != 200:
                yield f"❌ API错误 {resp.status}: {resp.read().decode()[:200]}"
                conn.close()
                return

            buffer = b""
            while True:
                chunk = resp.read(1)
                if not chunk:
                    break
                buffer += chunk
                try:
                    text = buffer.decode("utf-8")
                    while "\n" in text:
                        line, text = text.split("\n", 1)
                        line = line.strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                buffer = b""
                                break
                            try:
                                obj = json.loads(data_str)
                                delta = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    full_reply += delta
                                    yield full_reply
                            except json.JSONDecodeError:
                                pass
                    buffer = text.encode("utf-8") if text else b""
                except UnicodeDecodeError:
                    continue
            conn.close()
        except Exception as e:
            if full_reply:
                yield full_reply
            else:
                yield f"❌ 流式调用失败: {str(e)}"
                return

        # 保存历史
        self.history.append({"role": "user", "content": user_message, "time": datetime.now().strftime("%H:%M")})
        self.history.append({"role": "assistant", "content": full_reply, "time": datetime.now().strftime("%H:%M")})
        self.save_memory()

    # ========== MCP 工具调用检测 ==========

    def _check_tool_call(self, message, keyword):
        """检查用户消息是否需要调用MCP工具"""
        if not self.db:
            return None

        msg_lower = message.lower()

        # 数据概览
        if any(w in msg_lower for w in ["数据概览", "采集了", "有多少数据", "数据统计", "数据总览"]):
            return self._tool_get_data()

        # 价格分析
        if any(w in msg_lower for w in ["价格分析", "均价", "价格区间", "价格分布", "价格情况"]) and keyword:
            return self._tool_price_analysis(keyword)

        # 标题趋势
        if any(w in msg_lower for w in ["标题趋势", "文案趋势", "热门词", "高频词", "标题分析"]) and keyword:
            return self._tool_title_trends(keyword)

        # 搜索建议
        if any(w in msg_lower for w in ["搜索建议", "关键词建议", "怎么搜", "搜什么"]):
            kw = keyword or self._extract_keyword(message)
            if kw:
                return self._tool_search_suggestions(kw)

        # 采集请求（Agent操作）
        if any(w in msg_lower for w in ["开始采集", "采集数据", "帮我采集", "爬一下", "爬取"]) or \
           (any(w in msg_lower for w in ["采集"]) and keyword):
            return self._tool_start_collection(message, keyword)

        # 导出请求
        if any(w in msg_lower for w in ["导出", "导出数据", "导出excel", "导出表格"]):
            kw = keyword or self._extract_keyword(message)
            return self._tool_export_data(kw)

        # 生成分析报告
        if any(w in msg_lower for w in ["生成报告", "分析报告", "文案报告", "完整分析"]):
            kw = keyword or self._extract_keyword(message)
            return self._tool_generate_report(kw)

        # 市场调研
        if any(w in msg_lower for w in ["市场调研", "调研", "市场分析", "研究市场"]):
            kw = keyword or self._extract_keyword(message)
            if kw:
                return self._tool_market_research(kw)

        return None

    def _extract_keyword(self, text):
        """从文本中提取关键词"""
        patterns = [
            r'["「「]([^"」」]+)["」」]',
            r'[关于对针对采集分析调研导出搜索爬]\s*[「「]?([^「」」\s,，。]{2,15})[」」]?',
            r'(?:关键词|关键字|商品|产品|品类)[是为:：]\s*([^\s,，。]{2,15})',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        # 尝试提取引号内容
        return ""

    # ========== MCP 工具实现 ==========

    def _tool_get_data(self):
        """获取数据概览"""
        try:
            total = self.db.get_item_count()
            tasks = self.db.get_tasks(limit=20)

            if total == 0:
                return "📊 **数据概览**\n\n还没有采集任何数据。请先在导航栏输入关键词后点击「开始采集」，或对我说「采集蓝牙耳机」我来引导你。\n\n💡 提示：采集前可以先做AI市场调研，了解市场情况再决定采什么。"

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

            md += f"\n💡 你可以对我说「分析{top_keywords[0][0] if top_keywords else '数据'}的价格」来获取详细分析。"
            return md
        except Exception as e:
            return f"获取数据失败: {e}"

    def _tool_price_analysis(self, keyword):
        """价格分析"""
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
                return f"📊 未找到「{keyword}」的采集数据。请先采集该关键词的商品（对我说「采集{keyword}」）。"

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

            md += f"\n💡 建议定价在 **¥{price['avg']}** 附近，略低于均价更容易成交。"
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

            md += "\n💡 参考高频词优化标题可以提高搜索曝光率。"
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

            md += f"\n💡 提示：尝试不同的关键词组合可以发现更多商品。要开始采集吗？"
            return md
        except Exception as e:
            return f"获取建议失败: {e}"

    def _tool_start_collection(self, message, keyword):
        """Agent触发采集"""
        if not keyword:
            return "请告诉我你想采集什么关键词？比如「采集蓝牙耳机」"

        # 提取数量
        count_match = re.search(r'(\d+)\s*[条个]', message)
        count = int(count_match.group(1)) if count_match else 30
        count = min(count, 100)

        # 如果有主窗口引用，直接设置并触发
        if self.main_window:
            self.main_window.nav_keyword.setText(keyword)
            self.main_window.nav_count.setText(str(count))
            return f"""🚀 **准备采集「{keyword}」**

| 参数 | 值 |
|------|------|
| 关键词 | **{keyword}** |
| 采集数量 | **{count}** 条 |

⚠ 我已经帮你填好参数，请点击导航栏的「**开始采集**」按钮或按回车键确认。

采集过程中会自动打开浏览器，请扫码登录闲鱼。"""
        else:
            return f"🚀 请在导航栏输入关键词「{keyword}」并设置数量为{count}条，然后点击「开始采集」。"

    def _tool_export_data(self, keyword):
        """Agent触发导出"""
        if self.main_window:
            try:
                from core.exporter import Exporter
                exporter = Exporter(self.db)
                path = exporter.export_to_excel(keyword=keyword if keyword else None)
                self.main_window._log(f"✅ AI Agent 导出成功: {path}", "success")
                self.main_window._refresh_data_view()
                return f"✅ **导出成功！**\n\n文件路径：`{path}`\n\n💡 你可以在导出目录找到这个文件。"
            except Exception as e:
                return f"❌ 导出失败: {e}"
        else:
            return "📥 请在「数据预览」标签页选择任务后点击「导出Excel」。"

    def _tool_generate_report(self, keyword):
        """Agent生成分析报告"""
        if self.main_window:
            try:
                from core.analyzer import Analyzer
                analyzer = Analyzer(self.db)
                md = analyzer.generate_markdown_report(None, keyword or "全部")
                self.main_window.analysis_text.setMarkdown(md)
                self.main_window.tab_widget.setCurrentIndex(4)
                self.main_window._log(f"✅ AI Agent 生成分析报告", "success")
                return f"✅ **分析报告已生成！**\n\n已切换到「文案分析」标签页查看。\n\n报告包含：高频词分析、标题模式、价格分布、卖家分布等。"
            except Exception as e:
                return f"❌ 生成报告失败: {e}"
        else:
            return "📊 请在「文案分析」标签页点击「生成分析报告」。"

    def _tool_market_research(self, keyword):
        """Agent执行市场调研"""
        try:
            from core.researcher import MarketResearcher
            mr = MarketResearcher()
            md = mr.generate_markdown_report(keyword)

            if self.main_window:
                self.main_window.research_keyword.setText(keyword)
                self.main_window.research_text.setMarkdown(md)
                self.main_window.tab_widget.setCurrentIndex(2)

            return f"✅ **市场调研完成！**\n\n已对「{keyword}」进行市场调研分析，切换到「AI调研」标签页查看完整报告。\n\n💡 确认调研结果后，可以对我说「采集{keyword}」开始采集数据。"
        except Exception as e:
            return f"❌ 调研失败: {e}"
