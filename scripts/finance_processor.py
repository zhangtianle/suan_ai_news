#!/usr/bin/env python3
"""
Finance News Processor v1
财经新闻数据处理 - 投资者视角

核心功能:
1. 智能分类 - 按投资领域划分
2. 重要性评分 - 投资价值导向
3. 市场情绪分析 - 多空信号识别
4. 实体提取 - 股票、板块、公司
"""

import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
RAW_DIR = PROJECT_ROOT / "data" / "finance" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "finance" / "processed"

# 投资领域分类关键词
INVESTMENT_CATEGORIES = {
    "宏观政策": [
        "央行", "美联储", "利率", "降息", "加息", "货币政策", "财政政策",
        "GDP", "CPI", "PMI", "通胀", "通缩", "经济数据", "统计局",
        "国常会", "政治局", "发改委", "商务部", "财政部",
        "Fed", "FOMC", "ECB", "利率决议", "缩表", "QE"
    ],
    "A股市场": [
        "A股", "上证", "深证", "创业板", "科创板", "北交所",
        "沪指", "深成指", "两市", "成交额", "北向资金", "南向资金",
        "涨停", "跌停", "龙虎榜", "机构", "游资", "融资", "融券"
    ],
    "美股市场": [
        "美股", "纳指", "道指", "标普", "纳斯达克", "纽交所",
        "道琼斯", "S&P", "NYSE", "NASDAQ", "华尔街", "美联储",
        "科技股", "中概股", "ADR", "FAANG", "七巨头"
    ],
    "港股市场": [
        "港股", "恒指", "恒生指数", "港交所", "HKEX",
        "港股通", "恒生科技", "腾讯", "阿里", "美团", "小米"
    ],
    "行业板块": [
        "半导体", "芯片", "新能源", "光伏", "锂电池", "储能", "风电",
        "白酒", "医药", "生物制药", "医疗器械", "中药",
        "银行", "券商", "保险", "地产", "房地产",
        "汽车", "新能源汽车", "智能驾驶", "汽车零部件",
        "消费电子", "苹果产业链", "消费", "食品饮料",
        "军工", "航天", "通信", "5G", "人工智能", "AI",
        "有色", "煤炭", "石油", "化工", "钢铁", "水泥"
    ],
    "商品期货": [
        "期货", "商品", "原油", "黄金", "白银", "铜", "铝",
        "螺纹钢", "铁矿石", "焦炭", "动力煤",
        "农产品", "大豆", "玉米", "小麦", "棉花", "白糖",
        "OPEC", "减产", "增产", "库存", "供需"
    ],
    "外汇市场": [
        "汇率", "美元", "人民币", "欧元", "日元", "英镑",
        "USD", "CNY", "EUR", "JPY", "GBP",
        "外汇储备", "贬值", "升值", "汇率波动"
    ],
    "基金理财": [
        "基金", "公募", "私募", "ETF", "LOF", "QDII",
        "基金经理", "净值", "申购", "赎回", "定投",
        "权益基金", "债券基金", "货币基金", "指数基金"
    ],
    "财报业绩": [
        "财报", "年报", "季报", "业绩", "营收", "净利润",
        "毛利率", "净利率", "ROE", "EPS", "每股收益",
        "业绩预告", "业绩快报", "分析师", "评级", "研报"
    ],
    "并购重组": [
        "并购", "重组", "收购", "借壳", "定增", "配股",
        "IPO", "上市", "退市", "私有化", "分拆",
        "股权转让", "要约收购", "合并"
    ],
    "风险预警": [
        "暴雷", "违约", "退市", "风险", "调查", "处罚",
        "诉讼", "仲裁", "亏损", "减值", "坏账",
        "质押", "冻结", "破产", "清算"
    ]
}

# 重要公司/股票关键词
KEY_ENTITIES = {
    "科技巨头": ["苹果", "微软", "谷歌", "Meta", "亚马逊", "特斯拉", "英伟达", "Netflix"],
    "中国科技": ["腾讯", "阿里", "字节", "美团", "京东", "拼多多", "百度", "小米", "快手", "B站"],
    "新能源": ["宁德时代", "比亚迪", "蔚来", "理想", "小鹏", "隆基", "阳光电源"],
    "半导体": ["台积电", "中芯国际", "华虹", "北方华创", "韦尔股份"],
    "金融": ["工商银行", "建设银行", "中国平安", "招商银行", "中信证券", "东方财富"],
    "消费": ["茅台", "五粮液", "伊利", "海天", "美的", "格力"]
}

