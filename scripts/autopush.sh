#!/usr/bin/env sh
set -eu

cd "$(git rev-parse --show-toplevel)"

# Only act if there are changes
if git status --porcelain | grep -q .; then
  git add -A
  git commit -m "chore: auto update $(date -u +'%Y-%m-%dT%H:%M:%SZ')" || true
  branch="$(git rev-parse --abbrev-ref HEAD)"
  git push origin "$branch" || true
fi
