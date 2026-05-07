# Codex Session Patcher

一个轻量级的本地 Python 工具，用于重写 Codex CLI 的会话和记忆文件，绕过上下文中的 AI 拒绝回复。

## 功能特性

- 🔍 **自动定位**: 自动查找 `~/.codex/sessions/` 下最新修改的会话文件
- 🧹 **会话清洗**: 清除 AI 拒绝回复并注入肯定的占位回复
- 🧠 **推理擦除**: 删除可能存在的 `Reasoning`/`Thought` 等拒绝逻辑字段
- 📝 **记忆清理**: 清理 `MEMORY.md` 中的拒绝记录
- 💾 **安全备份**: 修改前自动创建 `.bak` 备份文件
- ⚡ **零依赖**: 仅使用 Python 标准库，即插即用

## 快速开始

```bash
# 直接运行
python codex_patcher.py

# 查看帮助
python codex_patcher.py --help

# 执行后自动 resume
python codex_patcher.py --auto-resume
```

## 使用场景

当 Codex CLI 因上下文中包含 AI 拒绝回复而无法继续执行时：

```bash
# 1. 运行 patcher 清理会话
python codex_patcher.py

# 2. 继续 codex 会话
codex resume
```

## 配置

可通过命令行参数或配置文件自定义行为：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--auto-resume` | 执行完毕后自动调用 `codex resume` | `False` |
| `--no-backup` | 跳过备份步骤 | `False` |
| `--dry-run` | 仅预览修改，不实际写入 | `False` |
| `--session-dir` | 自定义会话目录 | `~/.codex/sessions/` |
| `--memory-file` | 自定义记忆文件路径 | `~/.codex/memories/MEMORY.md` |

## 项目结构

```
codex-session-patcher/
├── codex_patcher.py      # 主程序入口
├── docs/
│   └── DESIGN.md         # 详细设计文档
├── tests/
│   └── test_patcher.py   # 单元测试
├── scripts/
│   └── install.sh        # 安装脚本（可选）
├── README.md
└── pyproject.toml        # 项目配置
```

## 安全说明

- 本工具仅修改本地文件，不涉及网络请求
- 所有修改前会自动备份原始文件
- 建议在重要会话前手动备份 `~/.codex/` 目录

## 许可证

MIT License
