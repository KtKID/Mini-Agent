---
name: jina-reader
description: 使用 jina.ai Reader 抓取网页内容，绕过付费墙，获取干净的 Markdown 格式
---

# Jina Reader

使用 jina.ai Reader 服务抓取任何网页的干净 Markdown 内容。

## 功能

1. **绕过付费墙** - 可以获取需要登录才能查看的付费内容
2. **抓取 X（推特）** - 能够抓取推特上的推文信息
3. **输出 Markdown** - 返回干净的 AI 友好的 Markdown 格式
4. **免费使用** - 无需 API key，直接使用
5. **RSS新闻采集** - 结合 [RSS News Skill](./rss-news) 可以采集完整新闻内容

## 使用方法

在任何网址前面加上 `https://r.jina.ai/` 前缀即可。

**语法：**
```
https://r.jina.ai/<目标URL>
```

**示例：**
- 目标：`https://example.com/article`
- 访问：`https://r.jina.ai/https://example.com/article`

## 执行步骤

1. 确定要抓取的网页 URL
2. 在 URL 前添加 `https://r.jina.ai/` 前缀
3. 使用 `read_file` 或 curl 命令访问生成的 URL
4. 解析返回的 Markdown 内容

## 结合 RSS News 使用

如果需要批量采集新闻并获取完整内容，建议使用 **RSS News Skill**：

```bash
# 使用 rss_news skill 采集带完整内容的新闻
python3 mini_agent/skills/rss_news/rss_news.py --jina --format markdown
```

详细使用方法请参考 [RSS News Skill](./rss-news)

## 注意事项

- 如果目标 URL 以 https:// 开头，只需要替换为 `https://r.jina.ai/https://`
- 如果目标 URL 以 http:// 开头，只需要替换为 `https://r.jina.ai/http://`
- 返回的内容是纯 Markdown 文本，需要自行解析提取需要的信息
