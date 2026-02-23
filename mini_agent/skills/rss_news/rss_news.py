#!/usr/bin/env python3
"""
AI/Tech RSS 新闻采集工具
使用 jina.ai Reader 获取完整新闻内容
使用方法: python3 rss_news.py [--count N] [--verbose]
"""

import feedparser
import html
import re
import urllib.request
import urllib.parse
import json
import sys
import argparse
from datetime import datetime

# AI/科技相关的RSS源列表
# type: 'rss' 表示传统RSS源，'web' 表示网页URL
RSS_SOURCES = [
    ("OpenAI", "https://openai.com/blog/rss.xml", "rss"),
    ("MIT AI", "https://news.mit.edu/rss/topic/artificialintelligence2", "rss"),
    ("Google AI", "https://blog.google/technology/ai/rss", "rss"),
    ("Microsoft AI", "https://blogs.microsoft.com/ai/feed", "rss"),
    ("NVIDIA", "https://blogs.nvidia.com/feed", "rss"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "rss"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "rss"),
    # Anthropic 来源 - 使用网页URL类型
    ("Anthropic News", "https://www.anthropic.com/news", "web"),
    ("Anthropic Engineering", "https://www.anthropic.com/engineering", "web"),
]

# Anthropic网页源的特殊处理 - 解析新闻列表页面
ANTHROPIC_WEB_SOURCES = {
    "Anthropic News": {
        "base_url": "https://www.anthropic.com/news",
        "list_selector": None,  # 使用jina直接抓取
    },
    "Anthropic Engineering": {
        "base_url": "https://www.anthropic.com/engineering", 
        "list_selector": None,
    },
}

def clean_html(text):
    """清理HTML标签"""
    if not text:
        return ""
    return re.sub('<[^<]+?>', '', text)

