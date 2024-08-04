from dataclasses import dataclass, field, fields

import simplejson as json


@dataclass
class ByDbReplace:
    check: str
    dbname: str
    rule: dict
    sql: str
    sqlParam: dict


@dataclass
class ByResReplace:
    check: str
    rule: dict


@dataclass
class MockRequest:
    redirection: str = None
    toGet: bool = False


@dataclass
class ApiMockConfig:
    mockCheck: str = None
    mockApiName: str = None
    returnBody: str = None
    mockRequest: MockRequest = field(default=None)
    byDbReplace: ByDbReplace = field(default=None)
    byResReplace: ByResReplace = field(default=None)
    timeout: int = 0

    # 当 ApiMockConfig 对象被实例化时，__post_init__ 方法会检查 byDbReplace 和 byResReplace 是否是字典，如果是，则将其转换为相应的类对象。
    def __post_init__(self):
        if isinstance(self.byDbReplace, dict):
            self.byDbReplace = self._init_dataclass(ByDbReplace, self.byDbReplace)
        if isinstance(self.byResReplace, dict):
            self.byResReplace = self._init_dataclass(ByResReplace, self.byResReplace)
        if isinstance(self.mockRequest, dict):
            self.mockRequest = self._init_dataclass(MockRequest, self.mockRequest)

    # 只保留数据类中定义的字段
    @staticmethod
    def _init_dataclass(cls, data):
        cls_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in cls_fields}
        return cls(**filtered_data)


# JSON 字符串
json_str = '''
{
    "mockCheck": "invoice",
    "mockApiName": "发票查验转发后处理返回",
    "byResReplace": {
        "rule": {
            "data.amountTax": null,
            "data.totalAmount": null
        },
        "check": "invoiceNumber"
    },
    "byDbReplace": {
        "check": "invoiceNumber",
        "dbname": "rhine3_asset",
        "rule": {
            "data.amountTax": -1,
            "data.purchaserName": 0,
            "data.salesName": 1,
            "data.totalAmount": 2
        },
        "sql": "select buyer_name as '买家', supplier_name as '卖家', amount as '金额', pretax_amount as '税前金额' from invoice i where i.invoice_number = '{invoiceNumber}';",
        "sqlParam": {
            "invoiceNumber": "data.invoiceNumber"
        }
    }
}
'''

if __name__ == '__main__':
    data = json.loads(json_str)
    replace_data = ApiMockConfig(**data)
    print(replace_data.byDbReplace.sql)
