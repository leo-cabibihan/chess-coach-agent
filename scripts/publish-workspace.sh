#!/usr/bin/env bash
# Push this monorepo to github.com/leo-cabibihan/workspace
set -euo pipefail

OWNER="${GITHUB_OWNER:-leo-cabibihan}"
REPO="${GITHUB_REPO:-workspace}"
REMOTE="${REMOTE:-workspace}"
BRANCH="${BRANCH:-main}"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
  git remote add "$REMOTE" "https://github.com/${OWNER}/${REPO}.git"
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if ! gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1; then
    echo "Creating ${OWNER}/${REPO} on GitHub..."
    gh repo create "${OWNER}/${REPO}" --private \
      --description "Personal monorepo: apps, games, infra" \
      --source=. --remote="$REMOTE" --push || {
      echo ""
      echo "Could not create repo via gh (token may lack repo create permission)."
      echo "Create an empty repo manually: https://github.com/new?name=${REPO}"
      echo "Then re-run: bash scripts/publish-workspace.sh"
      exit 1
    }
    exit 0
  fi
fi

CURRENT="$(git branch --show-current)"
echo "Pushing ${CURRENT} → ${REMOTE}/${BRANCH}"
git push -u "$REMOTE" "${CURRENT}:${BRANCH}"
