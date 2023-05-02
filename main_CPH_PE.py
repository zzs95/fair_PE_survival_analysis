import os
import sys
sys.path.append(os.getcwd())
import numpy as np
import matplotlib.pyplot as plt
from sksurv.metrics import concordance_index_censored
from sksurv.linear_model import CoxPHSurvivalAnalysis
import pandas as pd
# from copy import deepcopy
from file_and_folder_operations import *
from prepare_dict import get_datadict

def process(group = 'race'):
    random_state_i = 777
    global df_dict0
    df_dict = deepcopy(df_dict0)
    print(random_state_i, group)
    df_dict, img_feat_dict, text_feat_dict, \
    event_dict, time_dict, labels_dict, race_dict, ethnicity_dict, sex_dict, \
    AHA_dict, PESI_dict, PESI_caseid_dict, PESI_prams_dict, = get_datadict(df_dict, random_state_i)
    if group == 'race':
        group_dict = race_dict
        key_2 = ['ts_race_White', 'ts_race_Color', ]
    elif group == 'ethnicity':
        group_dict = ethnicity_dict
        key_2 = ['ts_ethnicity_nolatino', 'ts_ethnicity_latino', ]
    elif group == 'sex':
        group_dict = sex_dict
        key_2 = ['ts_sex_men', 'ts_sex_women']

    # save feats
    save_feat_root = f'./cph_exps/{group}/result_{str(random_state_i)}/'
    save_dict_root = join(save_feat_root, 'KM_dict')
    maybe_mkdir_p(save_dict_root)
     
    train_set = 'tr'
    cox_model_img = CoxPHSurvivalAnalysis(alpha=0.1, verbose=2, n_iter=10)
    cox_model_img = cox_model_img.fit(img_feat_dict[train_set], labels_dict[train_set])
    cox_model_text = CoxPHSurvivalAnalysis(alpha=0.1, verbose=2, n_iter=10)
    cox_model_text = cox_model_text.fit(text_feat_dict[train_set], labels_dict[train_set])
    cox_model_clin = CoxPHSurvivalAnalysis(alpha=0.1, verbose=2, n_iter=10)
    cox_model_clin = cox_model_clin.fit(PESI_prams_dict[train_set], labels_dict[train_set])
    cox_cph = CoxPHSurvivalAnalysis()
    cox_fuse_PESI_cph = CoxPHSurvivalAnalysis()

    c_d = {}
    # test the performance
    c_d['PESI_c_ind_dict'] = {}
    c_d['cph_img_dict'] = {}
    c_d['cph_text_dict'] = {}
    c_d['cph_clin_dict'] = {}
    c_d['cph_fuse_dict'] = {}
    c_d['cph_fuse_PESI_dict'] = {}

    # evaluate
    for trts in list(df_dict.keys()):
        if trts in ['tr', 'ts', 'ts_'+group, ] + key_2:
            # ----------PESI c index
            c_d['PESI_c_ind_dict'][trts] = concordance_index_censored(event_dict[trts].astype(bool), time_dict[trts], PESI_dict[trts])[0]
            # # ----------RSF c index
            c_d['cph_img_dict'][trts] = cox_model_img.score(img_feat_dict[trts], labels_dict[trts])
            c_d['cph_text_dict'][trts] = cox_model_text.score(text_feat_dict[trts], labels_dict[trts])
            c_d['cph_clin_dict'][trts] = cox_model_clin.score(PESI_prams_dict[trts], labels_dict[trts])

            risk_img = cox_model_img.predict(img_feat_dict[trts])
            risk_text = cox_model_text.predict(text_feat_dict[trts])
            risk_clin = cox_model_clin.predict(PESI_prams_dict[trts])
            risk_imgclin = np.concatenate((np.array(risk_img)[None], np.array(risk_text)[None], np.array(risk_clin)[None]), axis=0)
            risk_imgclin = np.transpose(risk_imgclin)

            if trts == train_set:
                cox_cph = cox_cph.fit(risk_imgclin, labels_dict[trts])
            c_d['cph_fuse_dict'][trts] = cox_cph.score(risk_imgclin, labels_dict[trts])
            risk_cph_fused = cox_cph.predict(risk_imgclin)

            risk_concatPESI = np.concatenate([risk_cph_fused[:,None], PESI_dict[trts][:,None]], axis=1)
            if trts == train_set:
                cox_fuse_PESI_cph = cox_fuse_PESI_cph.fit(risk_concatPESI, labels_dict[trts])
            c_d['cph_fuse_PESI_dict'][trts] = cox_fuse_PESI_cph.score(risk_concatPESI, labels_dict[trts])
            risk_cph_fused_PESI = cox_fuse_PESI_cph.predict(risk_concatPESI)

            cph_fused_curves = cox_cph.predict_survival_function(risk_imgclin)
            cph_fused_PESI_curves = cox_fuse_PESI_cph.predict_survival_function(risk_concatPESI)

            KM_dict = {'risk_img':risk_img, 'risk_text':risk_text, 'risk_clin':risk_clin,
                       'risk_cph_fused': risk_cph_fused, 'risk_cph_fused_PESI':risk_cph_fused_PESI,
                       'cph_fused_curves': cph_fused_curves, 'cph_fused_PESI_curves':cph_fused_PESI_curves,
                       'id_list':group_dict[trts],
                       'PESI_scores':PESI_dict[trts], 'PESI_caseid':PESI_caseid_dict[trts], 'PESI_variables':PESI_prams_dict[trts],
                       'time': time_dict[trts], 'event':event_dict[trts],}
            KM_dict_npy_path = join(save_dict_root, 'cph'+'@'+trts+'.npy')
            np.save(KM_dict_npy_path, KM_dict)
    return c_d


if __name__ == '__main__':
    label_path = './PE_data/pe_label_search.xls'
    labels_df_s = pd.read_excel(label_path)
    labels_df_s['Age'] = (labels_df_s['Age'] / labels_df_s['Age'].max())
    labels_df_s['follow_up_day'] = labels_df_s['follow_up_day'] / labels_df_s['follow_up_day'].max()
    RIH_df = labels_df_s.loc[labels_df_s['Var22'] == 'RIH']
    TMH_df = labels_df_s.loc[labels_df_s['Var22'] == 'TMH']
    NPH_df = labels_df_s.loc[labels_df_s['Var22'] == 'NPH']
    df_dict0 = {'RIH': RIH_df,
                "TMH": TMH_df,
                "NPH": NPH_df,
                }

    out_xlsx_folder = './cph_exps/out_xlsx'
    maybe_mkdir_p(out_xlsx_folder)
    for group in ['race', 'ethnicity', 'sex']:
        out_c_ind_dict = process( group)
        out_df = pd.DataFrame.from_dict(out_c_ind_dict).transpose()
        out_filename = 'CPH_'+group+'.xlsx'
        out_xlsx_path = join(out_xlsx_folder, out_filename)
        out_df.to_excel(out_xlsx_path)




