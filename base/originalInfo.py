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
    scheme: str = None
    query: str = None
    formData: dict = None
    body: str = None
    requestType: str = None
    headers: dict = None


class OriginalInfo:
    def __init__(self, response: OriginalResponse, request: OriginalRequest):
        self.response: OriginalResponse = response
        self.request: OriginalRequest = request


class OriginalInfoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, OriginalResponse) or isinstance(obj, OriginalRequest):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)
