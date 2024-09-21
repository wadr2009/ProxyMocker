import copy
import os
import simplejson as json
from flask import Blueprint
from flask import request, jsonify, Response

from base.originalInfo import OriginalResponse, OriginalRequest, OriginalInfo, OriginalInfoEncoder
from mock_service.mockServer import MockServer
from tools.logHandler import SingletonLogger

mock_service_bp = Blueprint('mock_service', __name__)
logging = SingletonLogger().logger

@mock_service_bp.route('/mock', methods=['POST'])
def mock():
    # 获取请求内容
    originalData = json.loads(request.data.decode('utf-8'))
    result = originalData
    # headers = request.headers
    try:
        logging.info(f"Received request: {json.dumps(originalData, ensure_ascii=False)}")
        data = copy.deepcopy(originalData)
        originalResponse = OriginalResponse(**(data.get('response')))
        originalrequest = OriginalRequest(**(data.get('request')))
        originalInfo = OriginalInfo(originalResponse, originalrequest)

        mockServer = MockServer(originalInfo.request.path)
        is_mock = mockServer.mockMock(originalInfo)
        if is_mock:
            result = originalInfo.to_dict()

    except Exception as e:
        logging.error(f"mock处理过程中出现异常, {e}", exc_info=True)

    logging.info(f"return data: {json.dumps(result, ensure_ascii=False)}")
    return jsonify(result)


# 保存mock配置
@mock_service_bp.route('/save_config', methods=['POST'])
def saveConfig():
    if request.method == 'POST':
        data = request.get_json()  # 获取传入的 JSON 数据
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json'))
        with open(config_path, 'w') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)  # 设置 ensure_ascii=False 以保留非 ASCII 字符

        response_data = {'code': 200, 'msg': 'Config saved successfully'}
        logging.info("保存配置成功")
        return jsonify(response_data)


# 获取mock配置
@mock_service_bp.route('/get_config', methods=['GET'])
def getConfig():
    try:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json'))
        with open(config_path, 'r') as file:
            data = json.load(file)
            logging.info("读取配置成功")

        return jsonify(data)
    except FileNotFoundError:
        return Response({'code': 404, 'msg': 'Config file not found'})

