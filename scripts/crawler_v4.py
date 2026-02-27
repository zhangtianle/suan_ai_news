#!/usr/bin/env python3
"""
Tech News Crawler v4 - 最终版
修复UTF-8解码错误 + 503处理 + 重试机制
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
import chardet

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "raw"
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"
LOGS_DIR = PROJECT_ROOT / "logs"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
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
    try:
        text = html.unescape(text)
    except:
        pass
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
                     "微信", "微博", "QQ", "分享", "收藏", "举报"]
    for kw in skip_keywords:
        if kw in title:
            return False, f"导航链接"
    
    return True, "验证通过"

def fetch_url_robust(url, retries=3):
    """
    健壮的URL获取，修复编码问题和503错误
    """
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(0.3, 1.5))
            
            # 使用二进制模式获取，避免编码问题
            cmd = ["curl", "-s", "-L", 
                   "--connect-timeout", "20",
                   "--max-time", "60",
                   "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
                   "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                   "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
                   "-H", "Cache-Control: no-cache",
                   url]
            
            result = subprocess.run(
                cmd,
                capture_output=True, timeout=90
            )
            
            # 获取HTTP状态码
            code_cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                       "--connect-timeout", "10", "--max-time", "30",
                       "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
                       url]
            code_result = subprocess.run(code_cmd, capture_output=True, text=True, timeout=40)
            http_code = code_result.stdout.strip()
            
            # 处理特定HTTP错误
            if http_code == "503":
                log(f"HTTP 503 - 服务暂时不可用，等待重试 ({attempt+1}/{retries})", "WARN")
                time.sleep(random.uniform(3, 6))
                continue
            elif http_code == "403":
                log(f"HTTP 403 - 访问被拒绝", "WARN")
                time.sleep(random.uniform(2, 4))
                continue
            elif http_code == "429":
                log(f"HTTP 429 - 请求过多，等待重试 ({attempt+1}/{retries})", "WARN")
                time.sleep(random.uniform(5, 10))
                continue
            
            # 处理编码问题 - 自动检测编码
            raw_data = result.stdout
            if not raw_data or len(raw_data) < 500:
                if attempt < retries - 1:
                    log(f"内容过短，重试 ({attempt+1}/{retries})", "WARN")
                    time.sleep(random.uniform(1, 3))
                    continue
                return None, "内容为空或过短"
            
            # 检测编码
            try:
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8') or 'utf-8'
                content = raw_data.decode(encoding, errors='replace')
            except Exception as e:
                # 如果chardet失败，尝试常见编码
                for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        content = raw_data.decode(enc, errors='replace')
                        break
                    except:
                        continue
                else:
                    content = raw_data.decode('utf-8', errors='replace')
            
            return content, None
            
        except subprocess.TimeoutExpired:
            log(f"请求超时，重试 ({attempt+1}/{retries})", "WARN")
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
    
    log(f"开始爬取: {name}")
    
    articles = []
    errors = []
    
    content, error = fetch_url_robust(url, retries=3)
    
    if error:
        errors.append(error)
        log(f"警告: {name} - {error}", "WARN")
        return articles, errors
    
    if not content or len(content) < 500:
        errors.append(f"内容过短: {len(content) if content else 0} bytes")
        return articles, errors
    
    # 检查反爬
    if any(kw in content for kw in ["验证码", "blocked", "访问频繁", "人机验证"]):
        errors.append("触发反爬机制")
    
    base_domain = re.match(r'https?://([^/]+)', url)
    base_domain = base_domain.group(1) if base_domain else ""
    
    # 提取链接
    patterns = [
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        r'<a[^>]*href=([^\s>]+)[^>]*>([^<]*)</a>',
    ]
    
    all_links = []
    for pattern in patterns:
        links = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        all_links.extend(links)
    
    seen_urls = set()
    for href, title in all_links[:200]:  # 限制解析数量
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
        
        valid, _ = validate_article(article)
        if valid:
            articles.append(article)
        
        if len(articles) >= 100:
            break
    
    log(f"{name} 完成: {len(articles)} 条有效")
    
    return articles, errors

def main():
    log("=" * 50)
    log("科技资讯爬虫 v4 启动")
    log("=" * 50)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    config = load_sources()
    sources = config.get("sources", [])
    
    all_articles = []
    all_errors = {}
    
    random.shuffle(sources)
    
    for source in sources:
        articles, errors = crawl_source(source)
        all_articles.extend(articles)
        if errors:
            all_errors[source["name"]] = errors
    
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
        "version": "v4",
        "total_articles": len(unique),
        "errors": all_errors,
        "articles": unique
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    log("-" * 50)
    log(f"完成! 共 {len(unique)} 条资讯")
    if all_errors:
        log(f"错误源: {list(all_errors.keys())}")
    log(f"保存: {output_file}")
    
    return unique

if __name__ == "__main__":
    main()