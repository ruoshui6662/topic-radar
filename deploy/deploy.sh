#!/usr/bin/env bash
# NAS 一键部署（把 compose + .env 推送到 NAS 并启动）
# 用法：NAS_USER=admin NAS_HOST=192.168.1.100 NAS_PATH=/volume1/docker/wechat-workbench ./deploy.sh
set -euo pipefail

NAS_USER="${NAS_USER:?请设置 NAS_USER=NAS 用户名}"
NAS_HOST="${NAS_HOST:?请设置 NAS_HOST=NAS IP（如 192.168.1.100）}"
NAS_PATH="${NAS_PATH:-/volume1/docker/wechat-workbench}"
cd "$(dirname "$0")/.."

echo "== 准备 NAS 目录 =="
ssh "${NAS_USER}@${NAS_HOST}" "mkdir -p '${NAS_PATH}/data/pgdata'"

echo "== 上传 compose 与 .env =="
scp docker-compose.yml "${NAS_USER}@${NAS_HOST}:${NAS_PATH}/"
scp .env "${NAS_USER}@${NAS_HOST}:${NAS_PATH}/"

echo "== 启动 =="
ssh "${NAS_USER}@${NAS_HOST}" "cd '${NAS_PATH}' && docker compose up -d && docker compose ps"

echo "✅ 部署完成。工作台: http://${NAS_HOST}:8000/health"
