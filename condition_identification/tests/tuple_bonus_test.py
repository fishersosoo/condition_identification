# coding=utf-8
import sys
import re
sys.path.append("..")

from bonus_identify.Tree import DocTree
from predicate_extraction.tuple_bonus_recognize import TupleBonus

def test_subtree():
    tree=DocTree('../bonus_identify/广州南沙新区(自贸片区)促进总部经济发展扶持办法｜广州市南沙区人民政府.txt')
    tree.construct()
    tuplebonus = TupleBonus()
    tuplebonus.bonus_tuple_analysis(tree)
    tuplebonus.get_bonus_tree().show()


if __name__ == "__main__":
    test_subtree()
