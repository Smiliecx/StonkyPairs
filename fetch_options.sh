#!/usr/bin/env bash
# Fetch today's put chains for the given tickers via GitHub Actions, into ./options
#   ./fetch_options.sh NVDA SMH SOXX QQQ
#   ./fetch_options.sh $(python puts.py NVDA --plan)
# Pushes request.txt to the 'requests' branch (based on main), waits for the
# "Download option chains" workflow to publish the 'options' branch, then clones it.
set -euo pipefail
REPO="${REPO:-https://github.com/Smiliecx/StonkyPairs.git}"
[ $# -gt 0 ] || { echo "usage: $0 TICKER [TICKER...]"; exit 1; }
before=$(git ls-remote "$REPO" refs/heads/options | cut -f1)
tmp=$(mktemp -d)
git clone -q --depth 1 --branch main "$REPO" "$tmp/r"
(
  cd "$tmp/r"
  git checkout -q -b requests
  printf "%s\n" "$@" > request.txt
  git add -f request.txt
  git -c user.name="stonkypairs" -c user.email="noreply@github.com" commit -q -m "Request put chains: $*"
  git push -q --force origin requests 2>/dev/null
)
rm -rf "$tmp"
echo "Requested: $*  (waiting for GitHub, usually 1-3 minutes)"
for i in $(seq 1 60); do
  sleep 10
  now=$(git ls-remote "$REPO" refs/heads/options | cut -f1)
  if [ -n "$now" ] && [ "$now" != "$before" ]; then
    rm -rf options
    git clone -q --depth 1 --branch options "$REPO" options
    cat options/meta.json
    exit 0
  fi
done
echo "Timed out after 10 minutes; check the repo's Actions tab." >&2
exit 1
