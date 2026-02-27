#!/usr/bin/env python3
"""
Finance News Crawler v1
财经新闻爬虫 - 投资者视角

数据源分类:
- 宏观经济: 央行政策、经济数据、国际贸易
- 股市动态: A股、港股、美股市场新闻
- 财报解读: 上市公司业绩、分析
- 行业研究: 板块轮动、行业趋势
- 商品期货: 能源、金属、农产品
- 国际市场: 美联储、地缘政治、汇率
"""

import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import subprocess
import html
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "finance" / "raw"
LOGS_DIR = PROJECT_ROOT / "logs" / "finance"

# 国内财经媒体
CN_SOURCES = [
    # 综合财经
    {"name": "新浪财经", "url": "https://finance.sina.com.cn", "type": "finance_portal", "priority": "high", "category": ["宏观", "股市", "期货"]},
    {"name": "东方财富", "url": "https://www.eastmoney.com", "type": "finance_portal", "priority": "high", "category": ["股市", "基金", "期货"]},
    {"name": "同花顺", "url": "https://www.10jqka.com.cn", "type": "finance_portal", "priority": "high", "category": ["股市", "技术分析"]},
    {"name": "证券时报", "url": "https://www.stcn.com", "type": "finance_media", "priority": "high", "category": ["股市", "宏观", "政策"]},
    {"name": "上海证券报", "url": "https://www.cnstock.com", "type": "finance_media", "priority": "high", "category": ["股市", "政策", "IPO"]},
    {"name": "中国证券报", "url": "https://www.cs.com.cn", "type": "finance_media", "priority": "high", "category": ["股市", "宏观"]},
    {"name": "第一财经", "url": "https://www.yicai.com", "type": "finance_media", "priority": "high", "category": ["宏观", "股市", "国际"]},
    {"name": "经济观察报", "url": "https://www.eeo.com.cn", "type": "finance_media", "priority": "medium", "category": ["宏观", "产业"]},
    {"name": "财新网", "url": "https://www.caixin.com", "type": "finance_media", "priority": "high", "category": ["宏观", "金融", "产业"]},
    {"name": "21世纪经济报道", "url": "https://www.21jingji.com", "type": "finance_media", "priority": "high", "category": ["宏观", "产业", "股市"]},
    
    # 股市专业
    {"name": "雪球", "url": "https://xueqiu.com", "type": "stock_community", "priority": "medium", "category": ["股市", "投资观点"]},
    {"name": "淘股吧", "url": "https://www.taoguba.com.cn", "type": "stock_community", "priority": "medium", "category": ["股市", "短线"]},
    
    # 期货专业
    {"name": "期货日报", "url": "https://www.qhrb.com.cn", "type": "futures_media", "priority": "high", "category": ["期货", "商品"]},
    {"name": "文华财经", "url": "https://www.wenhua.com.cn", "type": "futures_media", "priority": "medium", "category": ["期货", "技术分析"]},
    
    # 基金/资管
    {"name": "中国基金报", "url": "https://www.chnfund.com.cn", "type": "fund_media", "priority": "high", "category": ["基金", "机构"]},
]

