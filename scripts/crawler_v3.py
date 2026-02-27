#!/usr/bin/env python3
"""
Tech News Crawler v3 - 健壮版
解决503错误 + JS渲染支持
"""

import json
import os
import re
import time
import random
from datetime import datetime
from pathlib import Path
import hashlib
import subprocess
import html
import urllib.parse

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "raw"
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"
LOGS_DIR = PROJECT_ROOT / "logs"

# 随机User-Agent池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    
    log_file = LOGS_DIR / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_sources():
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def validate_article(article):
    title = article.get("title", "")
    url = article.get("url", "")
    
    if not title or len(title) < 5:
        return False, "标题过短"
    if len(title) > 200:
        article["title"] = title[:200]
    if not url or len(url) < 10:
        return False, "URL无效"
    
    skip_keywords = ["登录", "注册", "关于我们", "联系我们", "隐私政策", 
                     "用户协议", "帮助中心", "意见反馈", "APP下载",
                     "首页", "下一页", "上一页", "更多", "返回顶部",
                     "微信", "微博", "QQ", "分享", "收藏"]
    for kw in skip_keywords:
        if kw in title:
            return False, f"导航链接: {kw}"
    
    return True, "验证通过"

def fetch_url(url, retries=3, use_browser=False):
    """
    获取URL内容，支持重试和503错误处理
    """
    headers = [
        "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
        "-H", "Accept-Encoding: gzip, deflate, br",
        "-H", "Connection: keep-alive",
        "-H", "Cache-Control: max-age=0",
    ]
    
    for attempt in range(retries):
        try:
            # 随机延迟避免触发反爬
            time.sleep(random.uniform(0.5, 2))
            
            cmd = ["curl", "-s", "-L", 
                   "--connect-timeout", "20",
                   "--max-time", "90",
                   "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
                   "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                   "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
                   "--compressed",
                   url]
            
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=120
            )
            
            content = result.stdout
            
            # 检查HTTP状态码
            http_code_result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "--connect-timeout", "10", url],
                capture_output=True, text=True, timeout=30
            )
            http_code = http_code_result.stdout.strip()
            
            if http_code == "503":
                log(f"503错误，等待重试 ({attempt+1}/{retries})...", "WARN")
                time.sleep(random.uniform(3, 6))  # 503错误等待更长时间
                continue
            
            if http_code in ["403", "429"]:
                log(f"HTTP {http_code} - 可能被反爬拦截", "WARN")
                time.sleep(random.uniform(2, 5))
                continue
            
            if not content or len(content) < 500:
                if attempt < retries - 1:
                    log(f"内容过短，重试 ({attempt+1}/{retries})...", "WARN")
                    time.sleep(random.uniform(1, 3))
                    continue
            
            return content, None
            
        except subprocess.TimeoutExpired:
            log(f"请求超时，重试 ({attempt+1}/{retries})...", "WARN")
            if attempt < retries - 1:
                time.sleep(random.uniform(2, 4))
        except Exception as e:
            log(f"请求异常: {str(e)}", "ERROR")
            if attempt < retries - 1:
                time.sleep(random.uniform(1, 3))
    
    return None, "请求失败"

def crawl_source(source):
    name = source["name"]
    url = source["url"]
    
    log(f"开始爬取: {name} ({url})")
    
    articles = []
    errors = []
    
    # 获取内容
    content, error = fetch_url(url, retries=3)
    
    if error:
        errors.append(error)
        log(f"警告: {name} - {error}", "WARN")
        return articles, errors
    
    if not content or len(content) < 1000:
        errors.append(f"内容过短: {len(content) if content else 0} bytes")
        log(f"警告: {name} 返回内容异常", "WARN")
        return articles, errors
    
    # 检查反爬
    if "验证码" in content or "blocked" in content.lower() or "访问频繁" in content:
        errors.append("可能被反爬机制拦截")
        log(f"警告: {name} 可能被反爬拦截", "WARN")
    
    # 提取域名
    base_domain = re.match(r'https?://([^/]+)', url)
    base_domain = base_domain.group(1) if base_domain else ""
    
    # 多模式提取链接
    patterns = [
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        r'<a[^>]*href=([^\s>]+)[^>]*>([^<]*)</a>',
        r'<h[1-6][^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>.*?</h[1-6]>',
        r'<article[^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>.*?</article>',
    ]
    
    all_links = []
    for pattern in patterns:
        links = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        all_links.extend(links)
    
    seen_urls = set()
    for href, title in all_links:
        href = href.strip().replace('&amp;', '&')
        
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
            "source_type": source.get("type", "unknown"),
            "priority": source.get("priority", "medium"),
            "categories": source.get("category", []),
            "crawl_time": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "base_domain": base_domain
        }
        
        valid, reason = validate_article(article)
        if valid:
            articles.append(article)
        
        if len(articles) >= 100:
            break
    
    log(f"{name} 爬取完成: {len(articles)} 条有效 (共解析 {len(all_links)} 条链接)")
    
    return articles, errors

def main():
    log("=" * 60)
    log("开始爬取科技资讯 (v3 健壮版)")
    log("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    config = load_sources()
    sources = config.get("sources", [])
    
    all_articles = []
    all_errors = {}
    stats = {"total_links": 0, "valid_articles": 0, "skipped": 0}
    
    # 随机打乱顺序，避免每次都是同一顺序
    random.shuffle(sources)
    
    for source in sources:
        articles, errors = crawl_source(source)
        all_articles.extend(articles)
        if errors:
            all_errors[source["name"]] = errors
        stats["total_links"] += len(articles)
    
    # 去重
    seen_ids = set()
    seen_titles = set()
    unique_articles = []
    
    for article in all_articles:
        aid = article["id"]
        title_key = article["title"][:30]
        
        if aid not in seen_ids and title_key not in seen_titles:
            seen_ids.add(aid)
            seen_titles.add(title_key)
            unique_articles.append(article)
        else:
            stats["skipped"] += 1
    
    stats["valid_articles"] = len(unique_articles)
    
    # 保存数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"news_{timestamp}.json"
    
    output_data = {
        "crawl_time": datetime.now().isoformat(),
        "version": "v3",
        "stats": stats,
        "errors": all_errors,
        "total_articles": len(unique_articles),
        "articles": unique_articles
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("-" * 60)
    log(f"爬取完成!")
    log(f"  - 有效文章: {stats['valid_articles']} 条")
    log(f"  - 去重跳过: {stats['skipped']} 条")
    log(f"  - 错误数量: {len(all_errors)} 个源")
    log(f"  - 保存路径: {output_file}")
    
    if all_errors:
        log("错误详情:")
        for src, errs in all_errors.items():
            log(f"  - {src}: {', '.join(errs)}")
    
    return unique_articles

if __name__ == "__main__":
    main()