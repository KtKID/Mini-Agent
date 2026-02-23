# 定时抓取AI热点新闻任务说明

## 任务概述

- **任务名称**: 每日AI热点新闻自动抓取
- **执行频率**: 每天早上 9:00
- **执行脚本**: `/Volumes/machub_app/proj/Mini-Agent/rss_news.py`
- **输出方式**: 控制台输出（可重定向到日志文件）

---

## 技术方案

### 方案：使用 macOS crontab

```bash
# 编辑 crontab
crontab -e
```

### 添加以下定时任务规则

```bash
# 每天早上9点执行AI新闻抓取任务
0 9 * * * /usr/bin/python3 /Volumes/machub_app/proj/Mini-Agent/rss_news.py >> /Volumes/machub_app/proj/Mini-Agent/logs/ai_news_$(date +\%Y\%m\%d).log 2>&1
```

### crontab 时间格式说明

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日期 (1 - 31)
│ │ │ ┌───────────── 月份 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6) (周日=0)
│ │ │ │ │
0 9 * * * command
│ │ │ │ │
│ │ │ │ └── 每周所有天数
│ │ │ └──── 每月所有天数
│ └──────── 每天9点
└────────── 每小时的第0分钟
```

---

## 详细配置步骤

### 步骤 1：创建日志目录（如果不存在）

```bash
mkdir -p /Volumes/machub_app/proj/Mini-Agent/logs
```

### 步骤 2：编辑 crontab

```bash
crontab -e
```

### 步骤 3：按 `i` 进入插入模式，粘贴以下内容

```bash
# AI热点新闻每日抓取任务 - 每天早上9点执行
0 9 * * * cd /Volumes/machub_app/proj/Mini-Agent && /usr/bin/python3 rss_news.py >> logs/ai_news_$(date +\%Y\%m\%d).log 2>&1
```

### 步骤 4：按 `Esc` 键，输入 `:wq` 保存退出

---

## 验证配置

### 查看当前 crontab 任务列表

```bash
crontab -l
```

### 手动测试脚本

```bash
cd /Volumes/machub_app/proj/Mini-Agent
python3 rss_news.py
```

### 查看日志输出

```bash
# 查看今天的日志
tail -f /Volumes/machub_app/proj/Mini-Agent/logs/ai_news_$(date +%Y%m%d).log

# 查看所有日志
ls -la /Volumes/machub_app/proj/Mini-Agent/logs/
```

---

## 任务管理命令

| 操作 | 命令 |
|------|------|
| 查看任务 | `crontab -l` |
| 编辑任务 | `crontab -e` |
| 删除所有任务 | `crontab -r` |
| 查看 cron 日志 | `log show --predicate 'subsystem == "com.apple.cron"' --last 1d` |

---

## 注意事项

1. **路径问题**: 确保使用绝对路径，避免因工作目录导致脚本找不到文件
2. **Python环境**: 脚本依赖 `feedparser` 库，如未安装需先安装：
   ```bash
   pip install feedparser
   ```
3. **日志清理**: 建议定期清理旧日志文件，避免占用过多磁盘空间
4. **执行权限**: 确保 `rss_news.py` 有执行权限（如需）

---

## 扩展功能（可选）

### 如果需要邮件通知

```bash
0 9 * * * cd /Volumes/machub_app/proj/Mini-Agent && /usr/bin/python3 rss_news.py 2>&1 | mail -s "AI News Daily" your_email@example.com
```

### 如果需要同时推送到 Slack

可以在脚本中添加 Slack Webhook 调用，实现实时推送通知。

---

## 当前脚本信息

- **RSS 源**: OpenAI, MIT AI, Google AI, Microsoft AI, NVIDIA, TechCrunch AI
- **抓取数量**: 每次 5 条新闻
- **去重机制**: 基于标题去重
