#!/usr/bin/env bash
# push_to_github.sh
# ─────────────────────────────────────────────────────────────────────────────
# Creates GitHub repos in GITHUB_ORG and pushes the local git history.
#
# Prerequisites:
#   export GITHUB_ORG=oscorpAI
#   export GITHUB_PAT=ghp_...
#   bash setup_git_history.sh   (run this first)
#
# Usage: bash push_to_github.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

: "${GITHUB_ORG:?Set GITHUB_ORG env var}"
: "${GITHUB_PAT:?Set GITHUB_PAT env var}"

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
REPOS=("payment-service" "order-service" "notification-service")

create_and_push() {
    local repo="$1"
    echo ""
    echo "=== $repo ==="

    # Create repo via GitHub API (ignore error if already exists)
    HTTP_STATUS=$(curl -s -o /tmp/gh_create_out.json -w "%{http_code}" \
        -X POST \
        -H "Authorization: Bearer $GITHUB_PAT" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/orgs/$GITHUB_ORG/repos" \
        -d "{\"name\":\"$repo\",\"private\":true,\"auto_init\":false}")

    if [ "$HTTP_STATUS" == "201" ]; then
        echo "  Created: https://github.com/$GITHUB_ORG/$repo"
    elif [ "$HTTP_STATUS" == "422" ]; then
        echo "  Repo already exists — skipping create"
    else
        echo "  Warning: unexpected status $HTTP_STATUS"
        cat /tmp/gh_create_out.json
    fi

    # Push
    cd "$DEMO_DIR/$repo"
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://$GITHUB_PAT@github.com/$GITHUB_ORG/$repo.git"
    git push -u origin main --force
    echo "  Pushed: https://github.com/$GITHUB_ORG/$repo"
}

for repo in "${REPOS[@]}"; do
    create_and_push "$repo"
done

echo ""
echo "========================================================"
echo "All repos pushed to github.com/$GITHUB_ORG"
echo ""
echo "Now run: python demo_seed_data.py --org $GITHUB_ORG"
echo "========================================================"
