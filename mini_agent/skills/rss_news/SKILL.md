---
name: rss-news
description: "采集AI/科技RSS新闻，结合jina.ai Reader获取完整网页内容。当需要：(1) 收集今日AI行业新闻 (2) 获取最新科技动态 (3) 抓取OpenAI/NVIDIA等博客更新 (4) 批量采集多个RSS源的新闻摘要或全文 (5) 定时自动抓取新闻任务"
---

# RSS 新闻采集工具

## 概述

本 skill 用于采集 AI/科技领域的 RSS 新闻，并可选使用 jina.ai Reader 获取完整的网页内容，绕过付费墙。

## 功能特性

1. **多源 RSS 采集** - 同时从 OpenAI、MIT、Google、Microsoft、NVIDIA、Hugging Face、Anthropic 等 AI 博客获取新闻
2. **Jina Reader 集成** - 使用 `https://r.jina.ai/` 前缀获取完整网页内容
3. **绕过付费墙** - 可以获取需要登录才能查看的付费内容
4. **多格式输出** - 支持 text、markdown、json 三种输出格式
5. **来源过滤** - 支持指定只采集特定来源的新闻

## 支持的 RSS 源

| 来源 | RSS 地址 |
|------|----------|
| OpenAI Blog | https://openai.com/blog/rss.xml |
| MIT AI News | https://news.mit.edu/rss/topic/artificialintelligence2 |
| Google AI | https://blog.google/technology/ai/rss |
| Microsoft AI | https://blogs.microsoft.com/ai/feed |
| NVIDIA | https://blogs.nvidia.com/feed |
| Hugging Face | https://huggingface.co/blog/feed.xml |

> ⚠️ **注意**: Anthropic 官方 RSS 源已失效（返回 404），已从列表中移除。

## 使用方法

### 触发关键词

当用户请求以下内容时，应使用此 skill：

- "帮我收集今天的AI新闻"
- "获取最新的科技动态"
- "抓取OpenAI的博客更新"
- "今天的AI行业发生了什么"
- "帮我看看有什么AI新闻"
- "采集 RSS 新闻"
- "定时抓取新闻"
- "帮我整理一下最近的AI资讯"

### 基本命令

```bash
# 采集5条新闻（默认）
python3 mini_agent/skills/rss_news/rss_news.py

# 采集10条新闻
python3 mini_agent/skills/rss_news/rss_news.py --count 10

# 使用 jina.ai Reader 获取完整内容（绕过付费墙）
python3 mini_agent/skills/rss_news/rss_news.py --jina

# 输出为 Markdown 格式
python3 mini_agent/skills/rss_news/rss_news.py --format markdown

# 输出为 JSON 格式
python3 mini_agent/skills/rss_news/rss_news.py --format json

# 只采集特定来源
python3 mini_agent/skills/rss_news/rss_news.py --sources OpenAI NVIDIA

# 详细输出模式
python3 mini_agent/skills/rss_news/rss_news.py --verbose
```

### 组合使用示例

```bash
# 获取完整内容 + Markdown 输出 + 详细日志
python3 mini_agent/skills/rss_news/rss_news.py --jina --format markdown --verbose

# 采集3条 OpenAI 新闻，使用 JSON 输出
python3 mini_agent/skills/rss_news/rss_news.py --count 3 --sources OpenAI --format json
```

### 命令行参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--count` | `-c` | 采集新闻数量 | 5 |
| `--jina` | `-j` | 使用 jina.ai Reader 获取完整内容 | False |
| `--format` | `-f` | 输出格式 (text/markdown/json) | text |
| `--sources` | `-s` | 指定来源（可多个，空格分隔） | 全部 |
| `--verbose` | `-v` | 显示详细日志 | False |

## 输出示例

### Text 格式输出

```
======================================================================
今日Tech/AI RSS新闻
======================================================================

【Our First Proof submissions】
来源: OpenAI
链接: https://openai.com/index/first-proof-submissions
摘要: We're sharing our AI model's proof attempts for First Proof, a math challenge testing research-grade reasoning...
---------------------------------------------------------------------------
```

### Markdown 格式输出

```markdown
# 今日AI/科技新闻

*采集时间: 2024-01-21 10:30:00*

---

## 1. Our First Proof submissions

**来源**: OpenAI
**链接**: https://openai.com/index/first-proof-submissions

We're sharing our AI model's proof attempts for First Proof...

<details>
<summary>查看完整内容</summary>

[完整Markdown内容...]

</details>

---
```

## 结合 Jina Reader 使用

Jina Reader 可以绕过付费墙，获取完整文章内容。当需要：

- 获取需要登录的付费内容
- 获取推特(X)上的推文信息
- 获取完整的文章内容而非摘要

使用 jina.ai Reader 的语法：
```
https://r.jina.ai/<目标URL>
```

示例：
- 目标：`https://openai.com/blog/some-article`
- 访问：`https://r.jina.ai/https://openai.com/blog/some-article`

详细说明请参考 [jina-reader skill](../jina-reader)。

## 定时任务配置（可选）

如需定时自动执行，可以使用 crontab：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天早上9点执行）
0 9 * * * cd /Volumes/machub_app/proj/Mini-Agent && /usr/bin/python3 mini_agent/skills/rss_news/rss_news.py >> logs/ai_news_$(date +\%Y\%m\%d).log 2>&1
```

## 依赖说明

- Python 3.7+
- 无需额外安装包（使用内置 urllib 和 feedparser）
- feedparser 已包含在标准依赖中

## 注意事项

1. 使用 `--jina` 参数时会为每条新闻单独请求 jina.ai Reader，速度会较慢
2. 建议在需要获取完整文章内容时使用 `--jina` 参数
3. 默认只采集标题和摘要，速度更快
4. JSON 输出包含完整的 `full_content` 字段（当使用 `--jina` 时）
5. 部分网站（如 TechCrunch）可能因地区限制返回 HTTP 451 错误
