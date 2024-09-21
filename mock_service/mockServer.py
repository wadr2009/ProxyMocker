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
    def __init__(self, apiName):
        super().__init__(apiName)

    def mockMock(self, originalInfo: OriginalInfo):
        responseStatus = originalInfo.response.status

        # 判断mock返回还是mock请求
        is_mock = False
        if responseStatus != None and responseStatus == 200:
            request_body_bak = originalInfo.request.body
            self.__xml_api_mock_response(originalInfo, request_body_bak)

            json_body = originalInfo.request.body
            self.__mock_response_before(json_body)

            is_mock = self.mockResponse(originalInfo)
            originalInfo.response.headers['is_mock'] = ['True']

            self.__xml_api_mock_response(originalInfo, request_body_bak, mock_before=False)

        elif responseStatus == 0:
            is_mock = self.redirectionMock(originalInfo.request)
            originalInfo.request.headers['is_mock'] = ['True']
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
            r = get_data_by_json_path(json_data, json_path)
            return r == check_value

        try:
            otherReturnBody = self.mockConfig.otherReturnBody
            if otherReturnBody == None:
                return

            json_data = json.loads(request_body)
            for k, v in otherReturnBody.items():
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

    def __xml_api_mock_response(self, originalInfo: OriginalInfo, request_body: str, mock_before=True):
        if not self.mockConfig.isXmlApi:
            return

        if mock_before:
            json_body = xml_to_json_str(request_body)
            originalInfo.request.body = json_body
            return
        else:
            rep = requests.post('http://localhost:5001/xml', data=originalInfo.response.body)
            header = rep.headers
            content_type = header.get('Content-Type')
            content_lenght = header.get('Content-Length')
            originalInfo.response.headers['Content-Type'] = [f'{content_type}']
            originalInfo.response.headers['Content-Length'] = [f'{content_lenght}']
            originalInfo.request.body = request_body

    # 响应mock
    def mockResponse(self, originalInfo: OriginalInfo):
        """
        mockResponse
        :param originalInfo:
        :return: 返回mock后的body
        """

        # 判断是否需要mock
        if not self.checkMock(originalInfo.request, originalInfo.response):
            return False


        # 判断是否需要超时
        configTimeout = self.mockConfig.timeout
        if configTimeout > 0:
            logging.info(f" {originalInfo.request.path} ##超时## {configTimeout} s\n")
            time.sleep(configTimeout)

        # 判断是否需要直接修改返回
        originalRequestBody = self.getRequestBody(originalInfo.request)
        originalResponseBody = originalInfo.response.body
        processor = JsonRuleProcessor(originalRequestBody, originalResponseBody, self.mockConfig.variablesInitSql)
        configBody = self.mockConfig.returnBody

        try:
            if configBody != None and len(configBody) > 0:
                logging.info(f"mockResponse处理后的返回: {configBody}")
                result = processor.process_json(configBody)
                originalInfo.response.body = result
                return True

        except Exception as e:
            logging.error(f"直接mock返回异常, exception: {e}", exc_info=True)
            return False

        # 判断是否需要根据json路径修改返回
        byResReplace = self.mockConfig.byResReplace
        byDbReplace = self.mockConfig.byDbReplace
        if byResReplace == None or byDbReplace == None:
            return False

        result = json.loads(originalInfo.response.body)

        try:
            # 处理replaceSql的数据
            # 组装sql
            sql = sqlHandle(byDbReplace.sql, result, byDbReplace.sqlParam)
            # TODO:后续换成DBControls
            dbResult = queryMysql(byDbReplace.dbname, sql)
            if dbResult != None and len(dbResult) > 0:
                # 只取第一条
                dbResult = dbResult[0]
                for key, value in byDbReplace.rule.items():
                    key_parts = key.split('.')
                    current_data = result
                    for part in key_parts[:-1]:
                        current_data = current_data.get(part, {})
                    current_data[key_parts[-1]] = dbResult[value]


            # 处理replace的数据
            for key, value in byResReplace.rule.items():
                key_parts = key.split('.')
                current_data = result
                for part in key_parts[:-1]:
                    current_data = current_data.get(part, {})
                current_data[key_parts[-1]] = value

            # 处理特殊规则
            result = processor.process_json(result)
            result = json.dumps(result, ensure_ascii=False)

            logging.info(f"mockResponse处理后的返回: {result}")
            if result != None and len(result) > 0:
                originalInfo.response.body = result
            return True
        except Exception as e:
            logging.error(f"mockMock 替换接口响应时出现异常, {e}", exc_info=True)
            return False

    # 请求转发到其他服务
    # TODO: 目前只支持转发, 不支持修改请求参数和请求类型
    def redirectionMock(self, originalRequest: OriginalRequest):
        try:
            # 判断是否需要mock
            if not self.checkMock(originalRequest):
                logging.info("无需处理")
                return False

            # 判断是否需要转发
            if self.mockConfig.mockRequest is None or self.mockConfig.mockRequest.redirection == None or len(
                    self.mockConfig.mockRequest.redirection) <= 0:
                logging.info("redirectionUrl 为空")
                return False

            # method, url = redirectionUrl.split(' ')
            # 使用 urlparse() 函数解析 URL
            redirectionUrl = self.mockConfig.mockRequest.redirection
            parsed_url = urlparse(redirectionUrl)

            # 提取域名和路径
            originalRequest.destination = parsed_url.netloc
            originalRequest.path = parsed_url.path
            originalRequest.scheme = parsed_url.scheme

            # 是否需要转为GET请求
            if self.mockConfig.mockRequest.toGet:
                body = json.loads(originalRequest.body)
                url_params = urllib.parse.urlencode(body)
                originalRequest.query = url_params
                originalRequest.method = 'GET'

            logging.info(f"redirection= {redirectionUrl}")
            return True

        except Exception as e:
            logging.info(f"redirectionMock 处理异常, {e}", exc_info=True)
            return False

    def checkMock(self,
                  originalRequest: OriginalRequest,
                  originalResponse: OriginalResponse | None = None) -> bool:

        check = self.mockConfig.mockCheck
        if check is None or check == "":
            return False

        originalRequestBody = originalRequest.body
        originalRequestQuery = originalRequest.query

        originalResponseBody = ''
        if originalResponse is not None and originalResponse.body is not None:
            originalResponseBody = originalResponse.body

        return check in originalRequestBody or check in originalRequestQuery or check in originalResponseBody


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
