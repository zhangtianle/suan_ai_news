#!/usr/bin/env python3
"""
数据处理和分类脚本 v2
- 优化分类准确率（结合关键词+来源分类）
- 增强重要性评分算法
- 支持多级分类
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

# 扩展的分类关键词（更全面覆盖）
EXTENDED_KEYWORDS = {
    "AI": [
        "人工智能", "大模型", "机器学习", "深度学习", "LLM", "GPT", "Claude", "Gemini",
        "OpenAI", "Anthropic", "DeepSeek", "智谱", "GLM", "千问", "豆包", "Kimi",
        "文心", "通义", "AI", "AGI", "Transformer", "神经网络", "NLP", "ChatGPT",
        "Sora", "Agent", "智能体", "RAG", "多模态", "AIGC", "生成式", "AI模型",
        "大语言模型", "推理模型", "蒸馏", "训练", "微调", "提示词", "Prompt",
        "ChatBot", "对话", "语音识别", "图像识别", "自然语言", "知识图谱"
    ],
    "芯片": [
        "芯片", "GPU", "CPU", "半导体", "英伟达", "NVIDIA", "华为", "算力", "TPU",
        "AMD", "Intel", "高通", "联发科", "台积电", "中芯国际", "制程", "光刻",
        "晶圆", "封装", "SoC", "FPGA", "ASIC", "HBM", "内存", "存储", "显卡",
        "处理器", "架构", "指令集", "RISC-V", "ARM", "x86", "量子芯片"
    ],
    "互联网": [
        "互联网", "电商", "社交", "字节", "阿里", "腾讯", "美团", "拼多多", "京东",
        "百度", "快手", "抖音", "小红书", "B站", "知乎", "微博", "微信", "淘宝",
        "天猫", "外卖", "直播", "短视频", "平台", "流量", "用户增长", "运营",
        "商业化", "变现", "私域", "公域", "搜索", "推荐算法", "广告"
    ],
    "创业投资": [
        "融资", "投资", "创业", "IPO", "估值", "独角兽", "种子轮", "A轮", "B轮",
        "C轮", "VC", "PE", "风投", "并购", "上市", "纳斯达克", "港交所", "科创板",
        "创始人", "CEO", "估值", "市值", "股价", "财报", "营收", "利润", "亏损",
        "融资额", "投资人", "股东", "股权", "稀释", "天使投资"
    ],
    "前沿科技": [
        "量子计算", "机器人", "自动驾驶", "AR/VR", "元宇宙", "脑机接口", "无人机",
        "卫星", "航天", "太空", "火星", "新能源", "电池", "电动汽车", "自动驾驶",
        "无人驾驶", "特斯拉", "蔚来", "理想", "小鹏", "小米汽车", "比亚迪",
        "可控核聚变", "生物科技", "基因编辑", "CRISPR"
    ],
    "开源": [
        "开源", "GitHub", "Linux", "开源模型", "Apache", "MIT", "BSD", "GPL",
        "开源社区", "贡献者", "Issue", "PR", "Fork", "Star", "开源协议",
        "Hugging Face", "ModelScope", "开放源代码"
    ],
    "智能硬件": [
        "手机", "iPhone", "Android", "智能手表", "智能眼镜", "耳机", "平板", "笔记本",
        "PC", "电脑", "显示器", "键盘", "鼠标", "路由器", "智能家居", "IoT",
        "可穿戴", "VR头显", "AR眼镜", "Meta Quest", "Apple Vision", "折叠屏",
        "相机", "摄影", "无人机", "游戏机", "Switch", "PS5", "Xbox"
    ],
    "云计算": [
        "云计算", "云服务", "AWS", "Azure", "阿里云", "腾讯云", "华为云", "Google Cloud",
        "服务器", "容器", "Kubernetes", "Docker", "微服务", "Serverless", "边缘计算",
        "CDN", "数据库", "中间件", "SaaS", "PaaS", "IaaS", "DevOps", "CI/CD"
    ],
    "安全": [
        "安全", "漏洞", "攻击", "黑客", "勒索软件", "病毒", "木马", "钓鱼", "加密",
        "隐私", "数据泄露", "网络安全", "信息安全", "零信任", "防火墙", "渗透测试",
        "安全认证", "密码", "身份验证", "双因素", "生物识别"
    ]
}

def categorize_article(article, categories):
    """对文章进行分类 - 优化版"""
    title = article.get("title", "")
    url = article.get("url", "")
    source_categories = article.get("categories", [])  # 来源预定义分类
    
    text = (title + " " + url).lower()
    
    matched_categories = []
    match_scores = {}  # 记录每个分类的匹配得分
    
    # 1. 首先检查来源预定义分类（高权重）
    for cat in source_categories:
        # 映射来源分类到标准分类
        cat_mapping = {
            "AI": "AI", "深度学习": "AI", "大模型": "AI", "机器学习": "AI",
            "芯片": "芯片", "GPU": "芯片", "半导体": "芯片", "算力": "芯片",
            "互联网": "互联网", "电商": "互联网", "社交": "互联网",
            "科技": "前沿科技", "数码": "智能硬件", "硬件": "智能硬件",
            "创业": "创业投资", "投资": "创业投资", "融资": "创业投资",
            "开源": "开源", "技术": "云计算", "架构": "云计算", "编程": "云计算",
            "研究": "AI", "量子计算": "前沿科技", "国际": "前沿科技"
        }
        mapped_cat = cat_mapping.get(cat, cat)
        if mapped_cat in EXTENDED_KEYWORDS:
            match_scores[mapped_cat] = match_scores.get(mapped_cat, 0) + 3  # 来源分类加分
    
    # 2. 使用扩展关键词匹配标题和URL
    for category, keywords in EXTENDED_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text:
                # 标题中的关键词权重更高
                if keyword_lower in title.lower():
                    score += 2
                else:
                    score += 1
        
        if score > 0:
            match_scores[category] = match_scores.get(category, 0) + score
    
    # 3. 选择得分最高的分类（最多选3个）
    sorted_cats = sorted(match_scores.items(), key=lambda x: x[1], reverse=True)
    for cat, score in sorted_cats[:3]:
        if score >= 2:  # 最低阈值
            matched_categories.append(cat)
    
    return matched_categories if matched_categories else ["其他"]

def calculate_importance(article):
    """计算文章重要性分数 - 优化版"""
    score = 0
    title = article.get("title", "")
    title_lower = title.lower()
    source = article.get("source", "")
    
    # 1. 来源权重（权威媒体加分）
    source_weights = {
        "量子位": 3, "机器之心": 3, "智源社区": 3, "InfoQ": 2, "虎嗅": 2,
        "IT之家": 2, "TechCrunch": 3, "TheVerge": 3, "Wired": 2, "雷锋网": 2,
        "PingWest": 2, "爱范儿": 2, "驱动之家": 1
    }
    score += source_weights.get(source, 1)
    
    # 2. 来源优先级
    priority_scores = {"high": 3, "medium": 2, "low": 1}
    score += priority_scores.get(article.get("priority", "medium"), 1)
    
    # 3. 核心关键词权重（高权重）
    core_keywords = [
        # AI 公司/产品（最高权重）
        ("OpenAI", 5), ("openai", 5), ("DeepSeek", 5), ("deepseek", 5),
        ("Anthropic", 5), ("anthropic", 5), ("Claude", 4), ("claude", 4),
        ("GPT", 4), ("gpt", 4), ("Gemini", 4), ("gemini", 4),
        ("ChatGPT", 4), ("chatgpt", 4), ("Sora", 4), ("sora", 4),
        ("GLM", 4), ("智谱", 4), ("千问", 4), ("豆包", 3), ("Kimi", 3),
        ("Llama", 3), ("Mistral", 3), ("xAI", 3),
        
        # 重要事件关键词
        ("发布", 3), ("推出", 2), ("开源", 3), ("突破", 4), ("首次", 3),
        ("融资", 3), ("收购", 3), ("上市", 2), ("IPO", 2),
        
        # 技术关键词
        ("大模型", 3), ("AI", 2), ("AGI", 3), ("Agent", 3), ("智能体", 3),
        ("多模态", 2), ("Transformer", 2), ("推理", 2),
        
        # 芯片公司
        ("英伟达", 3), ("NVIDIA", 3), ("nvidia", 3), ("台积电", 2),
        ("AMD", 2), ("Intel", 2), ("高通", 2),
        
        # 科技巨头
        ("Google", 2), ("Meta", 2), ("微软", 2), ("Microsoft", 2),
        ("苹果", 2), ("Apple", 2), ("特斯拉", 2), ("Tesla", 2),
        ("华为", 2), ("字节", 2), ("阿里", 2), ("腾讯", 2),
        
        # 负面/争议（也重要）
        ("争议", 2), ("离职", 2), ("裁员", 2), ("诉讼", 2), ("调查", 2)
    ]
    
    for keyword, weight in core_keywords:
        if keyword in title or keyword.lower() in title_lower:
            score += weight
    
    # 4. 标题特征加分
    # 疑问句/感叹句通常更吸引眼球
    if "！" in title or "?" in title or "？" in title:
        score += 1
    
    # 包含数字（通常是有数据的报道）
    if re.search(r'\d+', title):
        score += 1
    
    # 5. 降权处理
    # 纯导航/标签页
    skip_patterns = ["tag/", "category/", "author/", "/page/", "rss", "sitemap"]
    url = article.get("url", "").lower()
    for pattern in skip_patterns:
        if pattern in url:
            score -= 5
            break
    
    # 标题过短或过长
    if len(title) < 8 or len(title) > 100:
        score -= 2
    
    return max(score, 1)  # 最低分为1

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