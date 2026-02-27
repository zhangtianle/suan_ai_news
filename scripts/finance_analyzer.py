#!/usr/bin/env python3
"""
Finance News Analyzer v1
财经新闻分析报告 - 投资者视角

报告内容:
1. 市场情绪概览 - 多空力量对比
2. 重要政策解读 - 对市场的影响
3. 行业热点追踪 - 板块轮动信号
4. 个股关注清单 - 重要标的动态
5. 风险预警提示 - 需要规避的风险
"""

import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/home/admin/.openclaw/workspace/tech-news")
PROCESSED_DIR = PROJECT_ROOT / "data" / "finance" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output" / "finance"

def load_processed_data():
    """加载处理后的数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = PROCESSED_DIR / f"processed_{today}.json"
    
    if not file_path.exists():
        files = sorted(PROCESSED_DIR.glob("processed_*.json"), reverse=True)
        if files:
            file_path = files[0]
    
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    return None

def format_pub_date(pub_date):
    """格式化发布时间"""
    if not pub_date:
        return "未知时间"
    
    if len(pub_date) > 10:
        try:
            dt = datetime.strptime(pub_date[:19], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff = (now - dt).total_seconds()
            
            if diff < 3600:
                return f"{int(diff/60)}分钟前"
            elif diff < 86400:
                return f"{int(diff/3600)}小时前"
            else:
                return dt.strftime("%m-%d %H:%M")
        except:
            pass
    
    return pub_date

def get_signal_emoji(signal):
    """获取信号图标"""
    if signal == "bullish":
        return "📈"
    elif signal == "bearish":
        return "📉"
    else:
        return "➖"

def generate_summary(data):
    """生成投资摘要 - 投资者视角"""
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = data.get("total_articles", 0)
    signal_stats = data.get("signal_stats", {})
    categories = data.get("categories", {})
    top_articles = data.get("top_articles", [])[:10]
    sector_stats = data.get("sector_stats", {})
    
    # 计算市场情绪指数
    bullish = signal_stats.get("bullish", 0)
    bearish = signal_stats.get("bearish", 0)
    neutral = signal_stats.get("neutral", 0)
    total_signals = bullish + bearish + neutral
    
    if total_signals > 0:
        sentiment_ratio = (bullish - bearish) / total_signals
        if sentiment_ratio > 0.2:
            sentiment = "偏多 📈"
            sentiment_desc = "市场情绪乐观，利好消息占优"
        elif sentiment_ratio < -0.2:
            sentiment = "偏空 📉"
            sentiment_desc = "市场情绪谨慎，需注意风险"
        else:
            sentiment = "中性 ➖"
            sentiment_desc = "市场多空平衡，观望为主"
    else:
        sentiment = "中性 ➖"
        sentiment_desc = "数据不足"
    
    summary = f"""# 财经资讯日报 - {date}

## 📊 市场情绪概览

| 指标 | 数值 | 解读 |
|------|------|------|
| **情绪指数** | {sentiment} | {sentiment_desc} |
| **利好消息** | {bullish} 条 | 📈 做多信号 |
| **利空消息** | {bearish} 条 | 📉 风险提示 |
| **中性消息** | {neutral} 条 | ➖ 观望信号 |

### 📈 热门板块 TOP 5

| 排名 | 板块 | 新闻数 | 信号 |
|------|------|--------|------|
"""
    
    for i, (sector, count) in enumerate(list(sector_stats.items())[:5], 1):
        summary += f"| {i} | **{sector}** | {count} 条 | {'🔥' if count > 10 else '📈'} |\n"
    
    summary += f"""
---

## 🔥 今日热点 TOP 10

"""
    
    for i, article in enumerate(top_articles[:10], 1):
        title = article.get("title", "")[:55]
        url = article.get("url", "")
        source = article.get("source", "")
        signal = article.get("market_signal", {}).get("overall", "neutral")
        signal_icon = get_signal_emoji(signal)
        pub_time = format_pub_date(article.get("pub_date", ""))
        
        summary += f"{i}. {signal_icon} **[{title}]({url})**\n"
        summary += f"   - 📰 {source} | ⏰ {pub_time}\n\n"
    
    # 分类要点
    categorized = data.get("categorized_articles", {})
    
    # 宏观政策
    macro_articles = categorized.get("宏观政策", [])[:5]
    if macro_articles:
        summary += "## 🏛️ 宏观政策\n\n"
        for a in macro_articles:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            summary += f"- [{title}]({url}) *{source}*\n"
        summary += "\n"
    
    # 行业板块
    sector_articles = categorized.get("行业板块", [])[:5]
    if sector_articles:
        summary += "## 🏭 行业动态\n\n"
        for a in sector_articles:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            summary += f"- [{title}]({url}) *{source}*\n"
        summary += "\n"
    
    # 风险预警
    risk_articles = data.get("risk_articles", [])[:5]
    if risk_articles:
        summary += "## ⚠️ 风险提示\n\n"
        for a in risk_articles:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            summary += f"- 🚨 [{title}]({url}) *{source}*\n"
        summary += "\n"
    
    summary += f"""
