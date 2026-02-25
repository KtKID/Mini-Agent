# Mini Agent 进化路线图

## 目标

将 Mini Agent 进化为功能更丰富、能力更强大的 Agent 框架，目标是超越 OpenClaw。

---

## 现状对比

| 能力维度 | Mini Agent | OpenClaw | 差距 |
|----------|------------|----------|------|
| 文件操作 | ✅ 读/写/编辑 | ✅ | 持平 |
| 命令执行 | ✅ BashTool | ✅ | 持平 |
| Git 操作 | ❌ 无 | ✅ | **需添加** |
| 多模态 | ⚠️ 预留接口 | ✅ 图片/截图 | **需增强** |
| 网页能力 | ⚠️ MCP 依赖 | ✅ 内置搜索/抓取 | **需内置** |
| 任务管理 | ❌ 无 | ✅ TodoWrite | **需添加** |
| 代码智能 | ⚠️ 基础 | ✅ 分析/重构 | **需增强** |
| 安全沙箱 | ❌ 无 | ✅ 权限控制 | **需添加** |
| 记忆系统 | ⚠️ 简单笔记 | ✅ 持久化 | **需增强** |
| IDE 集成 | ⚠️ ACP/Zed | ✅ 多编辑器 | **需扩展** |

---

## 进化路线图

### Phase 1: 基础能力补全（短期）

```
1. Git 工具集
   ├── GitStatusTool    - 状态查看
   ├── GitDiffTool      - 差异比较
   ├── GitLogTool       - 提交历史
   ├── GitBranchTool    - 分支管理
   ├── GitCommitTool    - 提交代码
   └── GitPushTool      - 推送远程

2. 任务管理
   ├── TodoWriteTool    - 创建/更新任务
   ├── TodoListTool     - 列出任务
   └── 与 Agent 循环集成

3. 代码智能工具
   ├── GlobTool         - 文件模式搜索
   ├── GrepTool         - 内容搜索
   ├── CodeSearchTool   - 语义代码搜索
   └── SymbolFinderTool - 符号跳转
```

### Phase 2: 多模态与网络能力（中期）

```
1. 多模态支持
   ├── ImageReadTool    - 读取/分析图片
   ├── ScreenshotTool   - 截图能力
   └── DiagramTool      - 图表生成

2. 网络能力内置
   ├── WebSearchTool    - 网页搜索
   ├── WebFetchTool     - 网页抓取
   └── APIRequestTool   - HTTP 请求

3. 浏览器操作
   ├── BrowserLaunchTool  - 启动浏览器
   ├── BrowserNavigateTool - 页面导航
   └── BrowserInteractTool - 页面交互
```

### Phase 3: 安全与智能增强（中期）

```
1. 安全沙箱
   ├── 权限系统
   │   ├── 文件系统沙箱
   │   ├── 命令白名单
   │   └── 敏感操作确认
   └── 风险评估

2. 增强记忆系统
   ├── 向量数据库集成
   ├── 长期记忆存储
   ├── 知识图谱
   └── 语义检索

3. 项目理解
   ├── CodebaseAnalysisTool - 代码库分析
   ├── DependencyGraphTool  - 依赖图谱
   ├── ArchitectureDocTool  - 架构文档生成
   └── ImpactAnalysisTool   - 影响分析
```

### Phase 4: 高级特性（长期）

```
1. 多 Agent 协作
   ├── Agent 协调器
   ├── 任务分解与分配
   └── 结果合并

2. 自我进化能力
   ├── 工具自生成
   ├── Prompt 优化
   └── 能力学习

3. 插件生态
   ├── 插件市场
   ├── 热加载机制
   └── 版本管理
```

---

## 差异化优势方向

要超越 OpenClaw，建议在以下方向建立独特优势：

| 方向 | 描述 |
|------|------|
| **🎯 项目级智能** | 深度理解整个代码库，而非单文件操作 |
| **🔄 持续学习** | 从用户行为中学习，优化操作模式 |
| **🤝 协作增强** | 支持多 Agent 协作处理复杂任务 |
| **🧠 深度推理** | 利用 M2.5 的 interleaved thinking 做复杂推理 |
| **🔌 生态开放** | 更灵活的插件/技能系统 |

---

## 当前进度

- [ ] Phase 1: 基础能力补全
  - [ ] Git 工具集
  - [ ] 任务管理
  - [ ] 代码智能工具
- [ ] Phase 2: 多模态与网络能力
- [ ] Phase 3: 安全与智能增强
- [ ] Phase 4: 高级特性
