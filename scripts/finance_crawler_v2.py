#!/usr/bin/env python3
"""
财经新闻爬虫 - 支持A股和美股市场
基于事件驱动分析框架
"""

import json
import re
import time
import random
from datetime import datetime
from pathlib import Path
import hashlib
import subprocess
import html

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOGS_DIR = PROJECT_ROOT / "logs"

# A股数据源
A_STOCK_SOURCES = [
    # 国内科技媒体
    {"name": "IT之家", "url": "https://www.ithome.com", "type": "tech_news", "market": "A股", "category": ["科技", "半导体", "AI"]},
    {"name": "InfoQ", "url": "https://www.infoq.cn", "type": "tech_media", "market": "A股", "category": ["技术", "AI"]},
    {"name": "量子位", "url": "https://www.qbitai.com", "type": "ai_media", "market": "A股", "category": ["AI", "大模型"]},
    {"name": "虎嗅", "url": "https://www.huxiu.com", "type": "media", "market": "A股", "category": ["科技", "商业"]},
    {"name": "雷锋网", "url": "https://www.leiphone.com", "type": "ai_media", "market": "A股", "category": ["AI", "科技"]},
    # 财经媒体
    {"name": "东方财富", "url": "https://www.eastmoney.com", "type": "finance", "market": "A股", "category": ["股票", "基金"]},
    {"name": "同花顺", "url": "https://www.10jqka.com.cn", "type": "finance", "market": "A股", "category": ["股票", "行情"]},
]

# 美股数据源
US_STOCK_SOURCES = [
    {"name": "TechCrunch", "url": "https://techcrunch.com", "type": "international", "market": "美股", "category": ["科技", "创业"]},
    {"name": "TheVerge", "url": "https://www.theverge.com", "type": "international", "market": "美股", "category": ["科技", "数码"]},
    {"name": "Wired", "url": "https://www.wired.com", "type": "international", "market": "美股", "category": ["科技", "文化"]},
    {"name": "CNBC", "url": "https://www.cnbc.com", "type": "finance", "market": "美股", "category": ["财经", "股票"]},
    {"name": "Bloomberg", "url": "https://www.bloomberg.com", "type": "finance", "market": "美股", "category": ["财经", "投资"]},
]

# 关键词权重（用于新闻影响分析）
KEYWORD_WEIGHTS = {
    # 高权重 - 政策落地
    "政策落地": 5, "政府工作报告": 5, "产业政策": 5, "国家支持": 5,
    # 高权重 - 业绩兑现
    "业绩增长": 5, "净利润": 4, "营收增长": 4, "超预期": 4,
    # 中权重 - 行业趋势
    "量产": 4, "突破": 4, "发布": 3, "上市": 3,
    # 中权重 - 资金流向
    "北向资金": 3, "机构买入": 3, "增持": 3,
    # 标签
    "AI": 3, "新能源": 3, "半导体": 3, "芯片": 3,
    "GPT": 3, "大模型": 3, "算力": 3,
    "宁德时代": 3, "比亚迪": 3, "英伟达": 3, "NVDA": 3,
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
]

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")
    try:
        with open(LOGS_DIR / f"crawler_{datetime.now().strftime('%Y%m%d')}.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {msg}\n")
    except:
        pass

def generate_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    try:
        text = html.unescape(text)
    except:
        pass
    return re.sub(r'\s+', ' ', text).strip()

def calculate_impact_score(title, content=""):
    """计算新闻影响力分数"""
    text = (title + " " + content).lower()
    score = 0
    matched_keywords = []
    
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword.lower() in text:
            score += weight
            matched_keywords.append(keyword)
    
    return score, matched_keywords

def validate_article(article):
    title = article.get("title", "")
    url = article.get("url", "")
    
    if not title or len(title) < 5 or len(title) > 200:
        return False
    if not url or len(url) < 10:
        return False
    
    skip_words = ["登录", "注册", "首页", "更多", "分享", "收藏", "微信", "微博", "APP"]
    if any(w in title for w in skip_words):
        return False
    
    return True

def fetch_fast(url, timeout=30):
    try:
        cmd = ["curl", "-s", "-L", "--connect-timeout", "15", "--max-time", str(timeout),
               "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
               "-H", "Accept: text/html,*/*", url]
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
        
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return result.stdout.decode(enc)
            except:
                continue
        return result.stdout.decode('utf-8', errors='replace')
    except:
        return None

def crawl_source(source):
    name = source["name"]
    url = source["url"]
    market = source.get("market", "A股")
    
    log(f"爬取: {name} [{market}]")
    
    content = fetch_fast(url, timeout=30)
    if not content:
        log(f"{name}: 获取失败", "WARN")
        return []
    
    pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
    links = re.findall(pattern, content, re.IGNORECASE)
    
    base_domain = re.match(r'https?://([^/]+)', url)
    base_domain = base_domain.group(1) if base_domain else ""
    
    articles = []
    seen_urls = set()
    
    for href, title in links[:150]:
        href = href.strip()
        if href.startswith("/"):
            href = f"https://{base_domain}{href}"
        elif not href.startswith("http"):
            continue
        
        if href in seen_urls:
            continue
        seen_urls.add(href)
        
        title = clean_text(title)
        
        # 计算影响力分数
        impact_score, keywords = calculate_impact_score(title)
        
        article = {
            "id": generate_id(href + title),
            "title": title,
            "url": href,
            "source": name,
            "market": market,
            "categories": source.get("category", []),
            "impact_score": impact_score,
            "keywords": keywords,
            "crawl_time": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        if validate_article(article):
            articles.append(article)
        
        if len(articles) >= 100:
            break
    
    log(f"{name}: {len(articles)} 条")
    return articles

def main():
    log("=" * 50)
    log("财经新闻爬虫启动 (A股 + 美股)")
    log("=" * 50)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_articles = []
    
    # 爬取A股数据源
    log("--- A股数据源 ---")
    for source in A_STOCK_SOURCES:
        articles = crawl_source(source)
        all_articles.extend(articles)
        time.sleep(random.uniform(0.5, 1.5))
    
    # 爬取美股数据源
    log("--- 美股数据源 ---")
    for source in US_STOCK_SOURCES:
        articles = crawl_source(source)
        all_articles.extend(articles)
        time.sleep(random.uniform(0.5, 1.5))
    
    # 去重
    seen = set()
    unique = []
    for a in all_articles:
        key = a["id"] + a["title"][:20]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    
    # 按影响力排序
    unique.sort(key=lambda x: x.get("impact_score", 0), reverse=True)
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"finance_news_{timestamp}.json"
    
    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "total_articles": len(unique),
        "a_stock_count": len([a for a in unique if a.get("market") == "A股"]),
        "us_stock_count": len([a for a in unique if a.get("market") == "美股"]),
        "high_impact_count": len([a for a in unique if a.get("impact_score", 0) >= 5]),
        "articles": unique
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("-" * 50)
    log(f"完成! 共 {len(unique)} 条")
    log(f"  A股: {output_data['a_stock_count']} 条")
    log(f"  美股: {output_data['us_stock_count']} 条")
    log(f"  高影响: {output_data['high_impact_count']} 条")
    log(f"保存: {output_file}")
    
    return unique

if __name__ == "__main__":
    main()