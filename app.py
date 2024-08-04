from flask import Flask, request, Response, current_app
from mock_service.routes import mock_service_bp
from file_service.routes import upload_bp
import secrets, os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['SERVICE_LOG'] = os.path.join(os.path.dirname(__file__), 'logs/service.log')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

app.secret_key = secrets.token_hex(16)  # 用于闪现消息

app.register_blueprint(mock_service_bp, url_prefix='/mock')
app.register_blueprint(upload_bp, url_prefix='/upload')


@app.route('/streamMockLog')
def stream_mock_log():
    file_path = current_app.config['SERVICE_LOG']
    n = int(request.args.get('lines', 10))  # 默认返回最后10行日志
    return Response(generateLastNLines(file_path, n), mimetype='text/plain')

def generateLastNLines(file_path, n):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        g = '-' * 150 + '\n'
        for line in lines[-n:]:
            yield line
            yield g
        yield ""  # 当文件读取完毕时停止生成内容

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8800)  # 指定端口为 8800
