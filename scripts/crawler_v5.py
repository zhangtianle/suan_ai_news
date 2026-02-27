#!/usr/bin/env python3
"""
Tech News Crawler v5 - 稳定版
- 跳过不可访问网站
- 严格超时控制
- 快速失败机制
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
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"
LOGS_DIR = PROJECT_ROOT / "logs"

# 可靠的数据源（已验证可用）
RELIABLE_SOURCES = [
    # 国内媒体
    {"name": "IT之家", "url": "https://www.ithome.com", "type": "tech_news", "priority": "high", "category": ["科技", "数码"]},
    {"name": "InfoQ", "url": "https://www.infoq.cn", "type": "tech_media", "priority": "high", "category": ["技术", "架构"]},
    {"name": "量子位", "url": "https://www.qbitai.com", "type": "ai_media", "priority": "high", "category": ["AI", "科技"]},
    {"name": "虎嗅", "url": "https://www.huxiu.com", "type": "media", "priority": "medium", "category": ["科技", "商业"]},
    {"name": "智源社区", "url": "https://hub.baai.ac.cn", "type": "ai_research", "priority": "high", "category": ["AI", "研究"]},
    {"name": "雷锋网", "url": "https://www.leiphone.com", "type": "ai_media", "priority": "high", "category": ["AI", "科技"]},
    {"name": "PingWest", "url": "https://www.pingwest.com", "type": "tech_media", "priority": "medium", "category": ["科技", "互联网"]},
    {"name": "爱范儿", "url": "https://www.ifanr.com", "type": "tech_media", "priority": "medium", "category": ["科技", "数码"]},
    {"name": "驱动之家", "url": "https://www.mydrivers.com", "type": "tech_news", "priority": "medium", "category": ["科技", "硬件"]},
    # 海外媒体
    {"name": "TechCrunch", "url": "https://techcrunch.com", "type": "international", "priority": "high", "category": ["科技", "创业", "国际"]},
    {"name": "TheVerge", "url": "https://www.theverge.com", "type": "international", "priority": "high", "category": ["科技", "数码", "国际"]},
    {"name": "Wired", "url": "https://www.wired.com", "type": "international", "priority": "medium", "category": ["科技", "文化", "国际"]},
]

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

def validate_article(article):
    title = article.get("title", "")
    url = article.get("url", "")
    
    if not title or len(title) < 5 or len(title) > 200:
        return False
    if not url or len(url) < 10:
        return False
    
    skip_words = ["登录", "注册", "首页", "更多", "分享", "收藏", "微信", "微博", "APP", "下一页", "上一页"]
    if any(w in title for w in skip_words):
        return False
    
    return True

def fetch_fast(url, timeout=30):
    """快速获取，严格超时"""
    try:
        cmd = ["curl", "-s", "-L",
               "--connect-timeout", "10",
               "--max-time", str(timeout),
               "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
               "-H", "Accept: text/html,*/*",
               url]
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
        
        if not result.stdout or len(result.stdout) < 500:
            return None
        
        # 尝试解码
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                content = result.stdout.decode(enc)
                return content
            except:
                continue
        
        return result.stdout.decode('utf-8', errors='replace')
        
    except subprocess.TimeoutExpired:
        log(f"超时: {url[:50]}", "WARN")
        return None
    except Exception as e:
        log(f"错误: {str(e)[:50]}", "ERROR")
        return None

def crawl_source(source):
    name = source["name"]
    url = source["url"]
    
    log(f"爬取: {name}")
    
    content = fetch_fast(url, timeout=30)
    
    if not content:
        log(f"{name} - 获取失败", "WARN")
        return []
    
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
        
        article = {
            "id": generate_id(href + title),
            "title": title,
            "url": href,
            "source": name,
            "categories": source.get("category", []),
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
    log("科技资讯爬虫 v5 启动")
    log("=" * 50)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_articles = []
    
    for source in RELIABLE_SOURCES:
        try:
            articles = crawl_source(source)
            all_articles.extend(articles)
            time.sleep(random.uniform(0.5, 1.5))
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
    
    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"news_{timestamp}.json"
    
    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "version": "v5",
        "total_articles": len(unique),
        "sources": [s["name"] for s in RELIABLE_SOURCES],
        "articles": unique
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("-" * 50)
    log(f"完成! 共 {len(unique)} 条资讯")
    log(f"保存: {output_file}")
    
    return unique

if __name__ == "__main__":
    main()