# 市场影响关键词
MARKET_IMPACT = {
    "高影响": [
        "降息", "加息", "QE", "缩表", "利率决议",
        "贸易战", "制裁", "地缘政治", "战争",
        "疫情", "封锁", "衰退", "危机",
        "财报超预期", "业绩暴雷", "重大并购"
    ],
    "中影响": [
        "政策", "规划", "补贴", "监管",
        "业绩", "营收", "利润", "订单",
        "产能", "扩张", "投资"
    ],
    "低影响": [
        "观点", "分析", "预测", "展望",
        "日常", "常规", "一般"
    ]
}

def categorize_article(article):
    """投资领域分类"""
    title = article.get("title", "")
    url = article.get("url", "")
    source_categories = article.get("categories", [])
    existing_entities = article.get("entities", {})
    
    text = (title + " " + url).lower()
    
    match_scores = {}
    
    # 1. 来源预分类加分
    for cat in source_categories:
        cat_mapping = {
            "宏观": "宏观政策", "政策": "宏观政策",
            "股市": "A股市场", "A股": "A股市场",
            "美股": "美股市场", "港股": "港股市场",
            "期货": "商品期货", "商品": "商品期货",
            "基金": "基金理财", "外汇": "外汇市场",
            "财报": "财报业绩", "业绩": "财报业绩",
            "能源": "商品期货", "原油": "商品期货"
        }
        mapped = cat_mapping.get(cat, cat)
        if mapped in INVESTMENT_CATEGORIES:
            match_scores[mapped] = match_scores.get(mapped, 0) + 3
    
    # 2. 关键词匹配
    for category, keywords in INVESTMENT_CATEGORIES.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                if keyword.lower() in title.lower():
                    score += 2
                else:
                    score += 1
        
        if score > 0:
            match_scores[category] = match_scores.get(category, 0) + score
    
    # 3. 实体匹配
    for entity_type, entities in KEY_ENTITIES.items():
        for entity in entities:
            if entity in title:
                # 根据实体类型映射到分类
                if entity_type in ["科技巨头", "中国科技"]:
                    match_scores["A股市场"] = match_scores.get("A股市场", 0) + 1
                elif entity_type == "新能源":
                    match_scores["行业板块"] = match_scores.get("行业板块", 0) + 1
                elif entity_type == "半导体":
                    match_scores["行业板块"] = match_scores.get("行业板块", 0) + 1
    
    # 4. 风险预警特殊处理
    risk_keywords = MARKET_IMPACT["高影响"] + ["暴雷", "违约", "退市", "调查", "处罚"]
    for kw in risk_keywords:
        if kw in title:
            match_scores["风险预警"] = match_scores.get("风险预警", 0) + 5
    
    # 选择得分最高的分类
    sorted_cats = sorted(match_scores.items(), key=lambda x: x[1], reverse=True)
    result = [cat for cat, score in sorted_cats[:3] if score >= 2]
    
    return result if result else ["其他"]

def calculate_investment_score(article):
    """计算投资价值分数"""
    score = 0
    title = article.get("title", "")
    source = article.get("source", "")
    
    # 1. 来源权重
    source_weights = {
        # 高权威媒体
        "证券时报": 5, "上海证券报": 5, "中国证券报": 5, "第一财经": 5,
        "财新网": 5, "21世纪经济报道": 5, "经济观察报": 4,
        # 国际权威
        "Bloomberg": 5, "Reuters": 5, "WSJ": 5, "FT": 5, "CNBC": 4,
        # 门户网站
        "新浪财经": 4, "东方财富": 4, "同花顺": 3,
        # 专业媒体
        "期货日报": 4, "中国基金报": 4,
        # 社区
        "雪球": 2, "淘股吧": 2
    }
    score += source_weights.get(source, 1)
    
    # 2. 市场信号权重
    signal = article.get("market_signal", {})
    overall = signal.get("overall", "neutral")
    if overall == "bullish":
        score += 2
    elif overall == "bearish":
        score += 2  # 利空也同样重要
    
    # 3. 核心关键词
    core_keywords = [
        # 政策类 (最高权重)
        ("降息", 5), ("加息", 5), ("利率决议", 5), ("货币政策", 4),
        ("国常会", 4), ("政治局会议", 4), ("美联储", 5), ("央行", 4),
        
        # 业绩类
        ("财报", 4), ("业绩", 3), ("超预期", 4), ("暴雷", 5),
        
        # 市场类
        ("北向资金", 3), ("机构", 2), ("龙虎榜", 2),
        
        # 公司类
        ("茅台", 3), ("宁德时代", 3), ("比亚迪", 3), ("腾讯", 3),
        ("英伟达", 3), ("特斯拉", 3), ("苹果", 2),
        
        # 风险类
        ("风险", 3), ("调查", 3), ("处罚", 3), ("违约", 4),
        
        # 国际类
        ("贸易战", 4), ("制裁", 4), ("地缘", 3)
    ]
    
    for keyword, weight in core_keywords:
        if keyword in title:
            score += weight
    
    # 4. 时间敏感性
    if any(w in title for w in ["今日", "刚刚", "突发", "重磅", "紧急"]):
        score += 2
    
    # 5. 数据含量
    if re.search(r'\d+(\.\d+)?%', title):  # 包含百分比
        score += 1
    if re.search(r'\d+亿', title):  # 包含金额
        score += 1
    
    # 6. 降权
    if len(title) < 10 or len(title) > 80:
        score -= 1
    
    return max(score, 1)

