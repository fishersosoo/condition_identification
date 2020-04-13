# coding=utf-8
import copy
import datetime
import traceback
import time
import json
from enum import Enum, unique

from celery_task import celery_app, log, config, rpc_server
from data_management.config import py_client, redis_cache
from service import conert_ch2num
from service.policy_graph_construct import understand_guide
from service.base_func import format_record, match_with_labels
from data_server.server import client, uid
from data_management.models.label import Label


@unique
class MatchResult(Enum):
    """
    表示匹配结果
    """
    MISMATCH = 0
    MATCH = 1
    UNRECOGNIZED = 2


@celery_app.task
def status_check():
    """
    检查状态

    Returns:

    """
    pass


@celery_app.task
def understand_guide_task(guide_id, text):
    """

    :param guide_id: 指南的外部id
    :return:
    """
    understand_guide(guide_id, text)


@celery_app.task
def check_single_guide(company_id, guide_id, labels, routing_key, threshold=.0):
    """

    Args:
        company_id:
        guide_id:
        routing_key:
        threshold:

    Returns:

    """
    start = time.time()
    record = _check_single_guide(company_id, guide_id, threshold=threshold)
    end = time.time()
    log.info(f"{company_id}-{guide_id} check_single_guide time:{end-start} seconds")
    log.info(f"{company_id}-{guide_id} check_single_guide record:{record}")
    if record is None:
        rpc_server().rabbitmq.push_message("task", routing_key,
                                           {"company_id": company_id, "guide_id": guide_id, "score": None})
    else:
        labels = Label.convert_texts(labels)
        record, _ = match_with_labels(record, labels)
        record = format_record(record)
        rpc_server().rabbitmq.push_message("task", routing_key,
                                           {"company_id": company_id, "guide_id": guide_id, "score": record["score"]})
    return record


def filter_industry(company_id, industries):
    """
    判断企业是否在指定行业内
    Args:
        company_id: 企业id
    Returns:
        (bool)是否在指定行业内
    """

    if industries is None or "Empty" in industries or len(industries) == 0:
        return True
    else:
        return_data = rpc_server().data.sendRequest(company_id, f"DR1.INDUSTRY")
        data = return_data.get("result", None)
        if data is None:
            return True
        for one in data:
            if one in industries:
                return True
        return False


def _check_single_guide(company_id, guide_id, threshold=.0):
    """
    检查单个指南和企业的匹配信息，如果存在匹配则存放到数据库中
    :param company_id:企业id
    :param guide_id:指南的平台id
    :return:
    {
        "company_id": "",
        "guide_id": "",
        "time": datetime.datetime.utcnow(),
        "latest": True,
        "has_label": False,
        "sentences": [
            {
                "text":"",
                "type": "正常",
                "result": "",
                "clauses":[
                    {
                        "fields":["专利名称",],
                        "relation":"是",
                        "value":"规定航运物流",
                        "result":"mismatch"
                    },
                ]
            }
        ]
    }
    """

    start = time.time()
    record = {"has_label": False, "sentences": [], }
    # record = {"mismatch": [], "match": [], "unrecognized": []}
    clause_sentence = dict()
    cached_data = dict()
    ret = py_client.ai_system["parsing_result"].find_one({"guide_id": str(guide_id)})
    if ret is None:
        log.info(f"guide_id:{guide_id} not found or have not been processed.")
        return None
    document = ret.get("document", None)
    if document is None:
        return None
    if not filter_industry(company_id, document.get("industries", None)):
        insert_industry_mismatch_record(company_id, guide_id, record)
        return None
    end = time.time()
    log.info(f"{company_id}-{guide_id} before check_single_requirement time:{end-start} seconds")
    for sentence in document["sentences"]:
        if sentence["type"] != "正常" and len(sentence["clauses"]) != 0:
            # 承诺及描述人的条件，标识为未识别
            sentence["result"] = "unrecognized"
            record["sentences"].append(sentence)
            continue
        if len(sentence["clauses"]) == 0:
            # 丢弃掉提取不出条件的句子
            continue
        recognized = False
        has_match = False
        for clause in sentence["clauses"]:
            # 遍历句子中识别出的条件，并给每个条件标记上是否匹配
            triple = clause
            if len(triple["fields"]) == 0:
                clause["result"] = "unrecognized"
                continue
            start = time.time()
            match, data, cached_data = check_single_requirement(company_id, triple, cached_data, guide_id)
            end = time.time()
            log.info(f"{company_id}-{guide_id} during check_single_requirement time:{end-start} seconds")
            if match == MatchResult.MISMATCH:
                clause["result"] = "mismatch"
                recognized = True
            if match == MatchResult.MATCH:
                clause["result"] = "match"
                recognized = True
                has_match = True
            if match == MatchResult.UNRECOGNIZED:
                clause["result"] = "unrecognized"
        sentence["result"] = "unrecognized"
        if recognized:
            sentence["result"] = "mismatch"
        if has_match:
            sentence["result"] = "match"
        record["sentences"].append(sentence)

    record["company_id"] = company_id
    record["guide_id"] = guide_id
    record["time"] = datetime.datetime.utcnow()
    record["latest"] = True
    start = time.time()
    py_client.ai_system["recommend_record"].delete_many({"company_id": company_id,
                                                         "guide_id": guide_id})
    py_client.ai_system["recommend_record"].insert_one(copy.deepcopy(record))
    end = time.time()
    log.info(f"{company_id}-{guide_id} end check_single_requirement time:{end-start} seconds")
    return record


