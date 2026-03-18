#!/bin/bash
# Usage: scripts/build.sh <command>
# Commands: zip-src, zip-layer, zip-common, diff, clean-src, clean-layer, clean-common
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMAND="${1:?Usage: build.sh <zip-src|zip-layer|zip-common|diff|clean-src|clean-layer|clean-common>}"

EXCLUDE_FIND=( -name "*.zip" -o -name "*.sha" -o -name "*.sha.tmp" -o
               -name "*.pyc" -o -name ".DS_Store" -o -name "Makefile" -o
               -path "*__pycache__*" )

# 디렉토리 내 모든 파일의 SHA256을 하나의 해시로 집계
dir_hash() {
  find "$1" -type f ! \( "${EXCLUDE_FIND[@]}" \) -print0 \
    | xargs -0 shasum -a 256 \
    | awk '{ print $1 }' \
    | shasum -a 256 \
    | awk '{ print $1 }'
}

zip_src() {
  local dirs
  dirs=$(find app/api -mindepth 2 -maxdepth 2 -type d -name "api_*" 2>/dev/null)

  for dir in $dirs; do
    echo ""
    echo "📦 Zipping: $dir"
    local build_dir="$PROJECT_ROOT/.build/$dir"
    local build_zip="$build_dir/build.zip"
    local build_sha="$build_dir/build.sha"
    local build_tmp="$build_dir/build.sha.tmp"
    mkdir -p "$build_dir"

    dir_hash "$dir" > "$build_tmp"

    if [ -f "$build_sha" ] && [ "$(cat "$build_sha")" = "$(cat "$build_tmp")" ]; then
      echo "⏸️  No changes. Skipping."
      rm -f "$build_tmp"
      continue
    fi

    mv "$build_tmp" "$build_sha"
    (cd "$dir" && zip -qr "$build_zip" . -x "*.zip" -x "*.sha" -x "*__pycache__*" -x "*.pyc" -x ".DS_Store")
    echo "✅ Zipped $dir → $build_zip"
  done
}

zip_layer() {
  echo ""
  echo "📦 Building layer from requirements.txt"
  local build_dir="$PROJECT_ROOT/.build/layer"
  local build_zip="$build_dir/layer.zip"
  local build_sha="$build_dir/layer.sha"
  local build_tmp="$build_dir/layer.sha.tmp"
  mkdir -p "$build_dir"

  shasum -a 256 requirements.txt | awk '{ print $1 }' > "$build_tmp"

  if [ -f "$build_sha" ] && [ "$(cat "$build_sha")" = "$(cat "$build_tmp")" ]; then
    echo "⏸️  No changes. Skipping."
    rm -f "$build_tmp"
    return
  fi

  mv "$build_tmp" "$build_sha"
  rm -rf "$build_dir/python"
  mkdir -p "$build_dir/python"
  pip install -r requirements.txt -t "$build_dir/python" -q
  (cd "$build_dir" && zip -qr layer.zip python/ && du -h layer.zip)
  rm -rf "$build_dir/python"
  echo "✅ Built layer → $build_zip"
}

zip_common() {
  echo ""
  echo "📦 Zipping: common"
  local build_dir="$PROJECT_ROOT/.build/common"
  local build_zip="$build_dir/layer.zip"
  local build_sha="$build_dir/layer.sha"
  local build_tmp="$build_dir/layer.sha.tmp"
  mkdir -p "$build_dir"

  dir_hash common > "$build_tmp"

  if [ -f "$build_sha" ] && [ "$(cat "$build_sha")" = "$(cat "$build_tmp")" ]; then
    echo "⏸️  No changes. Skipping."
    rm -f "$build_tmp"
    return
  fi

  mv "$build_tmp" "$build_sha"
  rm -rf "$build_dir/python"
  mkdir -p "$build_dir/python"
  cp -r common "$build_dir/python/"
  (cd "$build_dir" && zip -qr layer.zip python/ -x "*__pycache__*" -x "*.pyc" -x "*.zip" -x "*.sha")
  rm -rf "$build_dir/python"
  echo "✅ Zipped common → $build_zip"
}

diff_all() {
  local dirs
  dirs=$(find app/api -mindepth 2 -maxdepth 2 -type d -name "api_*" 2>/dev/null)

  for dir in $dirs; do
    local build_dir="$PROJECT_ROOT/.build/$dir"
    local build_sha="$build_dir/build.sha"
    mkdir -p "$build_dir"

    local new_hash
    new_hash="$(dir_hash "$dir")"

    if [ ! -f "$build_sha" ]; then
      echo "🆕 No SHA yet: $dir"
    elif [ "$(cat "$build_sha")" != "$new_hash" ]; then
      echo "🟡 Changed:   $dir"
    else
      echo "🟢 No change: $dir"
    fi
  done
}

case "$COMMAND" in
  zip-src)    zip_src    ;;
  zip-layer)  zip_layer  ;;
  zip-common) zip_common ;;
  diff)       diff_all   ;;
  clean-src)
    find "$PROJECT_ROOT/.build/app" -name "build.zip" -o -name "build.sha" -o -name "build.sha.tmp" 2>/dev/null | xargs rm -f
    echo "🧹 Cleaned src builds"
    ;;
  clean-layer)
    rm -rf "$PROJECT_ROOT/.build/layer"
    echo "🧹 Cleaned layer"
    ;;
  clean-common)
    rm -rf "$PROJECT_ROOT/.build/common"
    echo "🧹 Cleaned common"
    ;;
  *)
    echo "❌ Unknown command: $COMMAND"
    exit 1
    ;;
esac
