#!/bin/bash
# dev-runner-v2.sh — Parallel execution with pre-built briefs
# Called by OpenClaw after it prepares .openclaw/tasks/*.md briefs
#
# Usage: bash .openclaw/dev-runner-v2.sh [max_parallel]
# Default max_parallel=4

set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="building-life-os"
QUEUE=".openclaw/dev-queue.json"
TASKS_DIR=".openclaw/tasks"
MAX_PARALLEL="${1:-4}"
RESULTS_FILE=".openclaw/run-results.json"

echo "=== DEV-RUNNER V2 ==="
echo "Branch: $BRANCH"
echo "Max parallel: $MAX_PARALLEL"
echo ""

# Ensure on correct branch
git checkout "$BRANCH" 2>/dev/null

# Verify tests before starting
echo "--- Pre-flight test check ---"
if ! npm test 2>&1 | tail -5 | grep -q "fail 0"; then
  echo "BLOCKED: tests already failing before start"
  exit 1
fi
echo "Tests green. Starting."
echo ""

# Find all prepared task briefs
BRIEF_FILES=$(ls "$TASKS_DIR"/*.md 2>/dev/null | sort)
if [ -z "$BRIEF_FILES" ]; then
  echo "NO BRIEFS FOUND in $TASKS_DIR/. OpenClaw must prepare briefs first."
  exit 1
fi

TOTAL=$(echo "$BRIEF_FILES" | wc -l)
echo "Found $TOTAL task briefs."
echo ""

# Track results
DONE=0
FAILED=0
SKIPPED=0
declare -A PIDS
declare -A WORKTREES
declare -A TASK_IDS

# Process tasks in waves of MAX_PARALLEL
WAVE=0
REMAINING_BRIEFS="$BRIEF_FILES"

while [ -n "$REMAINING_BRIEFS" ]; do
  WAVE=$((WAVE + 1))
  echo "=== WAVE $WAVE ==="

  # Take up to MAX_PARALLEL briefs
  WAVE_BRIEFS=$(echo "$REMAINING_BRIEFS" | head -n "$MAX_PARALLEL")
  REMAINING_BRIEFS=$(echo "$REMAINING_BRIEFS" | tail -n +$((MAX_PARALLEL + 1)))

  # Launch each task in a worktree
  for BRIEF in $WAVE_BRIEFS; do
    TASK_NAME=$(basename "$BRIEF" .md)
    WORKTREE_DIR="/tmp/sb-worktree-$TASK_NAME"
    WORKTREE_BRANCH="dev-runner/$TASK_NAME"

    echo "  Launching: $TASK_NAME"

    # Create worktree
    git worktree add -b "$WORKTREE_BRANCH" "$WORKTREE_DIR" "$BRANCH" 2>/dev/null || {
      # Branch might already exist
      git branch -D "$WORKTREE_BRANCH" 2>/dev/null
      git worktree add -b "$WORKTREE_BRANCH" "$WORKTREE_DIR" "$BRANCH" 2>/dev/null
    }

    # Copy brief to worktree
    mkdir -p "$WORKTREE_DIR/.openclaw/tasks"
    cp "$BRIEF" "$WORKTREE_DIR/.openclaw/tasks/"

    # Launch Claude Code in background
    (
      cd "$WORKTREE_DIR"
      claude --permission-mode bypassPermissions --print \
        "Read the file .openclaw/tasks/$TASK_NAME.md — it contains EVERYTHING you need: what to implement, which files to modify, patterns to follow, and test commands. Implement exactly what it says. Run the tests specified. If tests pass, commit with the message specified in the brief. Do NOT push. Stay in scope." \
        2>&1 > "/tmp/sb-log-$TASK_NAME.txt"
      echo $? > "/tmp/sb-exit-$TASK_NAME.txt"
    ) &

    PIDS[$TASK_NAME]=$!
    WORKTREES[$TASK_NAME]="$WORKTREE_DIR"
    echo "    PID=${PIDS[$TASK_NAME]} worktree=$WORKTREE_DIR"
  done

  echo ""
  echo "  Waiting for wave $WAVE to complete..."

  # Wait for all tasks in this wave
  for TASK_NAME in "${!PIDS[@]}"; do
    wait "${PIDS[$TASK_NAME]}" 2>/dev/null || true
    EXIT_CODE=$(cat "/tmp/sb-exit-$TASK_NAME.txt" 2>/dev/null || echo "1")
    WORKTREE_DIR="${WORKTREES[$TASK_NAME]}"

    # Check if commit was created
    COMMIT_HASH=$(cd "$WORKTREE_DIR" && git log -1 --format=%h 2>/dev/null)
    MAIN_HEAD=$(git log -1 --format=%h)

    if [ "$COMMIT_HASH" != "$MAIN_HEAD" ] && [ "$EXIT_CODE" = "0" ]; then
      # New commit exists — merge into main branch
      echo "  ✓ $TASK_NAME: OK (commit $COMMIT_HASH)"

      # Cherry-pick the commit(s) from worktree branch into main
      git cherry-pick "$COMMIT_HASH" 2>/dev/null && {
        DONE=$((DONE + 1))
      } || {
        git cherry-pick --abort 2>/dev/null
        echo "  ✗ $TASK_NAME: merge conflict"
        FAILED=$((FAILED + 1))
      }
    else
      echo "  ✗ $TASK_NAME: FAILED (exit=$EXIT_CODE)"
      tail -5 "/tmp/sb-log-$TASK_NAME.txt" 2>/dev/null
      FAILED=$((FAILED + 1))
    fi

    # Cleanup worktree
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null
    git branch -D "dev-runner/$TASK_NAME" 2>/dev/null
    rm -f "/tmp/sb-exit-$TASK_NAME.txt" "/tmp/sb-log-$TASK_NAME.txt"
  done

  # Clear tracking for next wave
  unset PIDS
  unset WORKTREES
  declare -A PIDS
  declare -A WORKTREES

  echo ""
done

# Final test
echo "=== FINAL VERIFICATION ==="
npm test 2>&1 | tail -5

echo ""
echo "=== RESULTS ==="
echo "Total: $TOTAL | Done: $DONE | Failed: $FAILED"
echo "Commits:"
git log --oneline -$((DONE + 2))
