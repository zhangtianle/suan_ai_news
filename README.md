# Tech News Aggregator 项目

## 项目结构
```
tech-news/
├── README.md           # 项目说明
├── sources/            # 资讯源配置
├── scripts/
│   ├── crawler_v5.py   # ✅ 稳定版爬虫（推荐使用）
│   ├── processor.py    # 数据分类处理
│   └── analyzer.py     # 每日分析报告
├── data/
│   ├── raw/            # 原始爬取数据
│   └── processed/      # 处理后分类数据
├── output/             # 每日分析报告输出
└── logs/               # 日志文件
```

## 数据源（已验证可用）

| 网站 | 状态 | 平均条数 |
|------|------|---------|
| IT之家 | ✅ 稳定 | 100条 |
| InfoQ | ✅ 稳定 | 40条 |
| 量子位 | ✅ 稳定 | 30条 |
| 虎嗅 | ✅ 稳定 | 33条 |
| 智源社区 | ✅ 稳定 | 1条 |
| **合计** | | **~204条** |

## 定时任务

| 任务 | 时间 | 内容 |
|------|------|------|
| tech-news-crawler | 每小时 | 爬取+分类 |
| tech-news-analyzer | 每日17:00 | 生成报告发送 |

## 爬虫版本说明

- **v5 (推荐)**: 稳定版，25秒完成，204条
- v4: 重试机制过久，可能超时
- v3: 编码问题
- v2: 有效但不够稳定
- v1: 初始版本

## 使用方法

```bash
# 手动执行爬取
cd /home/admin/.openclaw/workspace/tech-news
python3 scripts/crawler_v5.py
python3 scripts/processor.py

# 生成分析报告
python3 scripts/analyzer.py
```