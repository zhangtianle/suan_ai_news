# Tech News Aggregator 项目

## 项目结构
```
tech-news/
├── README.md           # 项目说明
├── sources/            # 资讯源配置
├── scripts/
│   ├── crawler_v6.py   # ✅ 国际增强版爬虫（推荐）
│   ├── processor.py    # 数据分类处理
│   └── analyzer_v2.py  # 分析报告生成（带来源链接）
├── data/
│   ├── raw/            # 原始爬取数据
│   └── processed/      # 处理后分类数据
├── output/             # 每日分析报告输出
└── logs/               # 日志文件
```

## 数据源（v6 国际增强版）

### 国内数据源 (12个)
| 网站 | 类型 | 平均条数 | 发布时间 |
|------|------|---------|----------|
| IT之家 | 科技新闻 | 80条 | ❌ |
| InfoQ | 技术媒体 | 40条 | ❌ |
| 量子位 | AI媒体 | 30条 | ❌ |
| 虎嗅 | 商业科技 | 28条 | ❌ |
| 智源社区 | AI研究 | 1条 | ❌ |
| 雷锋网 | AI媒体 | 45条 | ❌ |
| PingWest | 科技媒体 | 44条 | ❌ |
| 爱范儿 | 数码媒体 | 34条 | ❌ |
| 驱动之家 | 硬件新闻 | 80条 | ❌ |
| 36氪 | 创投媒体 | 待定 | ❌ |
| 机器之心 | AI研究 | 6条 | ❌ |

### 海外数据源 (14个)
| 网站 | 类型 | 数据格式 | 平均条数 | 发布时间 |
|------|------|---------|---------|----------|
| TechCrunch | 科技/创业 | RSS | 20条 | ✅ |
| TheVerge | 科技/数码 | RSS+HTML | 80条 | ✅ |
| Wired | 科技/文化 | RSS | 50条 | ✅ |
| Ars Technica | 深度科技 | RSS | 20条 | ✅ |
| Engadget | 数码消费 | RSS | 50条 | ✅ |
| VentureBeat | 科技/AI | RSS | 7条 | ✅ |
| MIT Technology Review | 科技前沿 | RSS | 10条 | ✅ |
| TheRegister | IT新闻 | HTML | 60条 | ❌ |
| BBC Technology | 科技新闻 | RSS | 50条 | ✅ |
| Reuters Tech | 科技新闻 | RSS | 待定 | ✅ |
| Hacker News | 技术社区 | RSS | 20条 | ✅ |
| Dev.to | 开发者社区 | RSS | 11条 | ✅ |
| AI News | AI专业 | RSS | 12条 | ✅ |
| Synced | AI研究 | RSS | 10条 | ✅ |

### 数据统计
- **总数据源**: 26个（国内12 + 海外14）
- **日均资讯**: 1200+ 条
- **支持发布时间**: 16个数据源

## 定时任务

| 任务 | 时间 | 内容 |
|------|------|------|
| tech-news-crawler | 每小时 | 爬取+分类 |
| tech-news-analyzer | 每日17:00 | 生成报告发送 |

## 使用方法

```bash
# 手动执行爬取（国际增强版）
cd /home/admin/.openclaw/workspace/tech-news
python3 scripts/crawler_v6.py
python3 scripts/processor.py

# 生成分析报告（带来源链接和发布时间）
python3 scripts/analyzer_v2.py
```

## 版本说明

### v6 (推荐)
- ✅ 新增 14 个海外数据源
- ✅ 支持 RSS 订阅自动提取发布时间
- ✅ 数据量提升 128% (564 → 1285 条)
- ✅ 国际化资讯覆盖

### v5
- 稳定版，25秒完成，204条
- 仅国内数据源

## 报告格式

### 摘要报告 (summary_YYYY-MM-DD.md)
- 500字精简版
- 包含来源链接和发布时间
- 分类要点提炼

### 详细报告 (detailed_YYYY-MM-DD.md)
- 2000字深度分析
- 行业趋势洞察
- 重要新闻解读