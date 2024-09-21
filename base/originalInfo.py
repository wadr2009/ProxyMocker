from dataclasses import dataclass
import simplejson as json


@dataclass
class OriginalResponse:
    status: int = None
    body: str = None
    headers: dict = None
    encodedBody: bool = None

@dataclass
class OriginalRequest:
    path: str
    method: str
    destination: str = None
    scheme: str  = None
    query: str  = None
    formData:dict  = None
    body: str  = None
    requestType: str = None
    headers: dict = None

class OriginalInfo:
    def __init__(self, data: dict):
        self.response: OriginalResponse = OriginalResponse(**(data.get('response')))
        self.request: OriginalRequest = OriginalRequest(**(data.get('request')))

    def to_dict(self):
        return {
            'response': self.response.__dict__,
            'request': self.request.__dict__
        }

class OriginalInfoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, OriginalResponse) or isinstance(obj, OriginalRequest):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)

# 自定义 JSONEncoder 类
class OriginalInfoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, OriginalInfo):
            return {
                'response': obj.response.__dict__,
                'request': obj.request.__dict__
            }
        return json.JSONEncoder.default(self, obj)