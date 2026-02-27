#!/bin/bash
# 统一资讯爬取和分析脚本

cd /home/admin/.openclaw/workspace/tech-news

echo "=========================================="
echo "  资讯爬取与分析系统"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. 科技资讯
echo ""
echo "📡 [1/6] 爬取科技资讯..."
python3 scripts/tech_crawler.py

echo ""
echo "📊 [2/6] 处理科技资讯数据..."
python3 scripts/tech_processor.py

echo ""
echo "📝 [3/6] 生成科技资讯报告..."
python3 scripts/tech_analyzer.py

# 2. 财经资讯
echo ""
echo "💰 [4/6] 爬取财经资讯..."
python3 scripts/finance_crawler.py

echo ""
echo "📊 [5/6] 处理财经资讯数据..."
python3 scripts/finance_processor.py

echo ""
echo "📝 [6/6] 生成财经分析报告..."
python3 scripts/finance_analyzer.py

echo ""
echo "=========================================="
echo "  ✅ 全部完成!"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""
echo "📁 报告位置:"
echo "   - output/tech/     科技资讯报告"
echo "   - output/finance/  财经分析报告"