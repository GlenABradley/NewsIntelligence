#!/bin/bash

# News Intelligence Platform Startup Script

echo "🚀 Starting News Intelligence Platform..."

# Create data directories
mkdir -p data/reports
mkdir -p data/feeds
mkdir -p data/archives

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠️  MongoDB is not running. Please start MongoDB first."
    echo "   sudo systemctl start mongod"
    exit 1
fi

# Start backend
echo "📡 Starting backend server..."
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Check if backend is responding
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend is running on http://localhost:8001"
    echo "📚 API Documentation: http://localhost:8001/docs"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend (optional)
read -p "🌐 Start frontend dashboard? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🎨 Starting frontend dashboard..."
    cd ../frontend
    npm start &
    FRONTEND_PID=$!
    echo "✅ Frontend will be available at http://localhost:3000"
fi

echo ""
echo "🎉 News Intelligence Platform is running!"
echo ""
echo "📋 Available endpoints:"
echo "   • API Status: http://localhost:8001/api/news/"
echo "   • Health Check: http://localhost:8001/health"
echo "   • API Docs: http://localhost:8001/docs"
echo "   • Trigger Processing: curl -X POST http://localhost:8001/api/news/trigger-processing"
echo "   • Poll Feeds: curl -X POST http://localhost:8001/api/news/poll-feeds"
echo ""
echo "⏰ Automated processing scheduled for 12:00 PM Eastern daily"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $BACKEND_PID 2>/dev/null; kill $FRONTEND_PID 2>/dev/null; exit 0' INT
wait