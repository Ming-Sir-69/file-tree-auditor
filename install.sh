#!/usr/bin/env bash
# ==========================================
# File Tree Auditor — 一键安装脚本
# ==========================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================="
echo " File Tree Auditor 安装"
echo "=============================="

# 1. 复制主脚本
CLAUDE_SCRIPTS="$HOME/.claude/scripts"
mkdir -p "$CLAUDE_SCRIPTS"
cp "$SCRIPT_DIR/scripts/file-tree-auditor.py" "$CLAUDE_SCRIPTS/file-tree-auditor.py"
chmod +x "$CLAUDE_SCRIPTS/file-tree-auditor.py"
echo "[✓] 脚本 → $CLAUDE_SCRIPTS/file-tree-auditor.py"

# 2. 复制 Skill 定义
SKILL_DIR="$HOME/.claude/skills/file-tree-auditor"
mkdir -p "$SKILL_DIR"
if [ -f "$SCRIPT_DIR/SKILL.md" ]; then
    cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
    echo "[✓] Skill → $SKILL_DIR/SKILL.md"
else
    echo "[ ] SKILL.md 未找到，Claude Code Skill 需手动注册"
fi

echo ""
echo "=============================="
echo " 安装完成！"
echo "=============================="
echo ""
echo "在任何项目目录下运行:"
echo "  python3 ~/.claude/scripts/file-tree-auditor.py --target /path/to/project"
echo ""
echo "首次运行加 --no-diff 跳过差异对比（建立基线）:"
echo "  python3 ~/.claude/scripts/file-tree-auditor.py --target /path/to/project --no-diff"
