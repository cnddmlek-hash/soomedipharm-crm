#!/bin/sh
# 수메디팜 미니 CRM — 배포 스크립트
#
# 현재 배포 위치: cnddmlek-hash/soomedipharm 저장소의 gh-pages 브랜치 → crm/ 폴더
#   결과 주소: https://cnddmlek-hash.github.io/soomedipharm/crm/
#
# 전용 저장소 soomedipharm-crm 이 생기면 아래처럼 실행하세요.
#   TARGET=repo ./deploy.sh
#   → https://cnddmlek-hash.github.io/soomedipharm-crm/
set -e
cd "$(dirname "$0")"
SRC="$(pwd)"
TARGET="${TARGET:-subpath}"

say() { printf '%s\n' "$*"; }

if [ "$TARGET" = "repo" ]; then
  REPO_URL="https://github.com/cnddmlek-hash/soomedipharm-crm.git"
  BRANCH="main"
  SUBDIR=""
else
  REPO_URL="https://github.com/cnddmlek-hash/soomedipharm.git"
  BRANCH="gh-pages"
  SUBDIR="crm"
fi

WORK="${WORKDIR:-$SRC/../.deploy-soomedipharm-crm}"
rm -rf "$WORK"
say "→ $REPO_URL ($BRANCH) 에서 배포 브랜치를 받아옵니다"
git clone -q --depth 1 -b "$BRANCH" "$REPO_URL" "$WORK"

DEST="$WORK/$SUBDIR"
[ -n "$SUBDIR" ] && mkdir -p "$DEST"

tar -cf - index.html manifest.json sw.js \
  icon-192.png icon-512.png icon-maskable-512.png apple-touch-icon.png favicon-32.png \
  .nojekyll README.md tools 2>/dev/null | ( cd "$DEST" && tar -xf - )

cd "$WORK"
git add -A
if git diff --cached --quiet; then
  say "변경 없음 — 배포할 것이 없습니다."
  exit 0
fi
git -c user.name="최충의" -c user.email="cnddmlek@gmail.com" \
  commit -q -m "수메디팜 미니 CRM 배포 $(date '+%Y-%m-%d %H:%M')"
git push -q origin "$BRANCH"
say "배포 완료 (GitHub Pages 반영까지 30초~2분)"
if [ "$TARGET" = "repo" ]; then
  say "  https://cnddmlek-hash.github.io/soomedipharm-crm/"
else
  say "  https://cnddmlek-hash.github.io/soomedipharm/crm/"
fi
