import base64
import os,re
import requests
import xmltodict
import json
from jsonpath_ng import parse
from flask import current_app


# sql组装
def sqlHandle(sql, result, sqlParamConfig):
    sqlParam = {}
    for key, value in sqlParamConfig.items():
        key_parts = value.split('.')
        current_data = result
        for part in key_parts[:-1]:
            current_data = current_data.get(part, {})
        sqlParam[key] = current_data[key_parts[-1]]

    # 使用格式化字符串替换参数
    return sql.format(**sqlParam)

def convert_to_base64(file_name):
    """
    将传入的文件返回对应base64
    :param file_path:
    :return:
    """
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_name)

    # 检查文件是否存在
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    # 读取CSV文件并转换为Base64字符串
    with open(file_path, 'rb') as file:
        csv_bytes = file.read()
        base64_str = base64.b64encode(csv_bytes).decode('utf-8')

    return base64_str

def get_settlement_destroySign(settle_no):
    url = 'https://rhine3it.i.wxblockchain.com/asset/paygate/fund/QueryPayResult'

    body = {"settleNumber": f"{settle_no}","settleDate": "2018-05-30", "signStr": "2018-05", "financeFlag": True}
    response = requests.post(url, json=body, headers={'Content-Type': 'application/json'})
    destroySign = response.json().get('destroySign')
    return destroySign

def get_os_environ(variable_name):
    """get value of environment variable.

    Args:
        variable_name(str): variable name

    Returns:
        value of environment variable.

    Raises:
        exceptions.EnvNotFound: If environment variable not found.

    """
    try:
        return os.environ[variable_name]
    except KeyError:
        raise RuntimeError(f"variable_name not found: {variable_name}")



def xml_to_json_str(xml_data):
    json_data = xml_data

    try:
        # 将XML数据转换为Python字典
        xml_data = xml_data.replace('\n', '').replace('\t', '').strip()
        data_dict = xmltodict.parse(xml_data)
        # 将Python字典转换为JSON
        json_data = json.dumps(data_dict, ensure_ascii=False)
    except Exception:
        pass

    return json_data

def json_to_xml_str(json_data):
    xml_data = json_data
    try:
        # 将JSON字符串转换为XML
        xml_data = xmltodict.unparse(json.loads(json_data), pretty=True)
    except Exception:
        pass
    return xml_data

def is_json(json_string):
    try:
        json.loads(json_string)
    except Exception:
        return False
    return True


def get_data_by_json_path(data, json_path):
    try:
        json_path_expr = parse(json_path)
        # 使用 JSON Path 查找数据
        result = [match.value for match in json_path_expr.find(data)][0]
        return result
    except Exception as e:
        return json_path


def split_conditions(input_string):
    # 使用正则表达式进行分割
    conditions = re.split(r'&&|\|\|', input_string)

    # 去除空格
    conditions = [condition.strip() for condition in conditions]

    return conditions, '||' not in input_string


# upload/utils.py
if __name__ == '__main__':
    condition = "$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF000||$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF002&&$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF003||$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF004"
    list1, b = split_conditions(condition)

    print("List b:", b)
    print("List 1:", list1)












