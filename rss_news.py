#!/usr/bin/env python3
"""
RSS News 包装脚本
此文件已移至 mini_agent/skills/rss_news/rss_news.py
此处保留用于向后兼容
"""

import sys
import os

# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
skill_script = os.path.join(script_dir, 'mini_agent', 'skills', 'rss_news', 'rss_news.py')

# 检查 skill 版本是否存在
if os.path.exists(skill_script):
    # 执行 skill 版本的脚本，传递所有参数
    os.execv(sys.executable, [sys.executable, skill_script] + sys.argv[1:])
else:
    print("Error: Skill version not found at:", skill_script)
    print("Please ensure the rss_news skill is properly installed.")
    sys.exit(1)
