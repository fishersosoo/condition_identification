# coding=utf-8
import pika
import requests
from requests.auth import HTTPBasicAuth

from restful_server.server import config

host = config.get('rabbit_mq', 'host')
port = int(config.get('rabbit_mq', 'port'))
user = config.get('rabbit_mq', 'user')
pwd = config.get('rabbit_mq', 'pwd')
url = config.get('rabbit_mq', 'url')


def list_queue():
    ret = requests.get(url + "queues", auth=HTTPBasicAuth(user, pwd))
    return ret.json()


def exist_queue(name):
    for q in list_queue():
        if q["name"] == name:
            return True
    return False


def create_queue(channel, name, check_exist=True):
    if check_exist:
        if exist_queue(name):
            return None
    result = channel.queue_declare(queue=name)
    new_queue = result.method.queue
    return new_queue


def exist_exchange(name):
    exchanges = requests.get(url + "exchanges", auth=HTTPBasicAuth(user, pwd)).json()
    for exchange in exchanges:
        if exchange["name"] == name:
            return True
    return False


def create_exchange(channel, name, exchange_type, check_exist=True):
    if check_exist:
        if exist_exchange(name):
            return None
    result = channel.exchange_declare(exchange=name, exchange_type=exchange_type)
    return name


def create_queue_bind(channel, queue_name, exchange_name, routing_key):
    new_queue = create_queue(channel, queue_name)
    print(new_queue)
    if new_queue is not None:
        new_exchange = create_exchange(channel, exchange_name, exchange_type="topic")
        channel.queue_bind(exchange=exchange_name, queue=new_queue, routing_key=routing_key)


def init_mq():
    print("init_mq")
    credentials = pika.credentials.PlainCredentials(user, pwd)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=host, port=port, virtual_host="/", credentials=credentials))
    channel = connection.channel()
    create_queue_bind(channel, "file_event_qa", "event.file", "event.file.#")
    create_queue_bind(channel, "file_event_query", "event.file", "event.file.#")
    assert exist_queue("file_event_qa")
    assert exist_queue("file_event_query")
