#!/bin/bash
echo "开始启动hoverctl和python"

./hoverctl start --listen-on-host=0.0.0.0 --logs-output file --logs-file /app/logs/hoverfly.log 2>&1 &
nohup python3 /app/app.py > app_output.log &
nohup python3 /app/dangban.py > dangban_output.log &

sleep 2

#检查服务是否在 8800 端口上启动
echo "等待 Python 服务启动..."

## 检查服务是否在 8800 端口上启动, 依赖netcat-openbsd
#while ! nc -z localhost 8800; do
#  sleep 0.1 # 每 0.1 秒检查一次
#  echo "继续等待 Python 服务启动..."
#done

# 自定义等待机制，检查服务是否在 8800 端口上启动---更小的镜像
python3 /app/check_service.py

echo "Python 服务已启动"

./hoverctl mode modify
./hoverctl middleware --remote http://localhost:8800/mock/mock

echo "完成启动和设置"
#tail -f /dev/null
tail -f /app/logs/service.log
