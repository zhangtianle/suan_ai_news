#!/usr/bin/env python3
"""
Tech News Crawler
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

# 项目根目录
PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
DATA_DIR = PROJECT_ROOT / "data" / "raw"
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"
LOGS_DIR = PROJECT_ROOT / "logs"

def log(msg):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    
    # 写入日志文件
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
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码HTML实体
    text = html.unescape(text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def crawl_source(source):
    """爬取单个资讯源"""
    name = source["name"]
    url = source["url"]
    
    log(f"开始爬取: {name} ({url})")
    
    articles = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # 使用 curl 爬取
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", "Mozilla/5.0 (compatible; TechNewsBot/1.0)", 
             "--connect-timeout", "10", "--max-time", "30", url],
            capture_output=True, text=True, timeout=60
        )
        
        html_content = result.stdout
        
        if not html_content:
            log(f"警告: {name} 返回空内容")
            return articles
        
        # 简单提取标题和链接
        # 提取所有 a 标签
        links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', html_content, re.IGNORECASE)
        
        for href, title in links[:50]:  # 限制每个源最多50条
            title = clean_text(title)
            
            # 过滤无效链接
            if not title or len(title) < 5:
                continue
            if href.startswith("javascript:") or href.startswith("#"):
                continue
            
            # 补全相对URL
            if href.startswith("/"):
                base_url = re.match(r'(https?://[^/]+)', url)
                if base_url:
                    href = base_url.group(1) + href
            
            article = {
                "id": generate_id(href + title),
                "title": title,
                "url": href,
                "source": name,
                "source_type": source.get("type", "unknown"),
                "priority": source.get("priority", "medium"),
                "categories": source.get("category", []),
                "crawl_time": datetime.now().isoformat(),
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            articles.append(article)
        
        log(f"{name} 爬取完成: {len(articles)} 条")
        
    except subprocess.TimeoutExpired:
        log(f"错误: {name} 爬取超时")
    except Exception as e:
        log(f"错误: {name} 爬取失败 - {str(e)}")
    
    return articles

def crawl_with_search():
    """使用搜索引擎补充爬取"""
    log("使用搜索引擎补充爬取...")
    
    articles = []
    queries = [
        "AI 大模型 最新动态",
        "人工智能 科技新闻",
        "OpenAI Google AI 最新",
        "国产大模型 最新发布"
    ]
    
    try:
        # 模拟搜索结果（实际项目中需要调用搜索API）
        # 这里返回空列表，实际爬取由定时任务触发时使用 web_search 工具
        pass
    except Exception as e:
        log(f"搜索爬取失败: {str(e)}")
    
    return articles

def main():
    """主函数"""
    log("=" * 50)
    log("开始爬取科技资讯")
    log("=" * 50)
    
    # 确保目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载配置
    config = load_sources()
    sources = config.get("sources", [])
    
    all_articles = []
    
    # 爬取每个源
    for source in sources:
        articles = crawl_source(source)
        all_articles.extend(articles)
    
    # 去重
    seen_ids = set()
    unique_articles = []
    for article in all_articles:
        if article["id"] not in seen_ids:
            seen_ids.add(article["id"])
            unique_articles.append(article)
    
    # 保存数据
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"news_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "crawl_time": datetime.now().isoformat(),
            "total_articles": len(unique_articles),
            "articles": unique_articles
        }, f, ensure_ascii=False, indent=2)
    
    log(f"爬取完成! 共 {len(unique_articles)} 条资讯")
    log(f"数据保存至: {output_file}")
    
    return unique_articles

if __name__ == "__main__":
    main()