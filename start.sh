#!/bin/bash
echo "开始启动hoverctl和python"

./hoverctl start --listen-on-host=0.0.0.0 --logs-output file --logs-file /app/logs/hoverfly.log 2>&1 &
nohup python3 /app/app.py > /dev/null 2>&1 &
# 自定义等待机制，检查服务是否在 8800 端口上启动
sleep 2
echo "等待 Python 服务启动..."
python3 /app/check_service.py

echo "Python 服务已启动"

./hoverctl mode modify
./hoverctl middleware --remote http://localhost:8800/mock

echo "完成启动和设置"
#tail -f /dev/null
tail -f /app/logs/server.log