---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*🍄 蒜宝财经分析*
"""
    
    return summary

def generate_detailed_report(data):
    """生成详细投资报告"""
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = data.get("total_articles", 0)
    signal_stats = data.get("signal_stats", {})
    categories = data.get("categories", {})
    top_articles = data.get("top_articles", [])
    categorized = data.get("categorized_articles", {})
    sector_stats = data.get("sector_stats", {})
    entity_stats = data.get("entity_stats", {})
    risk_articles = data.get("risk_articles", [])
    
    # 市场情绪分析
    bullish = signal_stats.get("bullish", 0)
    bearish = signal_stats.get("bearish", 0)
    neutral = signal_stats.get("neutral", 0)
    
    report = f"""# 财经资讯深度分析报告
## {date}

---

## 一、市场情绪分析

### 1.1 情绪指数

本日共收集财经资讯 **{total}** 条，多空信号分布如下：

| 信号类型 | 数量 | 占比 | 解读 |
|----------|------|------|------|
| 📈 利好 | {bullish} | {bullish/total*100:.1f}% | 做多信号 |
| 📉 利空 | {bearish} | {bearish/total*100:.1f}% | 风险信号 |
| ➖ 中性 | {neutral} | {neutral/total*100:.1f}% | 观望信号 |

### 1.2 情绪判断

"""
    
    sentiment_ratio = (bullish - bearish) / total if total > 0 else 0
    
    if sentiment_ratio > 0.3:
        report += "**市场情绪: 偏多 📈**\n\n利好消息明显占优，市场信心较强。建议关注：\n"
        report += "- 顺势布局强势板块\n- 关注业绩超预期个股\n- 注意获利了结时机\n\n"
    elif sentiment_ratio < -0.3:
        report += "**市场情绪: 偏空 📉**\n\n利空消息较多，市场谨慎情绪升温。建议：\n"
        report += "- 控制仓位，规避风险\n- 关注防御性板块\n- 等待市场企稳信号\n\n"
    else:
        report += "**市场情绪: 中性 ➖**\n\n多空力量相对平衡，市场处于观望状态。建议：\n"
        report += "- 保持中性仓位\n- 关注政策信号\n- 精选结构性机会\n\n"
    
    # 板块分析
    report += """---

## 二、板块轮动分析

### 2.1 热门板块

"""
    
    for i, (sector, count) in enumerate(list(sector_stats.items())[:8], 1):
        percentage = count / total * 100 if total > 0 else 0
        heat = "🔥🔥🔥" if count > 15 else "🔥🔥" if count > 8 else "🔥"
        report += f"| {i} | **{sector}** | {count} 条 | {percentage:.1f}% | {heat} |\n"
    
    report += """

### 2.2 板块解读

"""
    
    # 根据热门板块给出投资建议
    if "半导体" in sector_stats or "芯片" in sector_stats:
        report += "**半导体板块**: 科技自主主线持续，关注国产替代机会\n\n"
    if "新能源" in sector_stats:
        report += "**新能源板块**: 政策支持力度大，但需注意估值风险\n\n"
    if "医药" in sector_stats:
        report += "**医药板块**: 创新药政策回暖，可逢低布局\n\n"
    if "银行" in sector_stats or "券商" in sector_stats:
        report += "**金融板块**: 关注利率政策变化带来的机会\n\n"
    
    # 宏观政策
    report += """---

## 三、宏观政策解读

"""
    
    macro_articles = categorized.get("宏观政策", [])
    if macro_articles:
        report += f"本日宏观政策相关资讯共 **{len(macro_articles)}** 条：\n\n"
        
        for i, a in enumerate(macro_articles[:10], 1):
            title = a.get("title", "")
            url = a.get("url", "")
            source = a.get("source", "")
            pub_time = format_pub_date(a.get("pub_date", ""))
            signal = a.get("market_signal", {}).get("overall", "neutral")
            signal_icon = get_signal_emoji(signal)
            
            report += f"{i}. {signal_icon} [{title}]({url})\n"
            report += f"   - 来源: {source} | 时间: {pub_time}\n\n"
        
        # 政策影响分析
        report += "### 政策影响分析\n\n"
        
        macro_text = " ".join([a.get("title", "") for a in macro_articles])
        
        if "降息" in macro_text or "降准" in macro_text:
            report += "- **货币政策宽松信号**: 利好股市、债市，关注高弹性品种\n"
        if "加息" in macro_text or "收紧" in macro_text:
            report += "- **货币政策收紧信号**: 利空高估值成长股，关注防御品种\n"
        if "美联储" in macro_text:
            report += "- **美联储动态**: 关注对全球资产配置的影响\n"
        if "房地产" in macro_text or "楼市" in macro_text:
            report += "- **房地产政策**: 关注地产链及相关金融股\n"
        
        report += "\n"
    
    # 股市动态
    report += """---