# 国际财经媒体
INTL_SOURCES = [
    # 综合财经
    {"name": "Bloomberg", "url": "https://www.bloomberg.com", "type": "international", "priority": "high", "category": ["国际", "宏观", "股市"], "rss": "https://www.bloomberg.com/feed/podcast/bloomberg-markets.xml"},
    {"name": "Reuters", "url": "https://www.reuters.com", "type": "international", "priority": "high", "category": ["国际", "宏观", "股市"], "rss": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"},
    {"name": "WSJ", "url": "https://www.wsj.com", "type": "international", "priority": "high", "category": ["国际", "股市", "宏观"]},
    {"name": "FT", "url": "https://www.ft.com", "type": "international", "priority": "high", "category": ["国际", "宏观", "金融"]},
    {"name": "CNBC", "url": "https://www.cnbc.com", "type": "international", "priority": "high", "category": ["国际", "股市", "宏观"], "rss": "https://www.cnbc.com/id/10000664/device/rss/rss.html"},
    
    # 市场数据
    {"name": "MarketWatch", "url": "https://www.marketwatch.com", "type": "international", "priority": "medium", "category": ["美股", "数据"], "rss": "https://www.marketwatch.com/rss/topstories"},
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com", "type": "international", "priority": "medium", "category": ["美股", "数据"]},
    {"name": "Seeking Alpha", "url": "https://seekingalpha.com", "type": "international", "priority": "medium", "category": ["美股", "分析"], "rss": "https://seekingalpha.com/market_currents.xml"},
    
    # 央行/政策
    {"name": "Federal Reserve", "url": "https://www.federalreserve.gov", "type": "policy", "priority": "high", "category": ["美联储", "政策"]},
    {"name": "ECB", "url": "https://www.ecb.europa.eu", "type": "policy", "priority": "medium", "category": ["欧洲", "政策"]},
    
    # 商品/能源
    {"name": "OilPrice", "url": "https://oilprice.com", "type": "commodity", "priority": "high", "category": ["能源", "原油"], "rss": "https://oilprice.com/rss/main"},
    {"name": "Investing.com", "url": "https://www.investing.com", "type": "international", "priority": "medium", "category": ["商品", "外汇", "数据"], "rss": "https://www.investing.com/rss/news.rss"},
    
    # 加密货币
    {"name": "CoinDesk", "url": "https://www.coindesk.com", "type": "crypto", "priority": "medium", "category": ["加密货币", "区块链"], "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
    {"name": "Cointelegraph", "url": "https://cointelegraph.com", "type": "crypto", "priority": "medium", "category": ["加密货币"], "rss": "https://cointelegraph.com/rss"},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
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

def parse_pub_date(date_str):
    """解析各种格式的发布时间"""
    if not date_str:
        return None
    
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo:
                dt = dt.astimezone(timezone(timedelta(hours=8)))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
    if match:
        return match.group(1)
    
    return None

def extract_market_signal(title, content=""):
    """提取市场信号 - 投资者视角"""
    text = (title + " " + content).lower()
    
    signals = {
        "bullish": [],  # 利好信号
        "bearish": [],  # 利空信号
        "neutral": []   # 中性/观望
    }
    
    # 利好关键词
    bullish_keywords = [
        "上涨", "大涨", "暴涨", "新高", "突破", "利好", "盈利", "增长", "超预期",
        "降息", "宽松", "刺激", "反弹", "回暖", "恢复", "并购", "收购",
        "增持", "回购", "分红", "业绩大增", "扭亏", "订单", "中标",
        "surge", "rally", "gain", "profit", "growth", "beat", "rise"
    ]
    
    # 利空关键词
    bearish_keywords = [
        "下跌", "大跌", "暴跌", "新低", "破位", "利空", "亏损", "下滑", "不及预期",
        "加息", "收紧", "萎缩", "衰退", "裁员", "破产", "违约", "暴雷",
        "减持", "抛售", "退市", "调查", "处罚", "诉讼", "罚款",
        "plunge", "crash", "drop", "loss", "down", "recession", "fear"
    ]
    
    for kw in bullish_keywords:
        if kw in text:
            signals["bullish"].append(kw)
    
    for kw in bearish_keywords:
        if kw in text:
            signals["bearish"].append(kw)
    
    # 确定整体信号
    if len(signals["bullish"]) > len(signals["bearish"]):
        signals["overall"] = "bullish"
    elif len(signals["bearish"]) > len(signals["bullish"]):
        signals["overall"] = "bearish"
    else:
        signals["overall"] = "neutral"
    
    return signals

def extract_entities(title, content=""):
    """提取关键实体 - 股票、公司、行业"""
    text = title + " " + content
    
    entities = {
        "stocks": [],
        "companies": [],
        "sectors": [],
        "indices": []
    }
    
    # 主要指数
    indices_patterns = [
        (r"上证指数|沪指|上证", "上证指数"),
        (r"深证成指|深成指", "深证成指"),
        (r"创业板指|创业板", "创业板指"),
        (r"科创50|科创板", "科创50"),
        (r"恒生指数|恒指", "恒生指数"),
        (r"道琼斯|道指", "道琼斯"),
        (r"纳斯达克|纳指", "纳斯达克"),
        (r"标普500|S&P", "标普500"),
    ]
    
    for pattern, name in indices_patterns:
        if re.search(pattern, text):
            entities["indices"].append(name)
    
    # 行业板块
    sectors = [
        "半导体", "芯片", "新能源", "光伏", "锂电池", "储能", "风电",
        "白酒", "医药", "生物制药", "医疗器械", "中药",
        "银行", "券商", "保险", "地产", "房地产",
        "汽车", "新能源汽车", "智能驾驶",
        "消费电子", "苹果产业链", "消费", "食品饮料",
        "军工", "航天", "通信", "5G", "人工智能", "AI",
        "互联网", "电商", "游戏", "传媒", "教育",
        "有色", "煤炭", "石油", "化工", "钢铁"
    ]
    
    for sector in sectors:
        if sector in text:
            entities["sectors"].append(sector)
    
    # 大公司
    companies = [
        "茅台", "宁德时代", "比亚迪", "腾讯", "阿里", "字节", "美团",
        "华为", "小米", "蔚来", "理想", "小鹏", "中芯国际",
        "苹果", "特斯拉", "英伟达", "微软", "谷歌", "Meta", "亚马逊"
    ]
    
    for company in companies:
        if company in text:
            entities["companies"].append(company)
    
    return entities

def fetch_rss(source):
    """通过 RSS 获取数据"""
    rss_url = source.get("rss")
    if not rss_url:
        return []
    
    log(f"RSS 获取: {source['name']}")
    
    try:
        cmd = ["curl", "-s", "-L",
               "--connect-timeout", "15",
               "--max-time", "30",
               "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
               rss_url]
        
        result = subprocess.run(cmd, capture_output=True, timeout=45)
        
        if not result.stdout or len(result.stdout) < 100:
            return []
        
        content = result.stdout.decode('utf-8', errors='replace')
        
        articles = []
        root = ET.fromstring(content)
        
        for item in root.findall('.//item')[:50]:
            try:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pub_date_elem = item.find('pubDate')
                desc_elem = item.find('description')
                
                if title_elem is None or link_elem is None:
                    continue
                
                title = clean_text(title_elem.text) if title_elem.text else ""
                url = link_elem.text.strip() if link_elem.text else ""
                pub_date = parse_pub_date(pub_date_elem.text) if pub_date_elem is not None else None
                
                if not title or len(title) < 5 or not url:
                    continue
                
                # 提取市场信号
                signals = extract_market_signal(title)
                entities = extract_entities(title)
                
                article = {
                    "id": generate_id(url + title),
                    "title": title,
                    "url": url,
                    "source": source["name"],
                    "categories": source.get("category", []),
                    "pub_date": pub_date,
                    "crawl_time": datetime.now().isoformat(),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "market_signal": signals,
                    "entities": entities
                }
                
                articles.append(article)
                
            except Exception as e:
                continue
        
        log(f"{source['name']} (RSS): {len(articles)} 条")
        return articles
        
    except subprocess.TimeoutExpired:
        log(f"RSS 超时: {source['name']}", "WARN")
        return []
    except Exception as e:
        log(f"RSS 错误 {source['name']}: {str(e)[:50]}", "WARN")
        return []

def fetch_html(source):
    """通过 HTML 页面获取数据"""
    url = source["url"]
    name = source["name"]
    
    log(f"HTML 获取: {name}")
    
    try:
        cmd = ["curl", "-s", "-L",
               "--connect-timeout", "10",
               "--max-time", "25",
               "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
               "-H", "Accept: text/html,*/*",
               url]
        
        result = subprocess.run(cmd, capture_output=True, timeout=35)
        
        if not result.stdout or len(result.stdout) < 500:
            return []
        
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                content = result.stdout.decode(enc)
                break
            except:
                continue
        else:
            content = result.stdout.decode('utf-8', errors='replace')
        
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
            
            signals = extract_market_signal(title)
            entities = extract_entities(title)
            
            article = {
                "id": generate_id(href + title),
                "title": title,
                "url": href,
                "source": name,
                "categories": source.get("category", []),
                "pub_date": None,
                "crawl_time": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "market_signal": signals,
                "entities": entities
            }
            
            if validate_article(article):
                articles.append(article)
            
            if len(articles) >= 80:
                break
        
        log(f"{name} (HTML): {len(articles)} 条")
        return articles
        
    except subprocess.TimeoutExpired:
        log(f"HTML 超时: {name}", "WARN")
        return []
    except Exception as e:
        log(f"HTML 错误 {name}: {str(e)[:50]}", "ERROR")
        return []

def validate_article(article):
    """验证文章有效性"""
    title = article.get("title", "")
    url = article.get("url", "")
    
    if not title or len(title) < 5 or len(title) > 200:
        return False
    if not url or len(url) < 10:
        return False
    
    skip_words = ["登录", "注册", "首页", "更多", "分享", "收藏", "微信", "微博", "APP",
                  "下一页", "上一页", "Subscribe", "Login", "Sign Up", "RSS", "About",
                  "广告", "合作", "联系我们", "版权"]
    if any(w in title for w in skip_words):
        return False
    
    # 必须包含财经相关关键词
    finance_keywords = [
        "股", "市", "金", "财", "经", "投资", "基金", "期货", "债", "汇率",
        "利率", "通胀", "GDP", "央行", "银行", "上市", "财报", "业绩",
        "融资", "并购", "IPO", "证券", "指数", "板块", "涨", "跌",
        "stock", "market", "invest", "fund", "trade", "economy", "finance",
        "rate", "bond", "currency", "profit", "loss", "earnings"
    ]
    
    if not any(kw in title.lower() for kw in finance_keywords):
        return False
    
    return True

def crawl_source(source):
    """爬取单个数据源"""
    if source.get("rss"):
        articles = fetch_rss(source)
        if articles:
            return articles
    return fetch_html(source)

def main():
    log("=" * 60)
    log("财经资讯爬虫 v1 启动 (投资者视角)")
    log("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_articles = []
    
    log("\n📍 爬取国内财经数据源...")
    for source in CN_SOURCES:
        try:
            articles = crawl_source(source)
            all_articles.extend(articles)
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            log(f"爬取 {source['name']} 异常: {e}", "ERROR")
    
    log("\n🌍 爬取国际财经数据源...")
    for source in INTL_SOURCES:
        try:
            articles = crawl_source(source)
            all_articles.extend(articles)
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            log(f"爬取 {source['name']} 异常: {e}", "ERROR")
    
    # 去重
    seen = set()
    unique = []
    for a in all_articles:
        key = a["id"] + a["title"][:20]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    
    # 统计
    source_stats = {}
    signal_stats = {"bullish": 0, "bearish": 0, "neutral": 0}
    
    for a in unique:
        src = a.get("source", "未知")
        source_stats[src] = source_stats.get(src, 0) + 1
        
        signal = a.get("market_signal", {}).get("overall", "neutral")
        signal_stats[signal] = signal_stats.get(signal, 0) + 1
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"finance_{timestamp}.json"
    
    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "version": "v1",
        "total_articles": len(unique),
        "cn_sources": [s["name"] for s in CN_SOURCES],
        "intl_sources": [s["name"] for s in INTL_SOURCES],
        "source_stats": source_stats,
        "signal_stats": signal_stats,
        "articles": unique
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("\n" + "=" * 60)
    log(f"✅ 完成! 共 {len(unique)} 条资讯")
    log(f"📁 保存: {output_file}")
    log("\n📊 市场情绪信号:")
    log(f"   利好: {signal_stats['bullish']} 条")
    log(f"   利空: {signal_stats['bearish']} 条")
    log(f"   中性: {signal_stats['neutral']} 条")
    log("\n📊 数据源统计:")
    for src, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        log(f"   {src}: {count} 条")
    
    return unique

if __name__ == "__main__":
    main()