"""
闲鱼数据调研工具 - AI市场调研模块 v2.0
支持：本地规则引擎 + 云端大模型API + API配置管理
"""

import re
import json
import os
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError


class MarketResearcher:
    """AI市场调研器 v2.0 - 规则引擎 + 大模型双模式"""

    # 预设的 API 提供商配置模板
    API_PROVIDERS = {
        "agnes": {
            "name": "Agnes AI ⭐推荐",
            "url": "https://apihub.agnes-ai.com/v1/chat/completions",
            "default_model": "agnes-2.0-flash",
            "price_note": "完全免费",
            "get_key_url": "https://platform.agnes-ai.com",
            "description": "长期免费，无需绑卡充值，文本/图片/视频全模态",
        },
        "deepseek": {
            "name": "DeepSeek",
            "url": "https://api.deepseek.com/v1/chat/completions",
            "default_model": "deepseek-chat",
            "price_note": "约 ¥1/百万token",
            "get_key_url": "https://platform.deepseek.com/api_keys",
        },
        "qwen": {
            "name": "通义千问",
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "default_model": "qwen-plus",
            "price_note": "约 ¥0.8/百万token",
            "get_key_url": "https://dashscope.console.aliyun.com/apiKey",
        },
        "openai": {
            "name": "OpenAI / 兼容接口",
            "url": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-4o-mini",
            "price_note": "约 $0.15/百万token",
            "get_key_url": "https://platform.openai.com/api-keys",
        },
        "custom": {
            "name": "自定义接口",
            "url": "",
            "default_model": "",
            "price_note": "自建/代理服务",
            "get_key_url": "",
        },
    }

    # 本地规则引擎的热门关键词库
    HOT_KEYWORDS_2024 = [
        "iPhone", "iPad", "MacBook", "AirPods", "Apple Watch",
        "华为", "小米", "大疆", "索尼", "任天堂", "Switch",
        "机械键盘", "显卡", "PS5", "Xbox",
        "Lululemon", "Nike", "Adidas", "始祖鸟",
        "乐高", "泡泡玛特", "原神",
        "考研", "公考", "雅思", "托福",
        "露营", "飞盘", "滑雪",
    ]

    CATEGORY_KEYWORDS = {
        "数码电子": ["手机", "电脑", "耳机", "相机", "平板", "手表", "音箱", "键盘", "鼠标", "充电器", "数据线", "显示器"],
        "服饰鞋包": ["鞋", "包", "衣服", "裙子", "外套", "卫衣", "牛仔裤", "运动鞋", "手表"],
        "美妆护肤": ["口红", "粉底", "面膜", "香水", "护肤", "彩妆", "精华", "乳液", "防晒"],
        "家居家电": ["台灯", "沙发", "床垫", "冰箱", "空调", "洗衣机", "微波炉", "电饭煲", "吸尘器"],
        "书籍文具": ["书", "教材", "笔记", "笔", "文具", "考研", "公务员", "考证"],
        "运动户外": ["自行车", "跑步机", "瑜伽", "帐篷", "钓鱼", "球拍", "健身", "露营"],
        "潮玩手办": ["手办", "盲盒", "乐高", "模型", "卡牌", "谷子", "周边"],
        "母婴亲子": ["婴儿", "玩具", "童装", "奶粉", "推车", "早教"],
    }

    def __init__(self, config=None):
        """
        Args:
            config: dict，API配置，如果为None则从文件读取
                {
                    "enabled": True/False,     # 是否启用AI
                    "provider": "deepseek",     # 提供商
                    "api_key": "sk-xxx",        # API密钥
                    "api_url": "https://...",   # API地址
                    "model": "deepseek-chat",   # 模型名
                }
        """
        self.config = config or self._load_config()

    def _config_path(self):
        """配置文件路径"""
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "ai_config.json")

    def _load_config(self):
        """加载AI配置"""
        path = self._config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"enabled": False, "provider": "deepseek", "api_key": "", "api_url": "", "model": ""}

    def save_config(self, config):
        """保存AI配置"""
        path = self._config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        self.config = config

    def is_ai_enabled(self):
        """检查AI是否可用"""
        return self.config.get("enabled", False) and bool(self.config.get("api_key", ""))

    def research(self, keyword):
        """
        市场调研主入口 - AI优先，规则兜底

        Returns:
            dict: 调研报告
        """
        if self.is_ai_enabled():
            try:
                return self._research_with_ai(keyword)
            except Exception as e:
                # AI失败，降级到本地规则
                return self._research_local(keyword, f"AI调用失败({str(e)[:50]})，已降级到本地分析")
        else:
            return self._research_local(keyword)

    # ========== AI 大模型调研 ==========

    def _research_with_ai(self, keyword):
        """使用大模型API进行市场调研"""
        prompt = self._build_prompt(keyword)
        response = self._call_llm(prompt)

        # 尝试解析AI返回的结构化数据
        report = self._parse_ai_response(keyword, response)
        report["research_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report["ai_powered"] = True
        report["model"] = self.config.get("model", "unknown")
        report["raw_response"] = response
        return report

    def _build_prompt(self, keyword):
        """构建给大模型的提示词"""
        return f"""你是一个专业的电商市场分析师。请分析闲鱼平台上关于「{keyword}」的市场情况。

请严格按照以下JSON格式回复（不要包含其他文字）：

```json
{{
    "category": "所属品类（如：数码电子、服饰鞋包、美妆护肤、家居家电、书籍文具、运动户外、潮玩手办、母婴亲子、其他）",
    "market_heat": {{
        "level": "热度等级（极高/较高/中等/较低）",
        "score": 热度分数0-100,
        "analysis": "热度分析说明，100字以内"
    }},
    "search_suggestions": ["建议搜索词1", "建议搜索词2", "建议搜索词3", "建议搜索词4", "建议搜索词5"],
    "price_range": {{
        "min": 预估最低价格数字,
        "max": 预估最高价格数字,
        "avg_range": "常见成交价格区间描述，如：200-500元"
    }},
    "collection_strategy": {{
        "items": "建议采集数量（如：30-50条）",
        "reason": "策略原因说明",
        "focus": "采集时重点关注什么"
    }},
    "title_tips": ["标题文案建议1", "标题文案建议2", "标题文案建议3"],
    "risks": ["风险提示1", "风险提示2"]
}}
```

要求：
1. 基于闲鱼平台特点，考虑二手交易的特殊性
2. 价格区间要符合闲鱼二手市场的实际水平
3. 搜索建议要实用，能帮助用户在闲鱼找到更多相关商品
4. 如果关键词可能涉及违规商品，请在risks中明确指出"""

    def _call_llm(self, prompt):
        """调用大模型API - 带重试机制"""
        import time as _time

        url = self.config.get("api_url", "")
        if not url:
            raise ValueError("API地址未配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['api_key']}",
        }

        data = json.dumps({
            "model": self.config.get("model", "agnes-2.0-flash"),
            "messages": [
                {"role": "system", "content": "你是一个专业的电商市场分析师，请始终用JSON格式回复。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }).encode("utf-8")

        last_error = None
        for attempt in range(3):
            try:
                req = Request(url, data=data, headers=headers, method="POST")
                with urlopen(req, timeout=45) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    content = result["choices"][0]["message"]["content"]
                    return content
            except URLError as e:
                last_error = e
                if hasattr(e, 'code') and e.code == 429:
                    wait = (attempt + 1) * 5
                    _time.sleep(wait)
                    continue
                elif attempt < 2:
                    _time.sleep(2)
                    continue
            except Exception as e:
                last_error = e
                if attempt < 2:
                    _time.sleep(2)
                    continue

        raise Exception(f"API请求失败（重试3次后）: {last_error}")

    def _parse_ai_response(self, keyword, text):
        """解析AI返回的JSON"""
        # 提取JSON块
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个文本
            json_str = text

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 解析失败，使用兜底
            return self._research_local(keyword, "AI返回解析失败，使用本地分析")

        return {
            "keyword": keyword,
            "category": data.get("category", "其他"),
            "market_heat": data.get("market_heat", {}),
            "search_suggestions": data.get("search_suggestions", []),
            "price_reference": {
                "min": data.get("price_range", {}).get("min", 0),
                "max": data.get("price_range", {}).get("max", 9999),
                "avg": data.get("price_range", {}).get("avg_range", "未知"),
            },
            "collection_strategy": data.get("collection_strategy", {}),
            "title_tips": data.get("title_tips", []),
            "risk_warning": data.get("risks", ["✅ 未检测到风险"]),
        }

    # ========== 本地规则引擎（兜底） ==========

    def _research_local(self, keyword, note=""):
        """本地规则引擎调研"""
        category = self._guess_category(keyword)
        heat = self._analyze_heat(keyword, category)

        return {
            "keyword": keyword,
            "research_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ai_powered": False,
            "note": note,
            "category": category,
            "market_heat": heat,
            "search_suggestions": self._gen_suggestions(keyword, category),
            "price_reference": self._estimate_price(category),
            "collection_strategy": self._suggest_strategy(heat["score"]),
            "title_tips": self._gen_title_tips(keyword, category),
            "risk_warning": self._check_risk(keyword),
        }

    def _guess_category(self, keyword):
        for cat, kws in self.CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in keyword:
                    return cat
        return "其他/综合"

    def _analyze_heat(self, keyword, category):
        score = 0
        reasons = []
        for hot in self.HOT_KEYWORDS_2024:
            if hot.lower() in keyword.lower():
                score += 30
                reasons.append(f"命中热门关键词「{hot}」")
                break
        if category in ["数码电子", "潮玩手办"]:
            score += 20
            reasons.append(f"「{category}」是闲鱼热门品类")
        elif category in ["服饰鞋包", "美妆护肤"]:
            score += 15
        elif category != "其他/综合":
            score += 10
        if len(keyword) <= 4:
            score += 10
            reasons.append("短关键词搜索量大")
        if re.search(r'[A-Z]{2,}|\d{2,}', keyword):
            score += 10
            reasons.append("包含品牌/型号，精准搜索")
        if score >= 50: level = "🔥 极高"
        elif score >= 30: level = "🟠 较高"
        elif score >= 15: level = "🟡 中等"
        else: level = "🟢 较低"
        return {"level": level, "score": min(score, 100), "analysis": "；".join(reasons) if reasons else "常规关键词"}

    def _gen_suggestions(self, keyword, category):
        suggestions = [keyword]
        for c in ["全新", "99新", "95新"]:
            suggestions.append(f"{keyword} {c}")
        for t in ["包邮", "急出", "正品"]:
            suggestions.append(f"{keyword} {t}")
        if category == "数码电子":
            suggestions.append(f"{keyword} 国行")
        return suggestions[:6]

    def _estimate_price(self, category):
        prices = {
            "数码电子": (500, 8000, "2000-5000"),
            "服饰鞋包": (50, 2000, "200-800"),
            "美妆护肤": (30, 1000, "100-500"),
            "家居家电": (100, 5000, "500-2000"),
            "书籍文具": (5, 200, "20-80"),
            "运动户外": (100, 3000, "300-1500"),
            "潮玩手办": (50, 3000, "200-1000"),
            "母婴亲子": (30, 1000, "100-500"),
        }
        p = prices.get(category, (0, 9999, "未知"))
        return {"min": p[0], "max": p[1], "avg": p[2]}

    def _suggest_strategy(self, score):
        if score >= 50:
            return {"items": "50-100条", "reason": "热度高商品多，建议多采集", "focus": "关注价格分布和卖家信用"}
        elif score >= 30:
            return {"items": "30-50条", "reason": "热度适中", "focus": "关注标题文案套路和描述模板"}
        else:
            return {"items": "20-30条", "reason": "热度较低", "focus": "关注差异化文案和定价策略"}

    def _gen_title_tips(self, keyword, category):
        tips = [
            f"在标题前加上成色描述，如「99新 {keyword}」",
            f"突出价格优势，如「捡漏价 {keyword}」",
            "包含关键规格参数，增加搜索曝光",
        ]
        if category == "数码电子":
            tips.append("注明国行/港版/美版等版本信息")
        return tips

    def _check_risk(self, keyword):
        risks = []
        if any(w in keyword for w in ["假", "仿", "A货", "高仿"]):
            risks.append("⚠ 检测到敏感词，可能涉及假货风险")
        if any(w in keyword for w in ["刷", "代刷", "代写"]):
            risks.append("⚠ 检测到违规服务关键词")
        return risks if risks else ["✅ 未检测到风险关键词"]

    # ========== 报告生成 ==========

    def generate_markdown_report(self, keyword):
        """生成 Markdown 调研报告"""
        r = self.research(keyword)

        ai_badge = f"🤖 AI模型: {r.get('model', '本地规则')}" if r.get("ai_powered") else "📋 本地规则引擎"
        if r.get("note"):
            ai_badge += f" ({r['note']})"

        md = f"""# 🔍 AI市场调研报告

**关键词**: {keyword}
**调研时间**: {r['research_time']}
**分析引擎**: {ai_badge}

---

## 一、品类分析

| 维度 | 结果 |
|------|------|
| 推测品类 | {r['category']} |
| 市场热度 | {r['market_heat']['level']}（{r['market_heat']['score']}分）|

### 热度分析
{r['market_heat'].get('analysis', '暂无详细分析')}

---

## 二、搜索建议

| 序号 | 建议关键词 |
|------|------------|
"""
        for i, s in enumerate(r.get("search_suggestions", []), 1):
            md += f"| {i} | {s} |\n"

        md += f"""
---

## 三、价格参考

| 维度 | 参考值 |
|------|--------|
| 预估最低价 | ¥{r['price_reference']['min']} |
| 预估最高价 | ¥{r['price_reference']['max']} |
| 常见价格区间 | ¥{r['price_reference']['avg']} |

> 💡 以上价格仅供参考，实际价格以采集结果为准

---

## 四、标题文案建议

"""
        for tip in r.get("title_tips", []):
            md += f"- 💡 {tip}\n"

        md += f"""
---

## 五、采集策略

| 维度 | 建议 |
|------|------|
| 建议采集数量 | {r['collection_strategy']['items']} |
| 策略说明 | {r['collection_strategy']['reason']} |
| 重点关注 | {r['collection_strategy']['focus']} |

---

## 六、风险提示

"""
        for risk in r.get("risk_warning", []):
            md += f"- {risk}\n"

        md += "\n---\n\n*本报告由闲鱼数据调研工具自动生成*\n"
        return md
