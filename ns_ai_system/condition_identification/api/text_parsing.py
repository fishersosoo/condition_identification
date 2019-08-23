# coding=utf-8
import json

from condition_identification.doctree_contruction.DocTree import *
from condition_identification.rdf_triple.triple_tree import constructTriple
from condition_identification.doctree_contruction.DocTreeOp import getTitle
from condition_identification.doctree_contruction.util import str_to_list
from condition_identification.industry_filter.industryFilter import industryFilter


class Document:
    """
    表示一个指南文档，指南文档包括了多个条件语句和一个标题。
    """

    @classmethod
    def paragraph_extract(cls, text):
        """

        根据指南的标题结构，抽取政策条件，并构造结构树，并构造一个Document对象

        Args：
            text: str 政策文本

        Returns：
            tree: Tree 构造后的政策树


        """
        doc_tree = DocTree()
        doc_tree.construct(text)
        tree = doc_tree.get_tree()
        document = Document()
        document._tree = tree
        if document.title is None:
            document.title = getTitle(text)
            document.industries = document._get_industry(text)
        return document


    def __init__(self, title=None, sentences=None, industries=None):
        """

        Args:
            industry (list):表示政策涉及的行业
            title: 标题
            sentences: 条件列表
        """
        self._tree = None  # 用于保存树结构
        self.title = title
        if industries is None:
            self.industries = []
        if sentences is None:
            self.sentences = list()

    def to_dict(self):
        return dict(title=self.title, sentences=[one.to_dict() for one in self.sentences], industries=self.industries)

    def triple_extract(self):
        if self._tree is not None:
            self.sentences = constructTriple(self._tree)

    def _get_industry(self, text):
        text = ''.join(str_to_list(text))
        if self.title is None:
            raise RuntimeError('请获取标题')
        text += self.title
        industry = industryFilter(text)
        return industry
