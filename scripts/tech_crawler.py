#!/usr/bin/env python3
"""
Tech News Crawler v6 - 国际版
- 新增海外综合及资讯类网站
- 增加发布时间提取
- 支持 RSS 订阅源
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
DATA_DIR = PROJECT_ROOT / "data" / "raw"
LOGS_DIR = PROJECT_ROOT / "logs"

# 国内科技媒体
CN_SOURCES = [
    {"name": "IT之家", "url": "https://www.ithome.com", "type": "tech_news", "priority": "high", "category": ["科技", "数码"]},
    {"name": "InfoQ", "url": "https://www.infoq.cn", "type": "tech_media", "priority": "high", "category": ["技术", "架构"]},
    {"name": "量子位", "url": "https://www.qbitai.com", "type": "ai_media", "priority": "high", "category": ["AI", "科技"]},
    {"name": "虎嗅", "url": "https://www.huxiu.com", "type": "media", "priority": "medium", "category": ["科技", "商业"]},
    {"name": "智源社区", "url": "https://hub.baai.ac.cn", "type": "ai_research", "priority": "high", "category": ["AI", "研究"]},
    {"name": "雷锋网", "url": "https://www.leiphone.com", "type": "ai_media", "priority": "high", "category": ["AI", "科技"]},
    {"name": "PingWest", "url": "https://www.pingwest.com", "type": "tech_media", "priority": "medium", "category": ["科技", "互联网"]},
    {"name": "爱范儿", "url": "https://www.ifanr.com", "type": "tech_media", "priority": "medium", "category": ["科技", "数码"]},
    {"name": "驱动之家", "url": "https://www.mydrivers.com", "type": "tech_news", "priority": "medium", "category": ["科技", "硬件"]},
    {"name": "36氪", "url": "https://36kr.com", "type": "startup_media", "priority": "high", "category": ["创业", "投资"]},
    {"name": "机器之心", "url": "https://www.jiqizhixin.com", "type": "ai_media", "priority": "high", "category": ["AI", "研究"]},
]

# 海外科技媒体
INTL_SOURCES = [
    # 主流科技媒体
    {"name": "TechCrunch", "url": "https://techcrunch.com", "type": "international", "priority": "high", "category": ["科技", "创业", "国际"], "rss": "https://techcrunch.com/feed/"},
    {"name": "TheVerge", "url": "https://www.theverge.com", "type": "international", "priority": "high", "category": ["科技", "数码", "国际"], "rss": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com", "type": "international", "priority": "high", "category": ["科技", "文化", "国际"], "rss": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://arstechnica.com", "type": "international", "priority": "high", "category": ["科技", "技术", "国际"], "rss": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Engadget", "url": "https://www.engadget.com", "type": "international", "priority": "high", "category": ["科技", "数码", "国际"], "rss": "https://www.engadget.com/rss.xml"},
    {"name": "VentureBeat", "url": "https://venturebeat.com", "type": "international", "priority": "high", "category": ["科技", "AI", "国际"], "rss": "https://venturebeat.com/feed/"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com", "type": "international", "priority": "high", "category": ["科技", "研究", "国际"], "rss": "https://www.technologyreview.com/feed/"},
    
    # AI 专业媒体
    {"name": "TheRegister", "url": "https://www.theregister.com", "type": "international", "priority": "medium", "category": ["科技", "IT", "国际"], "rss": "https://www.theregister.com/headlines.atom"},
    
    # 综合新闻科技版
    {"name": "BBC Technology", "url": "https://www.bbc.com/news/technology", "type": "international", "priority": "high", "category": ["科技", "新闻", "国际"], "rss": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "Reuters Tech", "url": "https://www.reuters.com/technology/", "type": "international", "priority": "high", "category": ["科技", "新闻", "国际"], "rss": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"},
    
    # 开发者社区
    {"name": "Hacker News", "url": "https://news.ycombinator.com", "type": "community", "priority": "high", "category": ["技术", "开源", "国际"], "rss": "https://hnrss.org/frontpage"},
    {"name": "Dev.to", "url": "https://dev.to", "type": "community", "priority": "medium", "category": ["技术", "开发", "国际"], "rss": "https://dev.to/feed"},
    
    # AI/ML 专业
    {"name": "AI News", "url": "https://www.artificialintelligence-news.com", "type": "ai_media", "priority": "medium", "category": ["AI", "国际"], "rss": "https://www.artificialintelligence-news.com/feed/"},
    {"name": "Synced", "url": "https://syncedreview.com", "type": "ai_media", "priority": "high", "category": ["AI", "研究", "国际"], "rss": "https://syncedreview.com/feed/"},
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
    
    # 常见日期格式
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            # 转换为北京时间
            if dt.tzinfo:
                dt = dt.astimezone(timezone(timedelta(hours=8)))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    # 尝试提取日期部分
    match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
    if match:
        return match.group(1)
    
    return None

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
        
        # 解析 XML
        articles = []
        root = ET.fromstring(content)
        
        # 处理 RSS 2.0 格式
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
                
                article = {
                    "id": generate_id(url + title),
                    "title": title,
                    "url": url,
                    "source": source["name"],
                    "categories": source.get("category", []),
                    "pub_date": pub_date,  # 发布时间
                    "crawl_time": datetime.now().isoformat(),
                    "date": datetime.now().strftime("%Y-%m-%d")
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
        
        # 解码
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                content = result.stdout.decode(enc)
                break
            except:
                continue
        else:
            content = result.stdout.decode('utf-8', errors='replace')
        
        # 提取链接
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
            
            # 尝试从 HTML 提取发布时间
            pub_date = None
            # 常见时间格式模式
            time_patterns = [
                r'<time[^>]*datetime=["\']([^"\']+)["\']',
                r'<span[^>]*class="[^"]*date[^"]*"[^>]*>([^<]+)</span>',
                r'data-date="([^"]+)"',
                r'pubdate="([^"]+)"',
            ]
            
            article = {
                "id": generate_id(href + title),
                "title": title,
                "url": href,
                "source": name,
                "categories": source.get("category", []),
                "pub_date": pub_date,  # 发布时间
                "crawl_time": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # 验证文章
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
                  "下一页", "上一页", "Subscribe", "Login", "Sign Up", "RSS", "About"]
    if any(w in title for w in skip_words):
        return False
    
    return True

def crawl_source(source):
    """爬取单个数据源"""
    # 优先使用 RSS
    if source.get("rss"):
        articles = fetch_rss(source)
        if articles:
            return articles
    
    # RSS 失败则用 HTML
    return fetch_html(source)

def main():
    log("=" * 60)
    log("科技资讯爬虫 v6 启动 (国际增强版)")
    log("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_articles = []
    
    # 爬取国内源
    log("\n📍 爬取国内数据源...")
    for source in CN_SOURCES:
        try:
            articles = crawl_source(source)
            all_articles.extend(articles)
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            log(f"爬取 {source['name']} 异常: {e}", "ERROR")
    
    # 爬取国际源
    log("\n🌍 爬取国际数据源...")
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
    for a in unique:
        src = a.get("source", "未知")
        source_stats[src] = source_stats.get(src, 0) + 1
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"news_{timestamp}.json"
    
    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "version": "v6",
        "total_articles": len(unique),
        "cn_sources": [s["name"] for s in CN_SOURCES],
        "intl_sources": [s["name"] for s in INTL_SOURCES],
        "source_stats": source_stats,
        "articles": unique
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("\n" + "=" * 60)
    log(f"✅ 完成! 共 {len(unique)} 条资讯")
    log(f"📁 保存: {output_file}")
    log("\n📊 数据源统计:")
    for src, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        log(f"   {src}: {count} 条")
    
    return unique

if __name__ == "__main__":
    main()