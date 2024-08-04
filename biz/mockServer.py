import time
import urllib
from urllib.parse import urlparse

import simplejson as json

from base.mockbase import MockBase
from base.originalInfo import OriginalRequest, OriginalInfo, OriginalResponse
from biz.queryMysql import queryMysql
from tools.logHandler import SingletonLogger
from tools.tools import sqlHandle

logging = SingletonLogger().logger


class MockServer(MockBase):
    def __init__(self, apiName):
        super().__init__(apiName)

    def mockMock(self, originalInfo: OriginalInfo):
        responseStatus = originalInfo.response.status

        # 判断mock返回还是mock请求
        if responseStatus is not None and responseStatus == 200:
            self.mockResponse(originalInfo)
        elif responseStatus == 0:
            self.redirectionMock(originalInfo.request)
        else:
            logging.warn(f"请求返回码非200")

    # 响应mock
    def mockResponse(self, originalInfo: OriginalInfo):
        """
        mockResponse
        :param originalInfo:
        :return: 返回mock后的body
        """
        if self.mockConfig.mockCheck is None:
            return None

        # 判断是否需要mock
        originalRequestBody = originalInfo.request.body
        originalRequestQuery = originalInfo.request.query
        originalResponseBody = originalInfo.response.body

        configCheck = self.mockConfig.mockCheck
        if (configCheck not in originalRequestBody and configCheck not in originalRequestQuery
                and configCheck not in originalResponseBody):
            return

        # 判断是否需要超时
        configTimeout = self.mockConfig.timeout
        if configTimeout > 0:
            logging.info(f" {originalInfo.request.path} ##超时## {configTimeout} s\n")
            time.sleep(configTimeout)

        # 判断是否需要直接修改返回
        configBody = self.mockConfig.returnBody
        if configBody is not None and len(configBody) > 0:
            logging.info(f"mockResponse处理后的返回: {configBody}")
            originalInfo.response.body = configBody
            return

        # 判断是否需要根据json路径修改返回
        byResReplace = self.mockConfig.byResReplace
        byDbReplace = self.mockConfig.byDbReplace
        if byResReplace is None or byDbReplace is None:
            return

        result = json.loads(originalInfo.response.body)

        try:
            replaceSqlCheck = byDbReplace.check
            # 处理replaceSql的数据
            if (replaceSqlCheck in originalRequestBody or replaceSqlCheck in originalRequestQuery
                    or replaceSqlCheck in originalResponseBody):

                # 组装sql
                sql = sqlHandle(byDbReplace.sql, result, byDbReplace.sqlParam)
                dbResult = queryMysql(byDbReplace.dbname, sql)
                if dbResult is not None and len(dbResult) > 0:
                    # 只取第一条
                    dbResult = dbResult[0]
                    for key, value in byDbReplace.rule.items():
                        key_parts = key.split('.')
                        current_data = result
                        for part in key_parts[:-1]:
                            current_data = current_data.get(part, {})
                        current_data[key_parts[-1]] = dbResult[value]

            replaceCheck = byResReplace.check

            # 处理replace的数据
            if (replaceCheck in originalRequestBody or replaceCheck in originalRequestQuery
                    or replaceCheck in originalResponseBody):
                # 根据配置文件中的设置修改 JSON 数据
                for key, value in byResReplace.rule:
                    key_parts = key.split('.')
                    current_data = result
                    for part in key_parts[:-1]:
                        current_data = current_data.get(part, {})
                    current_data[key_parts[-1]] = value

            result = json.dumps(result, ensure_ascii=False)

            logging.info(f"mockResponse处理后的返回: {result}")
            if result is not None and len(result) > 0:
                originalInfo.response.body = result

        except Exception as e:
            logging.error(f"mockMock 替换接口响应时出现异常, {e}", exc_info=True)
            return

    # 请求转发到其他服务
    # TODO: 目前只支持转发, 不支持修改请求参数和请求类型
    def redirectionMock(self, originalRequest: OriginalRequest):
        try:
            # 判断是否需要mock
            if (self.mockConfig.mockCheck is None or
                    self.checkMock(self.mockConfig.mockCheck, originalRequest, OriginalResponse())):
                logging.info("无需处理")
                return

            # 判断是否需要转发
            redirectionUrl = self.mockConfig.mockRequest.redirection
            if redirectionUrl is None or len(redirectionUrl) <= 0:
                logging.info("redirectionUrl 为空")
                return

            # method, url = redirectionUrl.split(' ')
            # 使用 urlparse() 函数解析 URL
            parsed_url = urlparse(redirectionUrl)

            # 提取域名和路径
            originalRequest.destination = parsed_url.netloc
            originalRequest.path = parsed_url.path

            # 是否需要转为GET请求
            if self.mockConfig.mockRequest.toGet:
                body = json.loads(originalRequest.body)
                url_params = urllib.parse.urlencode(body)
                originalRequest.query = url_params
                originalRequest.method = 'GET'

            logging.info(f"redirection= {redirectionUrl}")

        except Exception as e:
            logging.info(f"redirectionMock 处理异常, {e}", exc_info=True)

    def checkMock(self, check: str, originalRequest: OriginalRequest, originalResponse: OriginalResponse):
        originalRequestBody = originalRequest.body
        originalRequestQuery = originalRequest.query
        originalResponseBody = originalResponse.body

        return (check not in originalRequestBody and check not in originalRequestQuery and
                check not in originalResponseBody)


if __name__ == '__main__':
    check = "dsd"
    originalRequest = OriginalRequest(method='GET', path='/')
    originalResponse = OriginalResponse()
    originalRequestBody = originalRequest.body
    originalRequestQuery = originalRequest.query
    originalResponseBody = originalResponse.body

    print(check not in originalRequestBody and check not in originalRequestQuery and check not in originalResponseBody)
