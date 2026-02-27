#!/usr/bin/env python3
"""
数据处理和分类脚本
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SOURCES_FILE = PROJECT_ROOT / "sources" / "media_list.json"

def load_categories():
    """加载分类配置"""
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("categories", {})

def categorize_article(article, categories):
    """对文章进行分类"""
    title = article.get("title", "").lower()
    url = article.get("url", "").lower()
    text = title + " " + url
    
    matched_categories = []
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in text:
                matched_categories.append(category)
                break
    
    return matched_categories if matched_categories else ["其他"]

def calculate_importance(article):
    """计算文章重要性分数"""
    score = 0
    
    # 来源优先级
    priority_scores = {"high": 3, "medium": 2, "low": 1}
    score += priority_scores.get(article.get("priority", "medium"), 1)
    
    # 标题关键词权重
    title = article.get("title", "").lower()
    important_keywords = [
        ("发布", 2), ("突破", 3), ("融资", 2), ("开源", 2),
        ("gpt", 3), ("claude", 3), ("gemini", 3), ("deepseek", 3),
        ("openai", 3), ("google", 2), ("meta", 2), ("anthropic", 3),
        ("英伟达", 2), ("芯片", 2), ("大模型", 2), ("ai", 1)
    ]
    
    for keyword, weight in important_keywords:
        if keyword in title:
            score += weight
    
    return score

def process_data():
    """处理当天爬取的数据"""
    print(f"[{datetime.now().isoformat()}] 开始处理数据...")
    
    # 加载分类配置
    categories = load_categories()
    
    # 读取所有原始数据
    all_articles = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for file in RAW_DIR.glob("news_*.json"):
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
    
    # 分类
    categorized = defaultdict(list)
    for article in unique_articles:
        # 自动分类
        auto_categories = categorize_article(article, categories)
        article["auto_categories"] = auto_categories
        
        # 计算重要性
        article["importance_score"] = calculate_importance(article)
        
        for cat in auto_categories:
            categorized[cat].append(article)
    
    # 按重要性排序
    for cat in categorized:
        categorized[cat].sort(key=lambda x: x.get("importance_score", 0), reverse=True)
    
    # 保存处理后的数据
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / f"processed_{today}.json"
    
    output_data = {
        "date": today,
        "process_time": datetime.now().isoformat(),
        "total_articles": len(unique_articles),
        "categories": {k: len(v) for k, v in categorized.items()},
        "categorized_articles": dict(categorized),
        "top_articles": sorted(unique_articles, key=lambda x: x.get("importance_score", 0), reverse=True)[:20]
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成! 共 {len(unique_articles)} 条资讯")
    print(f"分类统计: {dict((k, len(v)) for k, v in categorized.items())}")
    print(f"保存至: {output_file}")
    
    return output_data

if __name__ == "__main__":
    process_data()