## 四、股市动态

### 4.1 A股市场

"""
    
    a_stock_articles = categorized.get("A股市场", [])
    if a_stock_articles:
        report += f"A股相关资讯 **{len(a_stock_articles)}** 条：\n\n"
        
        for a in a_stock_articles[:8]:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            report += f"- [{title}]({url}) *{source}*\n"
        report += "\n"
    
    # 美股市场
    us_stock_articles = categorized.get("美股市场", [])
    if us_stock_articles:
        report += f"""### 4.2 美股市场

美股相关资讯 **{len(us_stock_articles)}** 条：

"""
        for a in us_stock_articles[:5]:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            report += f"- [{title}]({url}) *{source}*\n"
        report += "\n"
    
    # 商品期货
    futures_articles = categorized.get("商品期货", [])
    if futures_articles:
        report += f"""---

## 五、商品期货

期货相关资讯 **{len(futures_articles)}** 条：

"""
        for a in futures_articles[:8]:
            title = a.get("title", "")[:50]
            url = a.get("url", "")
            source = a.get("source", "")
            report += f"- [{title}]({url}) *{source}*\n"
        report += "\n"
    
    # 风险预警
    report += """---

## 六、风险预警

"""
    
    if risk_articles:
        report += f"⚠️ 本日风险相关资讯 **{len(risk_articles)}** 条，请重点关注：\n\n"
        
        for i, a in enumerate(risk_articles[:8], 1):
            title = a.get("title", "")
            url = a.get("url", "")
            source = a.get("source", "")
            
            report += f"{i}. 🚨 [{title}]({url})\n"
            report += f"   - 来源: {source}\n\n"
    else:
        report += "✅ 本日无明显风险预警信号。\n\n"
    
    # 投资建议
    report += f"""---

## 七、投资建议

### 7.1 仓位建议

| 投资者类型 | 建议仓位 | 理由 |
|------------|----------|------|
| **激进型** | 60-70% | 市场情绪{sentiment_ratio:+.1%}，可适当参与 |
| **稳健型** | 40-50% | 保持灵活，等待机会 |
| **保守型** | 20-30% | 控制风险为主 |

### 7.2 关注方向

"""
    
    # 根据数据给出关注方向
    top_sectors = list(sector_stats.keys())[:5]
    if top_sectors:
        report += f"1. **热点板块**: {', '.join(top_sectors[:3])}\n"
    
    if bullish > bearish * 1.5:
        report += "2. **策略**: 利好占优，可适当加仓\n"
    elif bearish > bullish * 1.5:
        report += "2. **策略**: 风险偏大，控制仓位\n"
    else:
        report += "2. **策略**: 观望为主，精选个股\n"
    
    report += "3. **风控**: 设置止损位，严格执行纪律\n"
    
    # 数据来源
    report += f"""

---

## 八、数据来源

本报告数据来源于国内外主流财经媒体：

"""
    
    sources = set(a.get("source", "") for a in top_articles[:30])
    for source in sorted(sources)[:15]:
        report += f"- {source}\n"
    
    report += f"""

---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*由 Finance News Analyzer v1 自动生成*  
*🍄 蒜宝财经分析 | 投资有风险，入市需谨慎*
"""
    
    return report

def main():
    """主函数"""
    print(f"[{datetime.now().isoformat()}] 开始生成财经分析报告...")
    
    data = load_processed_data()
    
    if not data:
        print("错误: 未找到处理后的数据")
        return
    
    summary = generate_summary(data)
    detailed = generate_detailed_report(data)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    year_month = date[:7]
    day_dir = OUTPUT_DIR / year_month
    day_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存摘要
    summary_file = day_dir / f"summary_{date}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 摘要已保存: {summary_file}")
    
    # 保存详细报告
    detailed_file = day_dir / f"detailed_{date}.md"
    with open(detailed_file, "w", encoding="utf-8") as f:
        f.write(detailed)
    print(f"✅ 详细报告已保存: {detailed_file}")
    
    # 保存JSON
    json_file = day_dir / f"report_{date}.json"
    report_data = {
        "date": date,
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "detailed_report": detailed,
        "stats": {
            "total_articles": data.get("total_articles", 0),
            "signal_stats": data.get("signal_stats", {}),
            "sector_stats": data.get("sector_stats", {}),
            "categories": data.get("categories", {})
        }
    }
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 财经报告生成完成!")
    
    return report_data

if __name__ == "__main__":
    main()