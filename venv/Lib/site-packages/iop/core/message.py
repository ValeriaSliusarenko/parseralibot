import time


class Headers(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Message:
    def __init__(self, payload=None, msgid: str = None, **headers):
        self.payload = payload
        self.msgid = str(msgid or time.time())
        self.headers = Headers(**headers)

    def __str__(self) -> str:
        return f"[msgid={self.msgid}, payload={self.payload}, headers={self.headers}]"