def extract_key_points(title, content=""):
    """提取关键投资要点"""
    points = []
    text = title + " " + content
    
    # 1. 政策影响
    if any(w in text for w in ["降息", "降准", "宽松"]):
        points.append("货币政策宽松信号")
    if any(w in text for w in ["加息", "收紧", "缩表"]):
        points.append("货币政策收紧信号")
    
    # 2. 行业机会
    sectors = []
    sector_keywords = {
        "半导体": ["半导体", "芯片", "集成电路"],
        "新能源": ["新能源", "光伏", "储能", "锂电池"],
        "医药": ["医药", "创新药", "医疗器械"],
        "消费": ["消费", "零售", "白酒"],
        "金融": ["银行", "券商", "保险"],
        "地产": ["地产", "房地产", "物业"]
    }
    
    for sector, keywords in sector_keywords.items():
        if any(kw in text for kw in keywords):
            sectors.append(sector)
    
    if sectors:
        points.append(f"涉及板块: {', '.join(sectors)}")
    
    # 3. 公司动态
    for entity_type, entities in KEY_ENTITIES.items():
        for entity in entities:
            if entity in text:
                points.append(f"关注标的: {entity}")
                break
    
    return points[:3]  # 最多3个要点

def process_data():
    """处理数据"""
    print(f"[{datetime.now().isoformat()}] 开始处理财经数据...")
    
    all_articles = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for file in RAW_DIR.glob("finance_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                articles = data.get("articles", [])
                all_articles.extend(articles)
        except Exception as e:
            print(f"读取文件失败 {file}: {e}")
    
    # 去重
    seen_ids = set()
    unique_articles = []
    for article in all_articles:
        aid = article.get("id")
        if aid not in seen_ids:
            seen_ids.add(aid)
            unique_articles.append(article)
    
    # 分类和评分
    categorized = defaultdict(list)
    signal_stats = {"bullish": 0, "bearish": 0, "neutral": 0}
    entity_stats = defaultdict(int)
    sector_stats = defaultdict(int)
    
    for article in unique_articles:
        # 投资分类
        categories = categorize_article(article)
        article["investment_categories"] = categories
        
        # 投资价值评分
        article["investment_score"] = calculate_investment_score(article)
        
        # 提取关键要点
        article["key_points"] = extract_key_points(article.get("title", ""))
        
        # 统计
        for cat in categories:
            categorized[cat].append(article)
        
        signal = article.get("market_signal", {}).get("overall", "neutral")
        signal_stats[signal] += 1
        
        entities = article.get("entities", {})
        for company in entities.get("companies", []):
            entity_stats[company] += 1
        for sector in entities.get("sectors", []):
            sector_stats[sector] += 1
    
    # 排序
    for cat in categorized:
        categorized[cat].sort(key=lambda x: x.get("investment_score", 0), reverse=True)
    
    # 保存
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / f"processed_{today}.json"
    
    output_data = {
        "date": today,
        "process_time": datetime.now().isoformat(),
        "total_articles": len(unique_articles),
        "categories": {k: len(v) for k, v in categorized.items()},
        "signal_stats": signal_stats,
        "entity_stats": dict(sorted(entity_stats.items(), key=lambda x: x[1], reverse=True)[:20]),
        "sector_stats": dict(sorted(sector_stats.items(), key=lambda x: x[1], reverse=True)[:15]),
        "categorized_articles": dict(categorized),
        "top_articles": sorted(unique_articles, key=lambda x: x.get("investment_score", 0), reverse=True)[:30],
        "risk_articles": categorized.get("风险预警", [])[:10]
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 处理完成! 共 {len(unique_articles)} 条资讯")
    print(f"\n📊 分类统计:")
    for cat, count in sorted(output_data["categories"].items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count} 条")
    
    print(f"\n📈 市场情绪:")
    print(f"   利好: {signal_stats['bullish']} 条")
    print(f"   利空: {signal_stats['bearish']} 条")
    print(f"   中性: {signal_stats['neutral']} 条")
    
    print(f"\n📁 保存至: {output_file}")
    
    return output_data

if __name__ == "__main__":
    process_data()