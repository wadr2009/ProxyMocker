import time
import urllib
from urllib.parse import urlparse

import requests
import simplejson as json

from base.mockbase import MockBase
from base.originalInfo import OriginalRequest, OriginalInfo, OriginalResponse
from mock_service.json_rule_processor import JsonRuleProcessor
from mock_service.queryMysql import queryMysql
from tools.logHandler import SingletonLogger
from tools.tools import sqlHandle, xml_to_json_str, get_data_by_json_path, split_conditions

logging = SingletonLogger().logger


class MockServer(MockBase):
    def __init__(self, original_info: OriginalInfo):
        api_name = original_info.request.path
        super().__init__(api_name)

        self.response: OriginalResponse = original_info.response
        self.response_status: int = self.response.status
        self.request: OriginalRequest = original_info.request

    def mock_mock(self):
        # 判断mock返回还是mock请求
        is_mock: bool = False
        if self.response_status is not None and self.response_status == 200:
            request_body_bak: str = self.request.body
            self.__xml_api_mock_response(request_body_bak)

            json_body = self.request.body
            self.__mock_response_before(json_body)

            is_mock = self.mock_response()
            self.response.headers['is_mock'] = ['True']

            self.__xml_api_mock_response(request_body_bak, mock_before=False)

        elif self.response_status == 0:
            is_mock = self.redirection_mock()
            self.request.headers['is_mock'] = ['True']
        else:
            logging.warn(f"请求返回码非200")

        return is_mock

    def __mock_response_before(self, request_body):
        """
        支持多个默认返回
        :param request_body:
        :return:
        """

        def check(json_data, json_path, check_value):
            """
            检查给定的 JSON 数据中指定路径的值是否等于预期值。

            :param json_data: 要检查的 JSON 数据（字典格式）。
            :param json_path: JSON 路径字符串，用于提取值。
            :param check_value: 预期的值。
            :return: 如果路径的值等于预期值，则返回 True，否则返回 False。
            """

            extracted_value = get_data_by_json_path(json_data, json_path)
            return extracted_value == check_value

        try:
            other_return_body = self.mockConfig.otherReturnBody
            if other_return_body:
                return

            json_data = json.loads(request_body)
            for k, v in other_return_body.items():
                # flag = '||' not in input_string
                ks, flag = split_conditions(k)
                bools = [True]
                for key in ks:
                    json_path = str(key).split('=')[0]
                    check_value = str(key).split('=')[1]
                    bools.append(check(json_data, json_path, check_value))

                if flag and False not in bools:
                    self.mockConfig.returnBody = v
                    logging.info(f"使用{k} = {check} 的返回配置")
                    return

                if flag == False and True in bools:
                    self.mockConfig.returnBody = v
                    logging.info(f"使用{k} = {check} 的返回配置")
                    return


        except Exception as e:
            logging.error(f"__mock_response_after, 选择返回配置异常, {e}", exc_info=True)

    def __xml_api_mock_response(self, request_body: str, mock_before=True):
        if not self.mockConfig.isXmlApi:
            return

        if mock_before:
            json_body = xml_to_json_str(request_body)
            self.request.body = json_body
            return
        else:
            rep = requests.post('http://localhost:5001/xml', data=self.response.body)
            header = rep.headers
            content_type = header.get('Content-Type')
            content_lenght = header.get('Content-Length')
            self.response.headers['Content-Type'] = [f'{content_type}']
            self.response.headers['Content-Length'] = [f'{content_lenght}']
            self.request.body = request_body

    # 响应mock
    def mock_response(self) -> bool:
        """
        mockResponse
        """

        # 判断是否需要mock
        if not self.check_mock():
            return False

        try:
            self._initialize_processing()
            result = json.loads(self.response.body)

            self.process_replace_sql(result)
            self.process_by_res_replace(result)

            # 处理特殊规则
            result = self._process_special_rules(result)

            result = json.dumps(result, ensure_ascii=False)

            logging.info(f"mockResponse处理后的返回: {result}")
            if result:
                self.response.body = result

            return True

        except Exception as e:
            logging.error(f"mockMock 替换接口响应时出现异常, {e}", exc_info=True)
            return False

    # 请求转发到其他服务
    # TODO: 目前只支持转发, 不支持修改请求参数和请求类型
    def redirection_mock(self) -> bool:
        # 判断是否需要mock
        if not self.check_mock():
            logging.info("无需处理")
            return False

        # 判断是否需要转发
        mock_request = self.mockConfig.mockRequest
        if not mock_request or not mock_request.redirection:
            logging.info("redirectionUrl 为空")
            return False

        try:
            # method, url = redirectionUrl.split(' ')
            # 使用 urlparse() 函数解析 URL
            redirection = mock_request.redirection
            parsed_url = urlparse(redirection)

            # 提取域名和路径
            self.request.destination = parsed_url.netloc
            self.request.path = parsed_url.path
            self.request.scheme = parsed_url.scheme

            # 是否需要转为GET请求
            if self.mockConfig.mockRequest.toGet:
                body = json.loads(self.request.body)
                url_params = urllib.parse.urlencode(body)
                self.request.query = url_params
                self.request.method = 'GET'

            logging.info(f"redirection= {redirection}")
            return True

        except Exception as e:
            logging.info(f"redirectionMock 处理异常, {e}", exc_info=True)
            return False

    def check_mock(self) -> bool:
        check = self.mockConfig.mockCheck
        if not check:
            return False

        response_body = self.response.body or ''
        request_body = self.request.body or ''
        request_query = self.request.query or ''

        return any(check in body for body in [request_body, request_query, response_body])

    def process_default_body(self):
        config_body = self.mockConfig.returnBody
        if config_body:
            logging.info(f"mockResponse处理后的返回: {config_body}")
            self.response.body = config_body

    def process_replace_sql(self, result):
        """
        处理replaceSql的数据
        :param result: 需要处理的结果数据
        :return: 处理后的结果数据
        """
        by_db_replace = self.mockConfig.byDbReplace

        if not by_db_replace:
            return

        # 组装sql
        sql = sqlHandle(by_db_replace.sql, result, by_db_replace.sqlParam)
        # TODO:后续换成DBControls
        db_result = queryMysql(by_db_replace.dbname, sql)
        if db_result:
            # 只取第一条
            db_result = db_result[0]
            for key, value in by_db_replace.rule.items():
                key_parts = key.split('.')
                current_data = result
                for part in key_parts[:-1]:
                    current_data = current_data.get(part, {})
                current_data[key_parts[-1]] = db_result[value]

    def process_by_res_replace(self, result):
        by_res_replace = self.mockConfig.byResReplace

        if not by_res_replace:
            return

        # 处理replace的数据
        for key, value in by_res_replace.rule.items():
            key_parts = key.split('.')
            current_data = result
            for part in key_parts[:-1]:
                current_data = current_data.get(part, {})
            current_data[key_parts[-1]] = value

    def process_time_out(self):
        # 判断是否需要超时
        timeout = self.mockConfig.timeout
        if timeout > 0:
            logging.info(f" {self.request.path} ##超时## {timeout} s\n")
            time.sleep(timeout)

    def _initialize_processing(self):
        self.process_time_out()
        self.process_default_body()

    def _process_special_rules(self, result):
        processor = JsonRuleProcessor(self.request.body, self.response.body, self.mockConfig.variablesInitSql)
        return processor.process_json(result)


if __name__ == '__main__':
    import re

    condition = "$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF002&&$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF003||$.bocb2e.trans.trn-b2e0603-rq.b2e0603-rq.transcode=SPF004"

    # 使用正则表达式按照 && 和 || 运算符进行分割
    conditions = re.split(r'\s*(&&|\|\|)\s*', condition)

    # 处理分割后的条件
    for i in range(0, len(conditions), 2):
        if conditions[i + 1] == '&&':
            # 处理 && 运算符
            condition1 = conditions[i]
            condition2 = conditions[i + 2]
            # 执行相应操作
            print(f"Condition 1: {condition1} AND Condition 2: {condition2}")
        elif conditions[i + 1] == '||':
            # 处理 || 运算符
            condition1 = conditions[i]
            condition2 = conditions[i + 2]
            # 执行相应操作
            print(f"Condition 1: {condition1} OR Condition 2: {condition2}")
