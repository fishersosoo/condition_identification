# coding=utf-8
from condition_identification.util.similarity_calculation import field_compare_similarity
from data_management.api.field_info import list_all_field_name
from condition_identification.args import similarity_value


class Field(object):
    """单例模式field 类

    对于一个value值，找到他的field, 根据他与field值的相似度，
    找到相似度高的满足条件的field 建立 field_dic
    单例模式可以大大减少内存消耗，加快程序运行速度，不用每次都去数据库读field

    Attributes:
        field: list,field 组成的list
        field_dict: dict， 与某个词相似度最高的field
        field_vec_dict: dict,field与其对应的bert词向量字典

    """
    def __init__(self, bc):


        self.bert_client = bc
        self.field_name = list_all_field_name()
        self.field_dict = dict()
        self.field_encode = self._get_field_vec_dict()

    def _get_field_vec_dict(self):
        """建立field与其对应的bert词向量字典

        Returns:
            field_vec_dict: dict,field与其对应的bert词向量字典
                Examples:
                    {'营业总收入’：array(768*1),'代理机构': array(768*1)}

        """
        field_vectors = self.bert_client.encode(list(self.field_name))
        field_encode = dict()
        for field, vector in zip(self.field_name, field_vectors):
            field_encode[field] = vector
        return field_encode



    def construct_field_dict(self, keywords):
        """建立一个field 的字典

        利用相似度找出跟keywords里每个词相似度最高且满足要求的field值

        Args:
            keywords: list ,政策语句抽取出的关键词，
                Examples:  ['年度营业收入', '1000万元以上基金销售', '保险经纪', '保险代理', '金融服务业']

        Returns：
             self.field_dict: dict,
                 Examples: {'年度营业收入': '营业总收入', '保险代理': '代理机构', '金融服务业': '金融贷款'}

        """
        if len(keywords) == 0:
            return self.field_dict
        regs_vector = self.bert_client.encode(keywords)
        for line, vector in zip(keywords, regs_vector):
            max_value, max_word = field_compare_similarity(line, vector,self.field_name,self.field_encode)
            if max_word != '' and max_value > similarity_value:  # 有与它最相近的field 并且他们的 相似度满足要求
                self.field_dict[line] = max_word
        return self.field_dict


if __name__ == '__main__':
    from bert_serving.client import BertClient
    bc = BertClient()
    f = Field(bc)
    print(f.instance)
    print(f.init_fir)
    g =Field(bc)
    print(g.init_fir)
