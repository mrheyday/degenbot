#!/usr/bin/env bash
set -euo pipefail

datetime_tz=$(date '+%Y-%m-%d %H:%M:%S %Z')
filename_ts=$(date '+%Y-%m-%d_%H-%M-%S')

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  repo_root=$(git rev-parse --show-toplevel)
  repo_name=$(basename "$repo_root")
  git_branch=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
  git_commit=$(git rev-parse HEAD)
else
  repo_root=""
  repo_name=""
  git_branch=""
  git_commit=""
fi

echo "Current Date/Time (TZ): $datetime_tz"
if [ -n "$git_commit" ]; then
  echo "Current Git Commit Hash: $git_commit"
fi
if [ -n "$git_branch" ]; then
  echo "Current Branch Name: $git_branch"
fi
if [ -n "$repo_name" ]; then
  echo "Repository Name: $repo_name"
fi
echo "Timestamp For Filename: $filename_ts"
