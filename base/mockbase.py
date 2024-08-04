import os

import simplejson as json
from base.configClass import ApiMockConfig

class MockBase():

    def __init__(self, apiName: str):
        self.mockConfig: ApiMockConfig = self.__getMockConfig(apiName)

    def __getMockConfig(self, apiName: str) -> ApiMockConfig:
        # 读取配置文件, 处理mock
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json'))
        with open(config_path, 'r') as file:
            data = json.load(file)

        mockConfigJson = data.get(apiName)
        if mockConfigJson is None:
            return ApiMockConfig()
        return ApiMockConfig(**mockConfigJson)


if __name__ == '__main__':
    m = MockBase('/mock/clover/invoice/check')
    print(m.mockConfig.mockApiName)