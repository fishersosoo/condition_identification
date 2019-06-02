# coding=utf-8
from bson import ObjectId
from flask.json import JSONEncoder
import pika

from restful_server.server import config


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return JSONEncoder.default(self, o)


