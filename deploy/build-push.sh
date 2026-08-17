#!/usr/bin/env bash
# 构建 app 镜像并推送到 GitHub Container Registry（用户确认的镜像流）
# 前置：gh auth login（GitHub CLI 已登录，有 ghcr.io 推送权限）
# 用法：GITHUB_USER=你的用户名 ./build-push.sh [tag]
set -euo pipefail

USER="${GITHUB_USER:?请设置 GITHUB_USER=你的 GitHub 用户名}"
TAG="${1:-latest}"
IMAGE="ghcr.io/${USER}/wechat-workbench:${TAG}"

cd "$(dirname "$0")/.."

echo "== 登录 GHCR =="
echo "$GH_PAT" | docker login ghcr.io -u "${USER}" --password-stdin || {
  echo "提示：若没有 GH_PAT，可先运行 gh auth login，再执行 gh auth token 获取。"
  exit 1
}

echo "== 构建 =="
docker build -t "${IMAGE}" -f app/Dockerfile .

echo "== 推送 =="
docker push "${IMAGE}"
echo "✅ 已推送: ${IMAGE}"
