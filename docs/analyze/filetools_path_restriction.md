# FileTools 路径限制方案评价

## 方案概述

在 ReadTool、WriteTool、EditTool 的 `execute()` 中添加路径验证，确保所有文件操作只能在 `workspace_dir` 范围内进行。

## 核心实现

```python
# 推荐方案：使用 relative_to 做路径校验
file_path = file_path.resolve()
try:
    file_path.relative_to(self.workspace_dir.resolve())
except ValueError:
    return ToolResult(success=False, error="Path outside workspace")
```

**不要用 `startswith`**：

```python
# ❌ 错误方案
workspace = "/home/user/app"
path      = "/home/user/app-secret/data.txt"
str(path).startswith(str(workspace))  # True！误放行

# ✅ 正确方案
Path("/home/user/app-secret/data.txt").relative_to(Path("/home/user/app"))
# 抛出 ValueError，正确拦截
```

---

## 优点

| 项 | 说明 |
|---|------|
| 极简 | 核心逻辑只有几行，几乎不可能写错 |
| 零依赖 | 不需要 Docker、firejail 等外部工具 |
| 跨平台 | `Path.resolve()` 在 Windows/Linux/Mac 都能工作 |
| 职责清晰 | FileTools 管文件访问，不越界去管 Bash |
| 向后兼容 | workspace 内的所有操作不受影响 |

---

## 已知问题及应对

### 1. startswith 字符串匹配陷阱

`/home/user/app-secret` 会被 `/home/user/app` 的 `startswith` 误判为合法路径。

**解决**：使用 `relative_to()` 替代 `startswith()`。

### 2. 符号链接逃逸

```
workspace/
└── link -> /etc/   (symlink)
```

`resolve()` 会解析符号链接，`workspace/link/passwd` 解析为 `/etc/passwd`，然后被 `relative_to` 拦截。**已覆盖**。

### 3. TOCTOU 竞态条件

```
1. 验证路径 workspace/data.txt  → 通过
2. 攻击者把 data.txt 替换为 symlink → /etc/passwd
3. 实际读取时读的是 /etc/passwd
```

Agent 场景中由 Agent 自身控制文件操作，不存在外部攻击者同时操作文件系统。**风险极低，可接受。**

### 4. Windows 路径大小写

`C:\Users` 和 `c:\users` 是同一路径，但字符串比较不等。`Path.resolve()` 在 Windows 上会标准化大小写，`relative_to()` 方案不受影响。

### 5. 三个工具重复代码

ReadTool、WriteTool、EditTool 需要加相同的验证逻辑。

**解决**：提取到基类

```python
class FileToolBase(Tool):
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = Path(workspace_dir).absolute()

    def _validate_path(self, path: str) -> tuple[Path, str | None]:
        """返回 (resolved_path, error_message_or_None)"""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.workspace_dir / file_path
        file_path = file_path.resolve()
        try:
            file_path.relative_to(self.workspace_dir.resolve())
        except ValueError:
            return file_path, "Path outside workspace"
        return file_path, None
```

三个工具继承 `FileToolBase`，一处修改，处处生效。

---

## 测试用例设计

在 `tests/test_tools.py` 中补充以下测试：

| 测试名 | 验证点 |
|--------|--------|
| `test_read_blocks_dotdot` | `../outside/secret.txt` 被拒绝 |
| `test_read_blocks_absolute_outside` | 绝对路径指向 workspace 外被拒绝 |
| `test_read_allows_inside` | workspace 内的相对和绝对路径正常工作 |
| `test_write_blocks_dotdot` | `../` 写入被拒绝，且文件未创建 |
| `test_write_blocks_absolute_outside` | 绝对路径写入外部被拒绝 |
| `test_write_allows_inside` | workspace 内写入正常 |
| `test_edit_blocks_dotdot` | `../` 编辑被拒绝，且原文件未被修改 |
| `test_edit_blocks_absolute_outside` | 绝对路径编辑外部被拒绝 |
| `test_edit_allows_inside` | workspace 内编辑正常 |
| `test_symlink_escape_blocked` | 符号链接指向外部被拒绝 |
| `test_similar_prefix_blocked` | `/workspace-other/file` 不被 `/workspace` 误放行 |

---

## 总结评价

| 维度 | 评分 | 说明 |
|------|------|------|
| **安全性** | ⭐⭐⭐⭐ | 用 `relative_to` 后基本无漏洞 |
| **简洁性** | ⭐⭐⭐⭐⭐ | 核心逻辑极少，复杂度极低 |
| **可维护性** | ⭐⭐⭐ → ⭐⭐⭐⭐⭐ | 提取基类后消除重复 |
| **可靠性** | ⭐⭐⭐⭐ | 依赖标准库，不存在正则绕过问题 |
| **实用性** | ⭐⭐⭐⭐⭐ | 零依赖，立即可用 |

### 关键改进两点

1. **用 `relative_to()` 替代 `startswith()`** — 消除路径前缀误判
2. **提取 `FileToolBase` 基类** — 消除重复，集中维护
