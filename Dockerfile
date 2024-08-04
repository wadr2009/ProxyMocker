
FROM python:3.9 as builder

WORKDIR /app
COPY ./requirements.txt /app/
# 替换为阿里云的 Debian 软件源
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list && \
    pip3 install --no-cache-dir -r requirements.txt

# 使用更小的基础镜像
FROM python:3.9-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app/
ENV TZ=Asia/Shanghai
# 替换为阿里云的 Debian 软件源
RUN apt-get install -y --no-install-recommends ca-certificates && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/* && chmod +x /app/start.sh

# 执行shell脚本, 启动Hoverfly和Python服务并完成设置
ENTRYPOINT ["/app/start.sh"]
CMD [""]

# 8500:Hoverfly代理端口
# 8888:Hoverfly前端页面端口
# 8800:python服务端口
EXPOSE 8500 8800
