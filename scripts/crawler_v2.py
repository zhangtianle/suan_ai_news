#!/usr/bin/env python3
"""
Tech News Crawler v2 - 增强验证版
每小时爬取科技资讯数据
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
import hashlib
import subprocess
import html
import urllib.parse

# 项目根目录
PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "raw"
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"
LOGS_DIR = PROJECT_ROOT / "logs"

def log(msg, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    
    log_file = LOGS_DIR / f"crawler_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def load_sources():
    """加载资讯源配置"""
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_id(text):
    """生成唯一ID"""
    return hashlib.md5(text.encode()).hexdigest()[:12]

def clean_text(text):
    """清理文本"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_valid_url(url, base_domain):
    """验证URL是否有效"""
    if not url:
        return False
    if url.startswith("javascript:"):
        return False
    if url.startswith("#"):
        return False
    if url.startswith("mailto:"):
        return False
    if "void(0)" in url:
        return False
    # 检查是否是同域名或相关链接
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc and base_domain not in parsed.netloc:
        # 允许一些常见的外链
        allowed_domains = ["weibo.com", "twitter.com", "github.com", "mp.weixin.qq.com"]
        if not any(d in parsed.netloc for d in allowed_domains):
            return True  # 仍然保留，但标记为外链
    return True

def validate_article(article):
    """验证文章数据"""
    title = article.get("title", "")
    url = article.get("url", "")
    
    # 标题验证
    if not title or len(title) < 5:
        return False, "标题过短"
    if len(title) > 200:
        article["title"] = title[:200]  # 截断过长标题
    
    # URL验证
    if not url or len(url) < 10:
        return False, "URL无效"
    
    # 过滤导航/页脚链接
    skip_keywords = ["登录", "注册", "关于我们", "联系我们", "隐私政策", 
                     "用户协议", "帮助中心", "意见反馈", "APP下载",
                     "首页", "下一页", "上一页", "更多", "返回顶部"]
    for kw in skip_keywords:
        if kw in title:
            return False, f"导航链接: {kw}"
    
    return True, "验证通过"

def crawl_source(source):
    """爬取单个资讯源"""
    name = source["name"]
    url = source["url"]
    
    log(f"开始爬取: {name} ({url})")
    
    articles = []
    errors = []
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", 
             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
             "--connect-timeout", "15", 
             "--max-time", "60",
             "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
             "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
             url],
            capture_output=True, text=True, timeout=120
        )
        
        html_content = result.stdout
        
        # 验证返回内容
        if not html_content or len(html_content) < 1000:
            errors.append(f"返回内容过短: {len(html_content) if html_content else 0} bytes")
            log(f"警告: {name} 返回内容异常", "WARN")
            return articles, errors
        
        # 检查是否被反爬
        if "验证码" in html_content or "blocked" in html_content.lower():
            errors.append("可能被反爬机制拦截")
            log(f"警告: {name} 可能被反爬拦截", "WARN")
        
        # 提取域名
        base_domain = re.match(r'https?://([^/]+)', url)
        base_domain = base_domain.group(1) if base_domain else ""
        
        # 提取链接 - 多种模式
        patterns = [
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',  # 标准模式
            r'<a[^>]*href=([^\s>]+)[^>]*>([^<]*)</a>',  # 无引号
            r'<h[1-6][^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>.*?</h[1-6]>',  # 标题中的链接
        ]
        
        all_links = []
        for pattern in patterns:
            links = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            all_links.extend(links)
        
        # 去重
        seen_urls = set()
        for href, title in all_links:
            href = href.strip().replace('&amp;', '&')
            
            # 补全相对URL
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
            
            # 验证文章
            valid, reason = validate_article(article)
            if valid:
                articles.append(article)
            
            if len(articles) >= 100:  # 每个源最多100条
                break
        
        log(f"{name} 爬取完成: {len(articles)} 条有效 (共解析 {len(all_links)} 条链接)")
        
    except subprocess.TimeoutExpired:
        errors.append("爬取超时")
        log(f"错误: {name} 爬取超时", "ERROR")
    except Exception as e:
        errors.append(str(e))
        log(f"错误: {name} 爬取失败 - {str(e)}", "ERROR")
    
    return articles, errors

def main():
    """主函数"""
    log("=" * 60)
    log("开始爬取科技资讯 (增强验证版)")
    log("=" * 60)
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    config = load_sources()
    sources = config.get("sources", [])
    
    all_articles = []
    all_errors = {}
    stats = {"total_links": 0, "valid_articles": 0, "skipped": 0}
    
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
        title_key = article["title"][:30]  # 用标题前30字去重
        
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