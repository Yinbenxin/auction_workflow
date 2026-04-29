#!/usr/bin/env bash
# Ralph Loop Runner — auction_workflow
# 用法: bash scripts/ralph/run.sh
# 功能: 调用 Claude Code 代理，按 prompt.md 逐一验收所有用户故事

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"
USER_STORIES_DIR="$PROJECT_ROOT/docs/user-stories"

echo "=== Ralph Loop — auction_workflow 验收 ==="
echo "项目根目录: $PROJECT_ROOT"
echo "用户故事目录: $USER_STORIES_DIR"
echo ""

# 列出所有用户故事文件
echo "发现以下用户故事文件:"
for f in "$USER_STORIES_DIR"/*.json; do
  echo "  - $(basename $f)"
done
echo ""

# 运行 Claude Code 代理执行验收
echo "启动 Ralph 验收代理..."
claude --print "$(cat $PROMPT_FILE)" --cwd "$PROJECT_ROOT"
