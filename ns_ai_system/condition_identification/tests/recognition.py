from condition_identification.api.text_parsing import paragraph_extract
from condition_identification.api.text_parsing import triple_extract
import os
import pandas as pd
import numpy as np

def isin(a, b):
    isin_flag = True
    for w in a:
        if w not in b:
            isin_flag = False
            break
    return isin_flag



def get_acc_pre(true_df_txt, triples):
    true_df_txt_len = true_df_txt.shape[0]
    predict_len = len(triples)
    txt_tr = 0 # 用来算准确率
    triple_tr = 0 # 用来算召回率,一个句子中多个实体三元组都满足
    for i in range(true_df_txt_len):
        sentence = true_df_txt['原文'].values[i]
        target = true_df_txt['列名'].values[i]
        is_none = True
        acc_flag=True
        for triple in triples:
            if isin(triple['sentence'], sentence) or isin(sentence, triple['sentence']):
                is_none = False
                pre = triple['fields']
                # 标注时把行业领域统一标成了经营业务范围
                if '行业领域' in pre:
                    pre.append('经营业务范围')
                # 因为同一个句子可能有多个实体，所以需要遍历所有实体
                if target in pre:
                    print(sentence)
                    triple_tr += 1
                    if acc_flag:
                        txt_tr+=1
                        acc_flag=False


        if target == 'None' and is_none:
            txt_tr += 1
            predict_len += 1
            triple_tr += 1
    return txt_tr,triple_tr,predict_len



if __name__ == '__main__':

    policy_file_dir = r"F:\\txt\\txt"
    true_file=r'G:\\QQ文件\\政策标注.csv'
    score_file='score0419.txt'

    true_df = pd.read_csv(true_file, engine='python')
    score_record = open(score_file, 'a')

    # 计算
    acc_result = []
    rec_result = []
    all_acctrue = 0
    all_rectrue = 0
    all_count = 0
    all_precount=0

    for j in range(0,40):
        true_df_txt = true_df[true_df['序号'] == j]
        if true_df_txt.shape[0] == 0:
            continue
        with open(os.path.join(policy_file_dir,str(j)+".txt"), encoding="utf8") as f:
            text = f.read()

        paragraph_extract_output = paragraph_extract(text)
        triples = triple_extract(paragraph_extract_output)
        true_df_txt_len = true_df_txt.shape[0]
        print(triples)
        txt_tr, triple_tr, predict_len = get_acc_pre(true_df_txt, triples)





        acc = txt_tr/true_df_txt_len
        acc_result.append(acc)

        if predict_len==0:
            recall=1
        else:
            recall=triple_tr/predict_len
        rec_result.append(recall)

        all_acctrue += txt_tr
        all_rectrue += triple_tr
        all_count += true_df_txt_len
        all_precount += predict_len

        print("%s 文件准确率 %f" % (str(j), acc))
        print("%s 文件召回率 %f" % (str(j), recall))

        score_record.write("%s 文件准确率 %f" % (str(j), acc))
        score_record.write('\n')
        score_record.write("%s 文件召回率 %f" % (str(j), recall))
        score_record.write('\n')

        print("总文件准确率 %f"%np.mean(np.array(acc_result)))
        score_record.write("总文件准确率 %f" % np.mean(np.array(acc_result)))
        score_record.write('\n')

        print("总文件召回率 %f"%np.mean(np.array(rec_result)))
        score_record.write("总文件召回率 %f" % np.mean(np.array(rec_result)))
        score_record.write('\n')

        print("all_count:%s\tall_true:%s\tprecision %f" % (all_count, all_acctrue,all_acctrue/all_count))
        score_record.write("all_count:%s\tall_true:%s\tprecision %f" % (all_count, all_acctrue, all_acctrue/all_count))
        score_record.write('\n')

        print("all_precount:%s\tall_true:%s\trecall %f" % (all_precount, all_rectrue,all_rectrue/all_precount))
        score_record.write("all_precount:%s\tall_true:%s\trecall %f" % (all_precount, all_rectrue, all_rectrue/all_precount))
        score_record.write('\n')

    score_record.close()