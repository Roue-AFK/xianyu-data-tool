"""
闲鱼数据调研工具 - 数据分析模块
文案分析、价格分析、高频词统计、对比报告
"""

import re
import os
from collections import Counter
from datetime import datetime

import jieba


class Analyzer:
    """数据分析器 - 对采集到的商品数据进行多维度分析"""

    # 中文停用词（常见无意义词）
    STOP_WORDS = set([
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
        "所", "为", "所以", "因为", "但是", "然而", "可以", "还是", "这个",
        "那个", "什么", "怎么", "如果", "的话", "吧", "啊", "呢", "哦", "嗯",
        "还有", "而且", "然后", "已经", "非常", "比较", "真的", "比较",
        "全新", "二手", "包邮", "正品", "转卖", "闲置", "出售", "转让",
        "购买", "下单", "咨询", "私聊", "联系",
    ])

    def __init__(self, db):
        self.db = db

    # ========== 文案分析 ==========

    def analyze_titles(self, task_id=None, top_n=50):
        """标题高频词分析"""
        items = self.db.get_items(task_id=task_id, limit=1000)
        if not items:
            return {"error": "没有数据", "words": [], "title_count": 0}

        all_words = []
        title_lengths = []

        for item in items:
            title = item.get("title", "")
            if title:
                title_lengths.append(len(title))
                # 中文分词
                words = jieba.cut(title)
                for w in words:
                    w = w.strip()
                    if len(w) >= 2 and w not in self.STOP_WORDS and not w.isdigit():
                        all_words.append(w)

        # 词频统计
        word_counter = Counter(all_words)
        top_words = word_counter.most_common(top_n)

        # 标题长度统计
        avg_length = sum(title_lengths) / len(title_lengths) if title_lengths else 0

        return {
            "words": [{"word": w, "count": c} for w, c in top_words],
            "title_count": len(title_lengths),
            "avg_title_length": round(avg_length, 1),
            "min_title_length": min(title_lengths) if title_lengths else 0,
            "max_title_length": max(title_lengths) if title_lengths else 0,
        }

    def analyze_descriptions(self, task_id=None, top_n=50):
        """描述文案高频词分析"""
        items = self.db.get_items(task_id=task_id, limit=1000)
        if not items:
            return {"error": "没有数据", "words": [], "desc_count": 0}

        all_words = []
        desc_lengths = []
        has_desc = 0

        for item in items:
            desc = item.get("description", "")
            if desc and len(desc) > 5:
                has_desc += 1
                desc_lengths.append(len(desc))
                words = jieba.cut(desc)
                for w in words:
                    w = w.strip()
                    if len(w) >= 2 and w not in self.STOP_WORDS and not w.isdigit():
                        all_words.append(w)

        word_counter = Counter(all_words)
        top_words = word_counter.most_common(top_n)

        avg_length = sum(desc_lengths) / len(desc_lengths) if desc_lengths else 0

        return {
            "words": [{"word": w, "count": c} for w, c in top_words],
            "desc_count": has_desc,
            "total_count": len(items),
            "desc_rate": round(has_desc / len(items) * 100, 1) if items else 0,
            "avg_desc_length": round(avg_length, 1),
        }

    def analyze_title_patterns(self, task_id=None):
        """标题结构分析：常用模板和套路"""
        items = self.db.get_items(task_id=task_id, limit=200)
        if not items:
            return {"error": "没有数据", "patterns": []}

        patterns = {
            "带emoji": 0,
            "带价格": 0,
            "带品牌": 0,
            "带成色": 0,
            "带包邮": 0,
            "带急出": 0,
            "带地名": 0,
        }

        brand_keywords = [
            "苹果", "华为", "小米", "三星", "OPPO", "vivo", "索尼", "戴尔",
            "联想", "惠普", "华硕", "耐克", "阿迪", "LV", "Gucci", "香奈儿",
            "iPhone", "iPad", "MacBook", "AirPods", "Nike", "Adidas"
        ]

        condition_keywords = ["全新", "九成新", "八成新", "99新", "95新", "几乎全新", "仅拆封"]

        for item in items:
            title = item.get("title", "")
            if not title:
                continue

            if re.search(r'[\U0001F300-\U0001F9FF]', title):
                patterns["带emoji"] += 1
            if re.search(r'[¥￥\d]+元?', title):
                patterns["带价格"] += 1
            if any(brand in title for brand in brand_keywords):
                patterns["带品牌"] += 1
            if any(cond in title for cond in condition_keywords):
                patterns["带成色"] += 1
            if "包邮" in title:
                patterns["带包邮"] += 1
            if "急出" in title or "急售" in title:
                patterns["带急出"] += 1
            if re.search(r'[北上广深杭成渝]|广州|深圳|杭州|成都|重庆|武汉|南京', title):
                patterns["带地名"] += 1

        total = len(items)
        return {
            "total": total,
            "patterns": [
                {"name": k, "count": v, "rate": f"{round(v/total*100, 1)}%"}
                for k, v in sorted(patterns.items(), key=lambda x: -x[1])
            ]
        }

    # ========== 价格分析 ==========

    def analyze_price(self, task_id=None):
        """价格区间分析"""
        items = self.db.get_items(task_id=task_id, limit=1000)
        if not items:
            return {"error": "没有数据"}

        prices = [item["price"] for item in items if item.get("price", 0) > 0]
        if not prices:
            return {"error": "没有有效价格数据"}

        prices.sort()

        # 价格区间分布
        if max(prices) <= 100:
            bins = [0, 10, 20, 30, 50, 80, 100]
        elif max(prices) <= 500:
            bins = [0, 50, 100, 150, 200, 300, 500]
        elif max(prices) <= 2000:
            bins = [0, 100, 200, 500, 800, 1200, 2000]
        else:
            bins = [0, 200, 500, 1000, 2000, 5000, float("inf")]

        distribution = []
        for i in range(len(bins) - 1):
            low, high = bins[i], bins[i+1]
            count = sum(1 for p in prices if low <= p < high)
            if count > 0:
                label = f"{low}-{high}" if high != float("inf") else f"{low}+"
                distribution.append({
                    "range": label,
                    "count": count,
                    "rate": f"{round(count/len(prices)*100, 1)}%"
                })

        return {
            "total": len(prices),
            "avg": round(sum(prices) / len(prices), 2),
            "median": round(prices[len(prices)//2], 2),
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "distribution": distribution,
        }

    # ========== 卖家分析 ==========

    def analyze_sellers(self, task_id=None):
        """卖家分布分析"""
        items = self.db.get_items(task_id=task_id, limit=1000)
        if not items:
            return {"error": "没有数据"}

        # 位置分布
        locations = Counter(
            item["location"] for item in items if item.get("location")
        )
        top_locations = locations.most_common(10)

        # 卖家等级分布
        levels = Counter(
            item["seller_level"] for item in items if item.get("seller_level")
        )

        return {
            "total_sellers": len(set(item.get("seller_name", "") for item in items)),
            "top_locations": [{"name": loc, "count": cnt} for loc, cnt in top_locations],
            "seller_levels": [{"level": lv, "count": cnt} for lv, cnt in levels.most_common()],
        }

    # ========== 综合报告 ==========

    def generate_report(self, task_id=None, keyword=""):
        """生成综合分析报告"""
        report = {
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "keyword": keyword,
            "task_id": task_id,
            "titles": self.analyze_titles(task_id),
            "descriptions": self.analyze_descriptions(task_id),
            "title_patterns": self.analyze_title_patterns(task_id),
            "price": self.analyze_price(task_id),
            "sellers": self.analyze_sellers(task_id),
        }
        return report

    def generate_markdown_report(self, task_id=None, keyword=""):
        """生成 Markdown 格式的分析报告"""
        report = self.generate_report(task_id, keyword)

        md = f"""# 📊 闲鱼竞品文案分析报告

**关键词**: {keyword}
**生成时间**: {report['report_time']}
**任务ID**: {task_id}

---

## 一、标题文案分析

"""
        titles = report["titles"]
        if "error" not in titles:
            md += f"- 分析标题数：{titles['title_count']} 条\n"
            md += f"- 平均标题长度：{titles['avg_title_length']} 字\n"
            md += f"- 最短/最长：{titles['min_title_length']} / {titles['max_title_length']} 字\n\n"

            md += "### 🔥 标题高频词 TOP 20\n\n"
            md += "| 排名 | 关键词 | 出现次数 |\n"
            md += "|------|--------|----------|\n"
            for i, w in enumerate(titles["words"][:20], 1):
                md += f"| {i} | {w['word']} | {w['count']} |\n"

            # 标题模板
            patterns = report["title_patterns"]
            if "error" not in patterns:
                md += "\n### 📝 标题结构分析\n\n"
                md += "| 特征 | 数量 | 占比 |\n"
                md += "|------|------|------|\n"
                for p in patterns.get("patterns", []):
                    md += f"| {p['name']} | {p['count']} | {p['rate']} |\n"
        else:
            md += "暂无数据\n"

        # 价格分析
        md += "\n---\n\n## 二、价格分析\n\n"
        price = report["price"]
        if "error" not in price:
            md += f"- 商品总数：{price['total']} 个\n"
            md += f"- 平均价格：¥{price['avg']}\n"
            md += f"- 中位数：¥{price['median']}\n"
            md += f"- 最低/最高：¥{price['min']} / ¥{price['max']}\n\n"

            md += "### 价格区间分布\n\n"
            md += "| 价格区间 | 数量 | 占比 |\n"
            md += "|----------|------|------|\n"
            for d in price.get("distribution", []):
                md += f"| {d['range']}元 | {d['count']} | {d['rate']} |\n"
        else:
            md += "暂无数据\n"

        # 卖家分析
        md += "\n---\n\n## 三、卖家分布\n\n"
        sellers = report["sellers"]
        if "error" not in sellers:
            md += f"- 不同卖家数：{sellers['total_sellers']} 个\n\n"
            md += "### 📍 地区分布 TOP 10\n\n"
            md += "| 地区 | 商品数 |\n"
            md += "|------|--------|\n"
            for loc in sellers.get("top_locations", []):
                md += f"| {loc['name']} | {loc['count']} |\n"
        else:
            md += "暂无数据\n"

        # 描述分析
        md += "\n---\n\n## 四、描述文案分析\n\n"
        descs = report["descriptions"]
        if "error" not in descs:
            md += f"- 有描述的商品：{descs['desc_count']}/{descs['total_count']}（{descs['desc_rate']}%）\n"
            md += f"- 平均描述长度：{descs['avg_desc_length']} 字\n\n"
            md += "### 🔥 描述高频词 TOP 20\n\n"
            md += "| 排名 | 关键词 | 出现次数 |\n"
            md += "|------|--------|----------|\n"
            for i, w in enumerate(descs["words"][:20], 1):
                md += f"| {i} | {w['word']} | {w['count']} |\n"
        else:
            md += "暂无数据\n"

        md += "\n---\n\n"
        md += "*本报告由闲鱼数据调研工具自动生成*\n"

        return md
