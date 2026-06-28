#!/bin/bash
# ============================================
#  会员运营智能体 — 一键启动脚本
# ============================================
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="/Users/fangchao/WorkBuddy/2026-06-28-18-15-31/.venv"
PYTHON="$VENV_DIR/bin/python3"

echo "========================================"
echo "  🤖 会员运营智能体 — 启动中..."
echo "========================================"

# 1. 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    echo "❌ 虚拟环境未找到: $VENV_DIR"
    echo "   请先安装依赖：pip install -r requirements.txt"
    exit 1
fi

# 2. 检查 .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  .env 未配置，从 .env.example 复制..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "   请编辑 .env 填入 DEEPSEEK_API_KEY"
fi

# 3. 检查 Mock 数据
if [ ! -f "$PROJECT_DIR/src/data/mock_members.json" ]; then
    echo "📦 生成 Mock 数据..."
    cd "$PROJECT_DIR"
    PYTHONPATH="$PROJECT_DIR/src" $PYTHON src/data/generator.py
fi

# 4. 清理旧进程
echo "🧹 清理旧进程..."
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

# 5. 启动后端
echo "🚀 启动后端 (FastAPI + LangGraph)..."
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR/src" $PYTHON src/backend/main.py &
BACKEND_PID=$!
sleep 2

# 验证后端
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   ✅ 后端已启动: http://localhost:8000"
else
    echo "   ❌ 后端启动失败"
    exit 1
fi

# 6. 启动前端
echo "🎨 启动前端 (Streamlit)..."
PYTHONPATH="$PROJECT_DIR/src" $PYTHON -m streamlit run src/frontend/app.py --server.port 8501 &
FRONTEND_PID=$!
sleep 3

echo ""
echo "========================================"
echo "  ✅ 启动完成！"
echo "  前端: http://localhost:8501"
echo "  后端: http://localhost:8000"
echo "  API:  http://localhost:8000/api/health"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 7. 等待用户终止
trap "echo ''; echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已停止'; exit 0" SIGINT SIGTERM
wait
