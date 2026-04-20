#!/bin/bash

# 项目路径
cd "$(dirname "$0")"

BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_status() {
    echo "=== 服务状态 ==="

    # 检查后端
    if lsof -i:$BACKEND_PORT > /dev/null 2>&1; then
        echo -e "后端 (port $BACKEND_PORT): ${GREEN}运行中${NC}"
    else
        echo -e "后端 (port $BACKEND_PORT): ${RED}未运行${NC}"
    fi

    # 检查前端
    if lsof -i:$FRONTEND_PORT > /dev/null 2>&1; then
        echo -e "前端 (port $FRONTEND_PORT): ${GREEN}运行中${NC}"
    else
        echo -e "前端 (port $FRONTEND_PORT): ${RED}未运行${NC}"
    fi
}

start() {
    echo "=== 启动服务 ==="

    # 启动后端
    if lsof -i:$BACKEND_PORT > /dev/null 2>&1; then
        echo -e "后端已在运行 (port $BACKEND_PORT)"
    else
        echo "启动后端..."
        cd $BACKEND_DIR && nohup python -m uvicorn main:app --reload --port $BACKEND_PORT > ../logs/backend.log 2>&1 &
        echo -e "后端已启动 (port $BACKEND_PORT)"
    fi

    # 启动前端
    if lsof -i:$FRONTEND_PORT > /dev/null 2>&1; then
        echo -e "前端已在运行 (port $FRONTEND_PORT)"
    else
        echo "启动前端..."
        cd $FRONTEND_DIR && nohup npm run dev > ../logs/frontend.log 2>&1 &
        echo -e "前端已启动 (port $FRONTEND_PORT)"
    fi

    # 等待服务启动
    sleep 3
    show_status

    echo ""
    echo "访问地址:"
    echo -e "  前端: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  后端API: ${GREEN}http://localhost:$BACKEND_PORT${NC}"
}

stop() {
    echo "=== 停止服务 ==="

    # 停止后端
    BACKEND_PID=$(lsof -t -i:$BACKEND_PORT 2>/dev/null)
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "后端已停止 (PID: $BACKEND_PID)"
    else
        echo "后端未运行"
    fi

    # 停止前端
    FRONTEND_PID=$(lsof -t -i:$FRONTEND_PORT 2>/dev/null)
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "前端已停止 (PID: $FRONTEND_PID)"
    else
        echo "前端未运行"
    fi
}

restart() {
    stop
    sleep 2
    start
}

# 创建日志目录
mkdir -p logs

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        show_status
        ;;
    logs)
        echo "=== 后端日志 (最后20行) ==="
        tail -20 logs/backend.log 2>/dev/null || echo "日志文件不存在"
        echo ""
        echo "=== 前端日志 (最后20行) ==="
        tail -20 logs/frontend.log 2>/dev/null || echo "日志文件不存在"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - 启动后端和前端服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看日志"
        exit 1
        ;;
esac

exit 0
