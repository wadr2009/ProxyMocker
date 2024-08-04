import base64
import json
import os
from typing import Callable

import requests

from mock_service.parser import parse_data
from tools.engine import DBControls
from tools.logHandler import SingletonLogger
from tools.tools import is_json

logging = SingletonLogger().logger


class JsonRuleProcessor:
    def __init__(self, request_body:str= None, response_body:str= None, variablesInitSqlDict:dict= None):
        self.request_cipher = None
        self.response_cipher = None
        self.data = {}
        if is_json(request_body):
            self.data['request'] = json.loads(request_body)
        else:
            self.request_cipher = request_body

        if is_json(response_body):
            self.data['response'] = json.loads(response_body)
        else:
            self.response_cipher = response_body

        mockFunctions = MockFunctions()
        self.variables_mapping = {'request_cipher': self.request_cipher, 'response_cipher': self.response_cipher}
        self.functions_mapping = self.__scan_class_methods(mockFunctions)
        self.variables_mapping.update(self.__init_variables(variablesInitSqlDict))


    def process_json(self, json_data):
        return parse_data(json_data, functions_mapping=self.functions_mapping,
                          variables_mapping=self.variables_mapping, json_data=self.data)

    def __scan_class_methods(self, class_obj) -> dict:
        functions_mapping = {}
        # 获取类的所有方法
        class_methods = [method for method in dir(class_obj) if callable(getattr(class_obj, method))]

        # 将公共方法添加到 functions_mapping 中
        for method_name in class_methods:
            method = getattr(class_obj, method_name)
            if method_name.startswith('_'):  # 跳过私有方法
                continue
            if isinstance(method, Callable):
                functions_mapping[method_name] = method

        return functions_mapping

    def __init_variables(self, sqlDict: dict):
        if sqlDict is None:
            return {}

        variables = {}
        try:
            sqlDict = parse_data(sqlDict, functions_mapping=self.functions_mapping,
                          variables_mapping=self.variables_mapping, json_data=self.data)
            for dbName, sqls in sqlDict.items():
                dBControls = DBControls(dbName)
                for sql in sqls:
                    result = dBControls.dBEngine.fetchone(sql)
                    variables.update(result)
        except Exception as e:
            logging.error(f'__init_variables exception {e}', exc_info=True)

        return variables


class MockFunctions:

    def method1(self, param1):
        return f"Method 1 executed with param: {param1}"

    def method2(self, param1, param2):
        return f"Method 2 executed with params: {param1}, {param2}"

    def method3(self, *args, **kwargs):
        return f"Method 3 executed with args: {args} and kwargs: {kwargs}"

    def convert_to_base64(self, file_name):
        """
        将对应文件返回base64
        :param file_path:
        :return:
        """
        # file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_name)
        file_path = os.path.join(os.path.join(os.path.dirname(__file__), '../uploads'), file_name)

        # 检查文件是否存在
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        # 读取CSV文件并转换为Base64字符串
        with open(file_path, 'rb') as file:
            csv_bytes = file.read()
            base64_str = base64.b64encode(csv_bytes).decode('utf-8')

        return base64_str

    def settleResult(self, cipher, env='it'):

        result = "{\"returnCode\":\"17000\",\"settleStatus\":\"fail\",\"destroySign\":\"@destroySign\",\"returnDesc\":\"settleResult默认请求失败\"}"
        try:
            cipher = base64.b64decode(cipher)
            separator = bytes([29])
            cipher = cipher.split(separator)[-1].decode('utf-8')
            # 解密
            rsp = requests.get(
                f"https://rhine3{env}.i.wxblockchain.com/asset/test/bank/decodeStr?encdata={cipher}").json()
            settleNumber = json.loads(rsp['data'])['body']['settleNumber']
            rsp = requests.post(f"https://rhine3{env}.i.wxblockchain.com/asset/paygate/fund/QueryPayResult",
                                   json={'settleNumber': settleNumber}).json()
            result = json.dumps(rsp, ensure_ascii=False).replace('"', '\"')
        except Exception as e:
            logging.error(f"destroySign 处理异常, exception: {e}")

        return result

    #x%y
    def remainder(self,x, y):
        return x % y


if __name__ == "__main__":
    json_str = '''
    {
        "name": "example",
        "file_field": "${convert_to_base64(3-2_20230703.csv)}",
        "tesrt":"${len('111')}",
        "tttt":"${method1($.request.txCodeCallbackList[0].txCode1)}",
        "nested": {
            "id": "$iidd1",
            "name": "$.request.aaa",
            "description": "${remainder($iidd, 3)}"
        }
    }
    '''

    json_data = json.loads(json_str)

    request_body = "{\"aaa\":\"278441\"}"
    sd = {"rhine3_asset":["select id as iidd from `settlement` where id = $.request.aaa"]}
    j = JsonRuleProcessor(request_body, '', sd)
    processed_json = j.process_json(json_data)

    print(json.dumps(processed_json, indent=4))
