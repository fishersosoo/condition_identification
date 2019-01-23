# coding=utf-8

from flask import request, jsonify
from flask_restful import Api, Resource, reqparse

from celery_task.policy.base import get_pending_task
from celery_task.policy.tasks import understand_guide_task, recommend_task, check_single_guide_batch_companies
from data_management.models.guide import Guide
from data_management.models.policy import Policy
from restful_server.policy import policy_service
from restful_server.policy.base import check_callback
from restful_server.server import mongo

policy_api = Api(policy_service)


class PolicyUnderstandAPI(Resource):
    """
    处理政策理解请求
    """
    post_parser = reqparse.RequestParser()
    post_parser.add_argument("id", type=str, required=True)
    post_parser.add_argument("content", type=str, required=True)

    def post(self):
        kwargs = self.post_parser.parse_args()
        return {}, 200


class PolicyRecommendAPI(Resource):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("id", type=str, required=True)

    def get(self):
        kwargs = self.get_parser.parse_args()
        return {}, 200


@policy_service.route("upload_policy/", methods=["POST"])
def upload_policy():
    """
    上传政策文件
    :return:
    """
    policy_file = request.files['file']
    policy_id = request.args.get("policy_id")
    # save file
    mongo.save_file(filename=policy_file.filename,
                    fileobj=policy_file, base="policy_file")
    Policy.create(policy_id=policy_id, file_name=policy_file.filename)
    return jsonify({
        "status": "success"
    })


@policy_service.route("upload_guide/", methods=["POST"])
def upload_guide():
    """
    上传政策指南
    :return:
    """
    guide_file = request.files['file']
    guide_id = request.form.get("guide_id")
    assert guide_id is not None
    mongo.save_file(filename=guide_file.filename,
                    fileobj=guide_file, base="guide_file")
    Guide.create(guide_id=guide_id, file_name=guide_file.filename)
    policy_id = request.args.get("policy_id", default=None)
    if policy_id is not None:
        Guide.link_to_policy(guide_id, policy_id)
    result = understand_guide_task.delay(guide_id)
    return jsonify({
        "task_id": result.id,
        "status": "SUCCESS"
    })


@policy_service.route("recommend/", methods=["GET"])
def recommend():
    """
    获取推荐结果
    :return:
    """
    response_dict = dict()
    if "company_id" in request.args:
        # 根据企业id获取推荐，返回结果并异步更新结果
        company_id = request.args.get("company_id")
        task_result = recommend_task.delay(company_id)
        response_dict["task_id"] = task_result.id
        records = [one for one in mongo.db.recommend_record.find({"company_id": company_id, "latest": True})]
        response_dict["result"] = records
        return jsonify(response_dict)
    if "task_id" in request.args:
        # 查看异步任务结果
        task_id = request.args.get("task_id")
        result = recommend_task.AsyncResult(task_id)
        state = result.state
        response_dict['status'] = state
        if state == "SUCCESS":
            results = result.get()
            records = [one for one in
                       mongo.db.recommend_record.find({"company_id": results["company_id"], "latest": True})]
            response_dict["result"] = records
        else:
            response_dict["result"] = []
    return jsonify(response_dict)


@policy_service.record("check_recommend/", methods=["POST"])
def check_single_guide_for_companies():
    """
    多个企业和单个政策的匹配情况
    :return:
    """
    MAX_PENDING = 120
    params = request.json
    companies = params.get("companies", [])
    # 检查参数是否正确
    guide_id = params.get("guide_id", None)
    _, _, guide_node = Guide.find_by_guide_id(guide_id)
    if guide_node is None:
        return jsonify({
            "task_id": "",
            "message":
                {
                    "status": "NOT_FOUND",
                    "traceback": guide_id
                }})
    callback_ok, callback_stack = check_callback(params.get("callback", None), params.get("guide_id", ))
    if not callback_ok:
        return jsonify({
            "task_id": "",
            "message":
                {
                    "status": "CALLBACK_FAIL",
                    "traceback": callback_stack
                }
        })
    max_input = MAX_PENDING - len(get_pending_task("check_single_guide"))
    if max_input == 0:
        # 队列已满
        return jsonify({
            "task_id": "",
            "message":
                {
                    "status": "FULL",
                    "traceback": companies
                }
        })
    elif max_input >= len(companies):
        # 队列能放进去
        task_result = check_single_guide_batch_companies.delay(companies, guide_id,
                                                               params.get("callback", None))
        return jsonify({
            "task_id": task_result.id,
            "message":
                {
                    "status": "SUCCESS",
                    "traceback": None
                }
        })
    else:
        # 队列有空位
        task_result = check_single_guide_batch_companies.delay(companies[:max_input], guide_id,
                                                               params.get("callback", None))
        return jsonify({
            "task_id": task_result.id,
            "message":
                {
                    "status": "FULL",
                    "traceback": companies[max_input:]
                }
        })


policy_api.add_resource(PolicyUnderstandAPI, "understand/")
policy_api.add_resource(PolicyRecommendAPI, "recommend/")
