import copy

import simplejson as json
from flask import Flask, request, jsonify, Response
from base.originalInfo import OriginalResponse, OriginalRequest, OriginalInfo
from biz.mockServer import MockServer
from tools.logHandler import SingletonLogger

logging = SingletonLogger().logger
app = Flask(__name__)


@app.route('/mock', methods=['POST'])
def mock():
    # 获取请求内容
    originalData = request.json
    # headers = request.headers
    try:
        logging.info(f"Received request: {json.dumps(originalData, ensure_ascii=False)}")
        data = copy.deepcopy(originalData)
        originalResponse = OriginalResponse(**(data.get('response')))
        originalrequest = OriginalRequest(**(data.get('request')))
        originalInfo = OriginalInfo(originalResponse, originalrequest)

        mockServer = MockServer(originalInfo.request.path)
        mockServer.mockMock(originalInfo)
        result = originalInfo.__dict__
    except Exception as e:
        result = originalData
        logging.error(f"mock处理过程中出现异常, {e}", exc_info=True)

    logging.debug(f"return data: {result}")
    return result


# 保存mock配置
@app.route('/save_config', methods=['POST'])
def saveConfig():
    if request.method == 'POST':
        data = request.get_json()  # 获取传入的 JSON 数据
        with open('./config/config.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)  # 设置 ensure_ascii=False 以保留非 ASCII 字符

        response_data = {'code': 200, 'msg': 'Config saved successfully'}
        return jsonify(response_data)


# 获取mock配置
@app.route('/get_config', methods=['GET'])
def getConfig():
    try:
        with open('config/config.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        return jsonify(data)
    except FileNotFoundError:
        return Response({'code': 404, 'msg': 'Config file not found'})


def generateLastNLines(file_path, n):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines[-n:]:
            yield line
        yield ""  # 当文件读取完毕时停止生成内容


@app.route('/streamMockLog', methods=['GET'])
def stream_mock_log():
    file_path = 'logs/server.log'
    n = int(request.args.get('lines', 10))  # 默认返回最后10行日志
    return Response(generateLastNLines(file_path, n), mimetype='text/plain')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8800)  # 指定端口为 8800

