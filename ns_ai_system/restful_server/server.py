# coding=utf-8
import pytz
from flask import Flask
from flask_pymongo import PyMongo

from read_config import config

from restful_server.func import CustomJSONEncoder
from my_log import Loggers
import logging

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder # 自定义json序列化，可以将Mongo的ObjectId序列化
app.logger.setLevel(logging.DEBUG)
Loggers.init_app('restful', app.logger)
app.config["MONGO_URI"] = f"mongodb://{config.get('mongoDB','host')}:{config.get('mongoDB','port')}/ai_system"
mongo = PyMongo(app, tz_aware=True, tzinfo=pytz.timezone('Asia/Shanghai'), )
from data_management.api.rpc_proxy import rpc_server
from restful_server import error_handlers
from restful_server.policy import policy_service
from restful_server.label import label_service


@app.route("/")
def index():
    return "ok", 200


app.register_blueprint(policy_service, url_prefix="/policy/")
app.register_blueprint(label_service, url_prefix="/label")
