import json
import logging

from flask import Flask, request, jsonify, Response
from werkzeug.http import HTTP_STATUS_CODES


"""
挡板服务
"""

app = Flask(__name__)

# 固定的 JSON 响应
fixed_response = {"message": "Hello, this is a fixed JSON response!"}

app = Flask(__name__)

# 用于处理XML请求的路由
@app.route('/xml', methods=['POST'])
def xml_handler():
    # 获取POST请求中的XML数据
    xml_data = request.data
    response = Response(xml_data, mimetype='text/xml')
    response.headers['is_mock'] = 'True'

    return response

@app.route('/err/<int:code>', methods=['GET', 'POST'])
def error_response(code):
    if code not in HTTP_STATUS_CODES:
        msg = f"Invalid HTTP response code"
        code = 500
    else:
        msg = HTTP_STATUS_CODES.get(code)

    response = jsonify({"message": msg, "code": code})
    response.headers['is_mock'] = 'True'

    return response, code

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    # data = request.data.decode('utf-8')
    # try:
    #     json_data = json.loads(data)
    # except Exception as e:
    #     json_data = fixed_response

    json_data = fixed_response
    logging.info(f"{request.path} 来了来了, 拿走了{json_data}")
    # 返回固定的 JSON 响应

    response = jsonify(json_data)
    response.headers['is_mock'] = 'True'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