def fetch_anthropic_list(source_name, verbose=False):
    """
    使用 jina.ai Reader 获取 Anthropic 新闻/工程博客列表页面
    解析返回的 Markdown 内容，提取文章标题和链接
    """
    if source_name not in ANTHROPIC_WEB_SOURCES:
        return []
    
    source_info = ANTHROPIC_WEB_SOURCES[source_name]
    base_url = source_info["base_url"]
    
    try:
        # 使用 jina.ai Reader 获取列表页面
        jina_url = f"https://r.jina.ai/{base_url}"
        req = urllib.request.Request(
            jina_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            
            news_items = []
            
            # 匹配所有 anthroplic.com/news/ 或 anthroplic.com/engineering/ 的链接
            news_items = []
            lines = content.split('\n')

            for i, line in enumerate(lines):
                if 'anthropic.com/engineering/' not in line and 'anthropic.com/news/' not in line:
                    continue
                
                # 简单方法 - 找到所有 anthroplic.com/(news|engineering)/ 的URL
                # 使用更宽松的正则来匹配URL
                url_matches = re.findall(r'(https?://www\.anthropic\.com/(?:news|engineering)/[^\s\)\]]+)', line)
                
                for article_url in url_matches:
                    # 从行中提取标题
                    # 格式: [Alt](img) Title](article_url)
                    # 需要先移除图片链接，再提取标题
                    url_pos = line.find(article_url)
                    if url_pos != -1:
                        before = line[:url_pos]
                        
                        # 移除所有图片链接格式 ![...](url)
                        temp = before
                        while '![' in temp:
                            img_start = temp.find('![')
                            if img_start == -1:
                                break
                            img_link_end = temp.find('](', img_start)
                            if img_link_end == -1:
                                break
                            paren_start = img_link_end + 2
                            paren_end = temp.find(')', paren_start)
                            if paren_end == -1:
                                break
                            temp = temp[:img_start] + temp[paren_end+1:]
                        
                        # 现在找最后一个 ]( 前面就是标题
                        last_bracket_close = temp.rfind('](')
                        if last_bracket_close != -1:
                            title_start = temp.rfind('[', 0, last_bracket_close)
                            if title_start != -1:
                                title = temp[title_start+1:last_bracket_close]
                                
                                # 清理标题
                                title = title.strip()
                                if title.startswith('###'):
                                    title = title[3:].strip()
                                if title.startswith('Featured '):
                                    title = title[9:].strip()
                                
                                news_items.append({
                                    'title': title,
                                    'link': article_url,
                                    'source': source_name
                                })
            
            # 清理标题
            for item in news_items:
                cleaned_title = item['title']
                
                # 移除图片Alt文本前缀（如 "Image 1: "）
                alt_pattern = re.compile(r'^Image\s+\d+:\s*')
                cleaned_title = alt_pattern.sub('', cleaned_title)
                
                # 移除末尾的日期
                if re.search(r' [A-Za-z]{3}\s+\d{1,2},\s+\d{4}$', cleaned_title):
                    cleaned_title = re.sub(r' [A-Za-z]{3}\s+\d{1,2},\s+\d{4}$', '', cleaned_title)
                
                # 清理多余的空白
                cleaned_title = ' '.join(cleaned_title.split())
                
                item['title'] = cleaned_title
                
                # 移除类别前缀
                category_pattern = re.compile(r'^(Announcements|Product|Research|Policy)\s+')
                cleaned_title = category_pattern.sub('', cleaned_title)
                
                # 清理多余的空白
                cleaned_title = ' '.join(cleaned_title.split())
                
                # 更新标题
                item['title'] = cleaned_title
                item['title'] = cleaned_title
            
            # 过滤太短或太长或无意义的标题
            valid_items = []
            for item in news_items:
                if len(item['title']) > 10 and len(item['title']) < 200:
                    valid_items.append(item)
            
            # 去重（基于链接URL）
            seen = set()
            unique_items = []
            for item in valid_items:
                if item['link'] not in seen:
                    seen.add(item['link'])
                    unique_items.append(item)
            
            if verbose:
                print(f"  [Anthropic] Found {len(unique_items)} articles from {source_name}")
            
            return unique_items[:10]
            
    except Exception as e:
        if verbose:
            print(f"  [Anthropic] Error fetching {source_name}: {e}")
        return []

def fetch_jina_content(url, verbose=False):
    """
    使用 jina.ai Reader 获取网页详细内容
    语法: https://r.jina.ai/<目标URL>
    清理返回的 Markdown 内容，去除标题、URL 行和多余的标题重复
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(
            jina_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            # 清理内容
            lines = content.split('\n')
            cleaned_lines = []
            found_content_start = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # 跳过 Title: 开头的行
                if stripped.startswith('Title:'):
                    continue
                # 跳过 URL Source: 开头的行
                if stripped.startswith('URL Source:'):
                    continue
                # 找到 Markdown Content: 后跳过后续的 --- 和第一行（通常是重复标题）
                if 'Markdown Content:' in stripped:
                    found_content_start = True
                    continue
                if found_content_start and stripped == '---':
                    continue
                # 跳过第一行内容（通常是网页标题的重复）
                if found_content_start and len(cleaned_lines) == 0 and stripped:
                    # 检查是否是标题格式（包含 | 或只是简单文字）
                    if '|' not in stripped and len(stripped) < 100:
                        continue
                    cleaned_lines.append(line)
                    continue
                
                if stripped or line == '':
                    cleaned_lines.append(line)
            
            cleaned_content = '\n'.join(cleaned_lines).strip()
            
            if verbose:
                print(f"  [Jina] Successfully fetched: {url[:50]}...")
            return cleaned_content
    except Exception as e:
        if verbose:
            print(f"  [Jina] Error fetching {url[:50]}...: {e}")
        return None

def extract_summary(content, max_length=300):
    """从完整内容中提取摘要"""
    if not content:
        return ""
    # 清理内容
    content = content.strip()
    
    # 去除第一行（通常是网页标题的重复）
    lines = content.split('\n')
    if lines and (lines[0].strip().endswith('| OpenAI') or 
                  lines[0].strip().endswith('| Google') or
                  lines[0].strip().endswith('| Microsoft') or
                  '|' in lines[0].strip()[:30]):
        lines = lines[1:]
        content = '\n'.join(lines).strip()
    
    # 取前 max_length 个字符
    summary = content[:max_length]
    # 确保不截断单词
    last_period = summary.rfind('.')
    if last_period > max_length * 0.7:
        summary = summary[:last_period + 1]
    return summary + "..."

def fetch_news(count=5, use_jina=False, verbose=False, sources=None):
    """获取AI/科技新闻"""
    if sources is None:
        sources = RSS_SOURCES
    
    news_items = []
    
    for source in sources:
        # 支持旧格式 (name, url) 和新格式 (name, url, type)
        if len(source) == 2:
            name, url = source
            source_type = 'rss'
        else:
            name, url, source_type = source
        
        if verbose:
            print(f"Fetching from {name} ({source_type})...")
        
        try:
            if source_type == 'web':
                # 网页类型来源（如 Anthropic 新闻/工程博客）
                web_items = fetch_anthropic_list(name, verbose)
                for item in web_items[:3]:
                    link = item.get('link', '')
                    
                    # 如果启用 jina，获取完整内容
                    full_content = None
                    summary = f"点击查看: {item.get('title', '')}"
                    
                    if use_jina and link:
                        full_content = fetch_jina_content(link, verbose)
                        if full_content:
                            summary = extract_summary(full_content)
                    
                    if item.get('title') and len(item['title']) > 5:
                        news_items.append({
                            'title': item['title'],
                            'summary': summary,
                            'link': link,
                            'source': item.get('source', name),
                            'full_content': full_content if use_jina else None
                        })
            else:
                # RSS 类型来源
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    title = html.unescape(entry.get('title', ''))
                    summary = clean_html(html.unescape(entry.get('summary', '')))
                    summary = summary[:250].strip()
                    link = entry.get('link', '')
                    
                    # 如果启用 jina，获取完整内容
                    full_content = None
                    if use_jina and link:
                        full_content = fetch_jina_content(link, verbose)
                        if full_content:
                            summary = extract_summary(full_content)
                    
                    if title and len(title) > 5:
                        news_items.append({
                            'title': title,
                            'summary': summary,
                            'link': link,
                            'source': name,
                            'full_content': full_content if use_jina else None
                        })
        except Exception as e:
            if verbose:
                print(f"Error fetching {name}: {e}")
    
    # 去重
    seen = set()
    unique_news = []
    for news in news_items:
        if news['title'] not in seen:
            seen.add(news['title'])
            unique_news.append(news)
            if len(unique_news) >= count:
                break
    
    return unique_news

def translate_to_chinese(news):
    """简单翻译（实际项目中可用API）"""
    translations = {
        "Introducing OpenAI for India": "OpenAI在印度推出AI服务",
        "GPT-5.2 derives a new result in theoretical physics": "GPT-5.2推导出理论物理学新成果",
        "Introducing Lockdown Mode and Elevated Risk labels in ChatGPT": "ChatGPT推出锁定模式和风险等级标签",
        "Scaling social science research": "OpenAI推出GABRIEL开源工具扩展社会科学研究",
        "Beyond rate limits: scaling access to Codex and Sora": "OpenAI构建实时访问系统扩展Codex和Sora",
    }
    
    for item in news:
        for eng, chi in translations.items():
            if eng.lower() in item['title'].lower():
                item['title'] = chi
                break
    return news

def format_markdown(news_items):
    """将新闻格式化为 Markdown 格式"""
    md_output = []
    md_output.append("# 今日AI/科技新闻\n")
    md_output.append(f"*采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    md_output.append("---\n")
    
    for i, item in enumerate(news_items, 1):
        md_output.append(f"## {i}. {item['title']}\n")
        md_output.append(f"**来源**: {item['source']}\n")
        md_output.append(f"**链接**: {item['link']}\n")
        md_output.append(f"\n{item['summary']}\n")
        
        # 如果有完整内容，添加折叠展示
        if item.get('full_content'):
            md_output.append(f"\n<details>\n<summary>查看完整内容</summary>\n\n")
            md_output.append(item['full_content'][:2000])  # 限制长度
            if len(item.get('full_content', '')) > 2000:
                md_output.append("\n... (内容过长已截断)")
            md_output.append("\n</details>\n")
        
        md_output.append("---\n")
    
    return "".join(md_output)

def format_json(news_items):
    """将新闻格式化为 JSON 格式"""
    return json.dumps(news_items, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description='AI/Tech RSS News Fetcher with Jina Reader')
    parser.add_argument('--count', '-c', type=int, default=5, help='Number of news to fetch (default: 5)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--jina', '-j', action='store_true', help='Use jina.ai Reader to get full content')
    parser.add_argument('--format', '-f', choices=['text', 'markdown', 'json'], default='text', help='Output format')
    parser.add_argument('--sources', '-s', nargs='+', help='Filter by source names (e.g., OpenAI NVIDIA)')
    
    args = parser.parse_args()
    
    # 根据来源过滤
    sources = RSS_SOURCES
    if args.sources:
        # 支持过滤带有type的新格式，支持部分匹配（如 "Anthropic" 可匹配 "Anthropic News"）
        sources = []
        for s in RSS_SOURCES:
            if len(s) == 2:
                name, url = s
            else:
                name, url, _ = s
            # 支持部分匹配
            for arg in args.sources:
                if arg.lower() in name.lower() or name.lower() in arg.lower():
                    sources.append(s)
                    break
        if not sources:
            print(f"Error: No matching sources found. Available: {[s[0] for s in RSS_SOURCES]}")
            sys.exit(1)
    
    if args.verbose:
        print(f"Fetching {args.count} news items...")
        print(f"Using jina.ai Reader: {args.jina}")
        print(f"Sources: {[s[0] for s in sources]}")
        print("-" * 50)
    
    news = fetch_news(args.count, use_jina=args.jina, verbose=args.verbose, sources=sources)
    news = translate_to_chinese(news)
    
    if args.format == 'markdown':
        print(format_markdown(news))
    elif args.format == 'json':
        print(format_json(news))
    else:
        print("=" * 70)
        print("今日Tech/AI RSS新闻")
        print("=" * 70)
        
        for item in news:
            print(f"\n【{item['title']}】")
            print(f"来源: {item['source']}")
            print(f"链接: {item['link']}")
            print(f"摘要: {item['summary']}")
            print("-" * 70)

if __name__ == "__main__":
    main()