def insert_industry_mismatch_record(company_id, guide_id, record):
    """
     不匹配行业时，还是插入数据，但加多一个mismatch_industry的标记
    Args:
        company_id:
        guide_id:
        record:

    Returns:

    """
    record["company_id"] = company_id
    record["guide_id"] = guide_id
    record["time"] = datetime.datetime.utcnow()
    record["score"] = -1
    record["latest"] = True
    record["mismatch_industry"] = True
    py_client.ai_system["recommend_record"].delete_many({"company_id": company_id,
                                                         "guide_id": guide_id})
    py_client.ai_system["recommend_record"].insert_one(copy.deepcopy(record))


def check_single_requirement(company_id, triple, cached_data, guide_id):
    """
    检查企业是否满足单一条件

    Args:
        cached_data: 缓存的数据
        company_id: 企业id
        triple: 三元组

    Returns:
        MatchResult, Data, cached_data
        MatchResult类表示是否满足或者未识别.
        Data，表示企业真实数据
    """

    if "独立法人资格" in triple["value"]:
        return MatchResult.MATCH, "", cached_data
    # field = triple["fields"][0]
    for index, field in enumerate(triple["fields"]):
        field_info = py_client.ai_system["field"].find_one({"item_name": field})
        if field_info is None:
            log.info(f"no field {field}")
            if index == len(triple["fields"]) - 1:
                return MatchResult.UNRECOGNIZED, "", cached_data
            else:
                continue
        log.info(f"item: {field_info['resource_id']}.{field_info['item_id']}")
        # data = cached_data.get(f"{field_info['resource_id']}.{field_info['item_id']}", None)
        data = redis_cache.get(f"{company_id}.{field_info['resource_id']}.{field_info['item_id']}")
        if data is None:
            # query_data
            start = time.time()
            #return_data = rpc_server().data.sendRequest(company_id, f"{field_info['resource_id']}.{field_info['item_id']}")
            try:
                value = client.service.getParamInfo(uid, company_id, f"{field_info['resource_id']}.{field_info['item_id']}")._value_1
                value = json.loads(value)
                if value["Status"] == "Success":
                    result = value["Result"]
                    data = [list(one.values())[0] for one in result]
                else:
                    data = None
            except:
                data = None
            end = time.time()
            log.info(f"{company_id} request time: {end-start} seconds")
            #data = return_data.get("result", None)
            # 用"null"来代表请求回来仍为空的字段，缓存起来，不再重复请求
            if data is None:
                redis_cache.set(f"{company_id}.{field_info['resource_id']}.{field_info['item_id']}", 'null', ex=600)
        elif data != 'null':
            data = json.loads(data)
        if data is None or data == 'null':
            if index == len(triple["fields"]) - 1:
                return MatchResult.UNRECOGNIZED, "", cached_data
            else:
                continue
        else:
            redis_cache.set(f"{company_id}.{field_info['resource_id']}.{field_info['item_id']}", json.dumps(data), ex=600)
            cached_data[f"{field_info['resource_id']}.{field_info['item_id']}"] = data
        if triple["relation"] in ["大于", "小于"]:
            match, data = compare_literal(data, triple)
            return match, data, cached_data
        else:
            if triple["relation"] == "位于":
                if triple["value"] in data[0]:
                    return MatchResult.MATCH, data[0], cached_data
                else:
                    if index == len(triple["fields"]) - 1:
                        return MatchResult.MISMATCH, data[0], cached_data
                    else:
                        continue
            if triple["relation"] == "否":
                if triple["value"] not in data[0]:
                    return MatchResult.MATCH, data[0], cached_data
                else:
                    if index == len(triple["fields"]) - 1:
                        return MatchResult.MISMATCH, data[0], cached_data
                    else:
                        continue
            if triple["relation"] == "是":
                if triple["value"] in data[0]:
                    return MatchResult.MATCH, data[0], cached_data
                else:
                    if index == len(triple["fields"]) - 1:
                        return MatchResult.MISMATCH, data[0], cached_data
                    else:
                        continue


