#!/usr/bin/env bash
# ==========================================
# File Tree Auditor — 一键安装脚本
# ==========================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============================="
echo " File Tree Auditor 安装"
echo "=============================="

# 1. 创建 skill 目录
SKILL_DIR="$HOME/.claude/skills/file-tree-auditor"
SCRIPTS_DIR="$SKILL_DIR/scripts"
mkdir -p "$SCRIPTS_DIR"

# 2. 复制主脚本到 skill 内部
cp "$SCRIPT_DIR/scripts/file-tree-auditor.py" "$SCRIPTS_DIR/file-tree-auditor.py"
chmod +x "$SCRIPTS_DIR/file-tree-auditor.py"
echo "[✓] 脚本 → $SCRIPTS_DIR/file-tree-auditor.py"

# 3. 全局快捷方式（符号链接）
GLOBAL_SCRIPT="$HOME/.claude/scripts/file-tree-auditor.py"
mkdir -p "$HOME/.claude/scripts"
ln -sf "$SCRIPTS_DIR/file-tree-auditor.py" "$GLOBAL_SCRIPT"
echo "[✓] 快捷方式 → $GLOBAL_SCRIPT"

# 4. 复制 Skill 定义
if [ -f "$SCRIPT_DIR/SKILL.md" ]; then
    cp "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
    echo "[✓] Skill → $SKILL_DIR/SKILL.md"
else
    echo "[ ] SKILL.md 未找到，需手动复制"
fi

echo ""
echo "=============================="
echo " 安装完成！"
echo "=============================="
echo ""
echo "用法:"
echo "  python3 ~/.claude/scripts/file-tree-auditor.py --target /path/to/project"
echo "  # 或 python3 ~/.claude/skills/file-tree-auditor/scripts/file-tree-auditor.py ..."
