"""
闲鱼数据调研工具 - AI市场调研模块
在采集前先分析关键词的市场热度和选品建议
"""

import re
import json
from collections import Counter
from datetime import datetime


class MarketResearcher:
    """AI市场调研器 - 基于关键词分析市场热度、给出选品建议"""

    # 热门品类关键词库
    CATEGORY_KEYWORDS = {
        "数码电子": ["手机", "电脑", "耳机", "相机", "平板", "手表", "音箱", "键盘", "鼠标", "充电器", "数据线", "显示器"],
        "服饰鞋包": ["鞋", "包", "衣服", "裙子", "外套", "卫衣", "牛仔裤", "运动鞋", "包包", "手表"],
        "美妆护肤": ["口红", "粉底", "面膜", "香水", "护肤", "彩妆", "精华", "乳液", "防晒"],
        "家居家电": ["台灯", "沙发", "床垫", "冰箱", "空调", "洗衣机", "微波炉", "电饭煲", "吸尘器"],
        "书籍文具": ["书", "教材", "笔记", "笔", "文具", "考研", "公务员", "考证"],
        "运动户外": ["自行车", "跑步机", "瑜伽", "帐篷", "钓鱼", "球拍", "健身", "露营"],
        "潮玩手办": ["手办", "盲盒", "乐高", "模型", "卡牌", "谷子", "周边"],
        "母婴亲子": ["婴儿", "玩具", "童装", "奶粉", "推车", "早教"],
    }

    # 闲鱼热门关键词（用于判断市场热度）
    HOT_KEYWORDS_2024 = [
        "iPhone", "iPad", "MacBook", "AirPods", "Apple Watch",
        "华为", "小米", "大疆", "索尼", "任天堂", "Switch",
        "机械键盘", "显卡", "PS5", "Xbox",
        "Lululemon", "Nike", "Adidas", "始祖鸟",
        "乐高", "泡泡玛特", "原神",
        "考研", "公考", "雅思", "托福",
        "露营", "飞盘", "滑雪",
    ]

    def __init__(self):
        pass

    def research(self, keyword):
        """
        对关键词进行市场调研分析

        Returns:
            dict: 调研报告
        """
        report = {
            "keyword": keyword,
            "research_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": self._guess_category(keyword),
            "market_heat": self._analyze_heat(keyword),
            "search_suggestions": self._generate_search_suggestions(keyword),
            "price_reference": self._estimate_price_range(keyword),
            "collection_strategy": self._suggest_strategy(keyword),
            "risk_warning": self._check_risk(keyword),
        }
        return report

    def _guess_category(self, keyword):
        """猜测关键词所属品类"""
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in keyword or keyword in kw:
                    return category
        return "其他/综合"

    def _analyze_heat(self, keyword):
        """分析市场热度"""
        heat_score = 0
        reasons = []

        # 检查是否命中热门关键词
        for hot in self.HOT_KEYWORDS_2024:
            if hot.lower() in keyword.lower():
                heat_score += 30
                reasons.append(f"命中热门关键词「{hot}」")

        # 品类热度加分
        category = self._guess_category(keyword)
        if category in ["数码电子", "潮玩手办"]:
            heat_score += 20
            reasons.append(f"「{category}」是闲鱼热门品类")
        elif category in ["服饰鞋包", "美妆护肤"]:
            heat_score += 15
            reasons.append(f"「{category}」品类交易活跃")
        elif category != "其他/综合":
            heat_score += 10
            reasons.append(f"属于「{category}」品类")

        # 关键词长度分析
        if len(keyword) <= 4:
            heat_score += 10
            reasons.append("短关键词搜索量大，竞争激烈")
        elif len(keyword) <= 8:
            heat_score += 5
            reasons.append("关键词长度适中")

        # 品牌/型号加分
        if re.search(r'[A-Z]{2,}|\d{2,}', keyword):
            heat_score += 10
            reasons.append("包含品牌名或型号，精准搜索")

        # 热度等级
        if heat_score >= 50:
            level = "🔥 极高"
        elif heat_score >= 30:
            level = "🟠 较高"
        elif heat_score >= 15:
            level = "🟡 中等"
        else:
            level = "🟢 较低"

        return {
            "score": min(heat_score, 100),
            "level": level,
            "reasons": reasons if reasons else ["常规关键词"],
        }

    def _generate_search_suggestions(self, keyword):
        """生成搜索建议关键词组合"""
        suggestions = [keyword]

        # 加上成色词
        condition_words = ["全新", "99新", "95新", "9成新", "仅拆封", "未拆封"]
        suggestions.extend([f"{keyword} {c}" for c in condition_words[:3]])

        # 加上交易词
        trade_words = ["包邮", "急出", "捡漏", "正品", "国行"]
        suggestions.extend([f"{keyword} {t}" for t in trade_words[:3]])

        # 加上规格词（如果是数码类）
        category = self._guess_category(keyword)
        if category == "数码电子":
            specs = ["256G", "128G", "512G", "Pro", "Max"]
            suggestions.extend([f"{keyword} {s}" for s in specs[:2]])

        return suggestions[:8]

    def _estimate_price_range(self, keyword):
        """估算价格区间"""
        category = self._guess_category(keyword)

        price_ranges = {
            "数码电子": {"min": 500, "max": 8000, "avg": "2000-5000"},
            "服饰鞋包": {"min": 50, "max": 2000, "avg": "200-800"},
            "美妆护肤": {"min": 30, "max": 1000, "avg": "100-500"},
            "家居家电": {"min": 100, "max": 5000, "avg": "500-2000"},
            "书籍文具": {"min": 5, "max": 200, "avg": "20-80"},
            "运动户外": {"min": 100, "max": 3000, "avg": "300-1500"},
            "潮玩手办": {"min": 50, "max": 3000, "avg": "200-1000"},
            "母婴亲子": {"min": 30, "max": 1000, "avg": "100-500"},
        }

        return price_ranges.get(category, {"min": 0, "max": 9999, "avg": "未知"})

    def _suggest_strategy(self, keyword):
        """建议采集策略"""
        heat = self._analyze_heat(keyword)
        category = self._guess_category(keyword)

        if heat["score"] >= 50:
            return {
                "items": "50-100条",
                "reason": "热度高，商品多，建议多采集以获得充分数据",
                "focus": "关注价格分布和卖家信用等级，筛选高性价比商品",
            }
        elif heat["score"] >= 30:
            return {
                "items": "30-50条",
                "reason": "热度适中，采集中等数量即可覆盖主要商品",
                "focus": "关注标题文案套路和描述模板",
            }
        else:
            return {
                "items": "20-30条",
                "reason": "热度较低，商品较少，少量采集即可",
                "focus": "关注差异化文案和定价策略",
            }

    def _check_risk(self, keyword):
        """检查关键词风险"""
        risks = []
        if any(word in keyword for word in ["假", "仿", "A货", "高仿"]):
            risks.append("⚠ 检测到敏感词，可能涉及假货风险")
        if any(word in keyword for word in ["刷", "代刷", "代写"]):
            risks.append("⚠ 检测到违规服务关键词")
        if not risks:
            risks.append("✅ 未检测到风险关键词")
        return risks

    def generate_markdown_report(self, keyword):
        """生成 Markdown 格式的调研报告"""
        r = self.research(keyword)

        md = f"""# 🔍 AI市场调研报告

**关键词**: {keyword}
**调研时间**: {r['research_time']}

---

## 一、品类分析

| 维度 | 结果 |
|------|------|
| 推测品类 | {r['category']} |
| 市场热度 | {r['market_heat']['level']}（{r['market_heat']['score']}分）|

### 热度分析
"""
        for reason in r["market_heat"]["reasons"]:
            md += f"- {reason}\n"

        md += f"""
---

## 二、搜索建议

以下关键词组合可能获得更好的搜索结果：

| 序号 | 建议关键词 |
|------|------------|
"""
        for i, s in enumerate(r["search_suggestions"], 1):
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

## 四、采集策略建议

| 维度 | 建议 |
|------|------|
| 建议采集数量 | {r['collection_strategy']['items']} |
| 策略说明 | {r['collection_strategy']['reason']} |
| 重点关注 | {r['collection_strategy']['focus']} |

---

## 五、风险提示

"""
        for risk in r["risk_warning"]:
            md += f"- {risk}\n"

        md += "\n---\n\n*本报告由闲鱼数据调研工具 AI 模块自动生成*\n"

        return md
