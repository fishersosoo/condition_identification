# coding=utf-8
from flask import request, url_for
from flask_restful import Api, Resource, reqparse

from condition_identification.bonus_identify.Tree import DocTree
from condition_identification.predicate_extraction.tuple_bonus_recognize import TupleBonus
from data_management.graph_access import build_policy_graph
from data_management.models.policy import Policy
from restful_server.policy import policy_service

policy_api = Api(policy_service)


class PolicyUnderstandAPI(Resource):
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


@policy_service.route("/")
def x():
    print(url_for("policy_service.UnderstandPolicyFile"))
    return "", 200


@policy_service.route("understand_file/", methods=["GET","POST"])
def UnderstandPolicyFile():
    file = request.files['file'].read()
    policy = Policy.create(content=request.files['file'].filename)
    tree = DocTree()
    # tree.construct_from_bytes(file)
    tuplebonus = TupleBonus(None, if_edit_hanlpdict=0)
    pytree=tree.get_bonus_tree()
    print("pytree.show()")
    pytree.show()
    tuplebonus.bonus_tuple_analysis(pytree)
    build_policy_graph(policy, tuplebonus.get_bonus_tree())
    return "", 200


policy_api.add_resource(PolicyUnderstandAPI, "understand/")
policy_api.add_resource(PolicyRecommendAPI, "recommend/")

