#!/bin/bash

RAGFLOW_DIR=$(pwd) 
VENV_PATH="$RAGFLOW_DIR/.venv"
LAUNCH_SCRIPT="$RAGFLOW_DIR/docker/launch_backend_service.sh"

if [ ! -d "$VENV_PATH" ]; then
    echo "错误: 虚拟环境不存在: $VENV_PATH"
    exit 1
fi

if [ ! -f "$LAUNCH_SCRIPT" ]; then
    echo "错误: 启动脚本不存在: $LAUNCH_SCRIPT"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting RAGFlow..."

source "$VENV_PATH/bin/activate"
export PYTHONPATH="$RAGFLOW_DIR"
bash "$LAUNCH_SCRIPT"
