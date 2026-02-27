#!/usr/bin/env python3
"""
每日分析报告生成器
下午5点执行，生成500字摘要和2000字详细分析
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"

def load_processed_data():
    """加载处理后的数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = PROCESSED_DIR / f"processed_{today}.json"
    
    if not file_path.exists():
        # 尝试加载最近的数据
        files = sorted(PROCESSED_DIR.glob("processed_*.json"), reverse=True)
        if files:
            file_path = files[0]
    
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None

def generate_summary(data):
    """生成500字摘要"""
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = data.get("total_articles", 0)
    categories = data.get("categories", {})
    top_articles = data.get("top_articles", [])[:10]
    
    summary = f"""# 科技资讯日报 - {date}

## 📊 今日概览
- **总资讯数**: {total} 条
- **主要分类**: {', '.join([f"{k}({v}条)" for k, v in list(categories.items())[:5]])}

## 🔥 热点聚焦
"""
    
    for i, article in enumerate(top_articles[:5], 1):
        title = article.get("title", "")[:50]
        source = article.get("source", "")
        summary += f"{i}. **{title}** - {source}\n"
    
    summary += """
## 💡 今日要点
"""
    
    # 按分类提取要点
    categorized = data.get("categorized_articles", {})
    
    # AI 相关
    ai_articles = categorized.get("AI", [])[:3]
    if ai_articles:
        summary += "\n### 🤖 AI/大模型\n"
        for a in ai_articles:
            summary += f"- {a.get('title', '')[:60]}\n"
    
    # 芯片相关
    chip_articles = categorized.get("芯片", [])[:3]
    if chip_articles:
        summary += "\n### 💻 芯片/算力\n"
        for a in chip_articles:
            summary += f"- {a.get('title', '')[:60]}\n"
    
    # 互联网相关
    internet_articles = categorized.get("互联网", [])[:3]
    if internet_articles:
        summary += "\n### 🌐 互联网\n"
        for a in internet_articles:
            summary += f"- {a.get('title', '')[:60]}\n"
    
    summary += f"""

---
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    return summary

def generate_detailed_report(data):
    """生成2000字详细报告"""
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = data.get("total_articles", 0)
    categories = data.get("categories", {})
    top_articles = data.get("top_articles", [])
    categorized = data.get("categorized_articles", {})
    
    report = f"""# 科技资讯深度分析报告
## {date}

---

## 一、今日数据概览

本日共收集科技资讯 **{total}** 条，来源涵盖国内外主流科技媒体。

### 分类分布
"""
    
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        report += f"- **{cat}**: {count} 条 ({percentage:.1f}%)\n"
    
    report += """

---

## 二、重点新闻深度解读

"""
    
    # 详细分析前10条
    for i, article in enumerate(top_articles[:10], 1):
        title = article.get("title", "未知标题")
        source = article.get("source", "未知来源")
        url = article.get("url", "")
        score = article.get("importance_score", 0)
        cats = article.get("auto_categories", [])
        
        report += f"""### {i}. {title}

**来源**: {source}  
**分类**: {', '.join(cats)}  
**重要性**: {'⭐' * min(score, 5)}  
**链接**: {url}

"""
        
        # 添加简要分析
        if "发布" in title or "推出" in title:
            report += "> 📢 **产品发布动态** - 值得关注的新产品/新功能发布\n\n"
        elif "融资" in title or "投资" in title:
            report += "> 💰 **资本动态** - 行业资本流向值得关注\n\n"
        elif "突破" in title or "首次" in title:
            report += "> 🚀 **技术突破** - 行业里程碑事件\n\n"
        
        report += "---\n\n"
    
    # 分类深度分析
    report += """## 三、行业趋势分析

"""
    
    # AI板块
    ai_articles = categorized.get("AI", [])
    if ai_articles:
        report += f"""### 🤖 AI/大模型板块 ({len(ai_articles)}条)

本日AI相关资讯共{len(ai_articles)}条，主要涉及：

"""
        for a in ai_articles[:8]:
            report += f"- {a.get('title', '')}\n"
        
        report += """
**趋势洞察**: """
        
        # 简单趋势判断
        ai_titles = " ".join([a.get("title", "") for a in ai_articles])
        if "开源" in ai_titles:
            report += "开源模型持续活跃，社区生态繁荣发展。"
        if "Agent" in ai_titles or "智能体" in ai_titles:
            report += "AI Agent成为新的竞争焦点，各大厂商加速布局。"
        if "多模态" in ai_titles:
            report += "多模态技术快速演进，应用场景不断拓展。"
        
        report += "\n\n"
    
    # 芯片板块
    chip_articles = categorized.get("芯片", [])
    if chip_articles:
        report += f"""### 💻 芯片/算力板块 ({len(chip_articles)}条)

"""
        for a in chip_articles[:5]:
            report += f"- {a.get('title', '')}\n"
        report += "\n"
    
    # 互联网板块
    internet_articles = categorized.get("互联网", [])
    if internet_articles:
        report += f"""### 🌐 互联网/巨头板块 ({len(internet_articles)}条)

"""
        for a in internet_articles[:5]:
            report += f"- {a.get('title', '')}\n"
        report += "\n"
    
    # 投资板块
    invest_articles = categorized.get("创业投资", [])
    if invest_articles:
        report += f"""### 💵 投资/融资板块 ({len(invest_articles)}条)

"""
        for a in invest_articles[:5]:
            report += f"- {a.get('title', '')}\n"
        report += "\n"
    
    report += f"""---

## 四、明日关注点

基于今日数据分析，建议关注以下方向：

1. **大模型竞争格局** - 关注OpenAI、Google、Anthropic等头部玩家动态
2. **国产算力突破** - 芯片自主可控进程值得持续跟踪
3. **应用落地进展** - AI应用商业化进入关键期
4. **资本流向变化** - 投资热点可能预示下一波风口

---

## 五、数据来源

本报告数据来源于：
"""
    
    sources = set(a.get("source", "") for a in top_articles)
    for source in sources:
        report += f"- {source}\n"
    
    report += f"""

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*由 Tech News Aggregator 自动生成*
"""
    
    return report

def main():
    """主函数"""
    print(f"[{datetime.now().isoformat()}] 开始生成分析报告...")
    
    # 加载数据
    data = load_processed_data()
    
    if not data:
        print("错误: 未找到处理后的数据")
        return
    
    # 生成报告
    summary = generate_summary(data)
    detailed = generate_detailed_report(data)
    
    # 保存报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    # 按时间分类保存
    year_month = date[:7]  # 2026-02
    day_dir = OUTPUT_DIR / year_month
    day_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存摘要
    summary_file = day_dir / f"summary_{date}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"摘要已保存: {summary_file}")
    
    # 保存详细报告
    detailed_file = day_dir / f"detailed_{date}.md"
    with open(detailed_file, "w", encoding="utf-8") as f:
        f.write(detailed)
    print(f"详细报告已保存: {detailed_file}")
    
    # 保存完整JSON
    json_file = day_dir / f"report_{date}.json"
    report_data = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "detailed_report": detailed,
        "stats": {
            "total_articles": data.get("total_articles", 0),
            "categories": data.get("categories", {})
        }
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告生成完成!")
    
    return report_data

if __name__ == "__main__":
    main()