def compare_literal(data, triple):
    query_values = []
    for one_data in data:
        try:
            query_values.append(float(one_data))
        except:
            pass
    if len(query_values) == 0:
        log.info(f"can not convert value of {triple['fields'][0]} to float")
        return MatchResult.UNRECOGNIZED, ""
    try:
        value = conert_ch2num(triple["value"])
    except:
        log.info(f"can not convert value \"{triple['value']}\" to float")
        return MatchResult.UNRECOGNIZED, ""
    if triple["relation"] == "大于":
        for query_value in query_values:
            if query_value > value:
                return MatchResult.MATCH, query_value
        return MatchResult.MISMATCH, query_values[0]
    else:
        for query_value in query_values:
            if query_value < value:
                return MatchResult.MATCH, query_value
        return MatchResult.MISMATCH, query_values[0]


@celery_app.task
def recommend_task(company_id, guide_id, threshold=.0):
    """
    更新指定企业的推荐记录
    :param company_id: 企业id
    :param threshold: 匹配度阈值（尚未使用），只有企业与指南匹配度高于此值时候才会推荐
    :param guide_id: 政策id
    :return:
    """
    try:
        log.info(f"recommend_task for company: {company_id}")
        log.info(f"recommend_task for guide: {guide_id}")
        # guides = list(Guide.list_valid_guides())
        # results = []
        # for guide in guides:
        result = _check_single_guide(company_id, guide_id)
        # if result is not None:
        # results.append(result)
        # task_group = group([check_single_guide.s(company_id, guide) for guide in guides])
        # 异步执行
        # result = job.apply_async()
        # 同步执行
        # result = task_group().get()
        return {"company_id": company_id, "result": result}
    except Exception as e:
        log.error(str(guide_id))
        log.error(traceback.format_exc())
        return None


def is_above_threshold(result, threshold):
    try:
        return float(result["score"]) >= float(threshold)
    except:
        return False

@celery_app.task
def update_recommend_record_with_label(company_id, guide_id, record_to_update):
    # guide_ids_with_label = json.loads(guide_ids_with_label)
    record_to_update = json.loads(record_to_update)
    record_to_update["time"] = datetime.datetime.utcnow()
    py_client.ai_system["recommend_record_with_label"].delete_many({"company_id": company_id,
                                                    "guide_id": guide_id})
    py_client.ai_system["recommend_record_with_label"].insert_one(copy.deepcopy(record_to_update))
    # for one in record_to_update:
    #     one["time"] = datetime.datetime.utcnow()
    # py_client.ai_system["recommend_record_with_label"].delete_many({"company_id": company_id,
    #                                         "guide_id": {"$in": guide_ids_with_label}})
    # py_client.ai_system["recommend_record_with_label"].insert_many(record_to_update)
