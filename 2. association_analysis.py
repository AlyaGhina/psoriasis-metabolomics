# Import libraries and dataset
import pandas as pd
import numpy as np

data = pd.read_csv('<filename>.csv') # Data should not contains NaN

# Z transformation for numerical variables
import scipy.stats as stats

continuous = ['age', 'bmi']
categorical = ['pso', 'ad', 'ra', 'sle', 'cd', 'uc', 'sex', 'eth', 'alc', 'smo']

meta = list(data.loc[:,'total_C':'S_HDL_TG_pct'].columns)

df = data[continuous + meta].apply(stats.zscore)
df[categorical] = data[categorical]

# Performing logistic regression for association analysis
import statsmodels.api as sm
import statsmodels.formula.api as smf

outcomes = ['pso', 'ad', 'ra', 'sle', 'cd', 'uc']
met_cols = data.loc[:, 'total_C':'S_HDL_TG_pct'].columns

for k in range(len(outcomes)):
    mets = []
    ors = []
    lo_ci = []
    up_ci = []
    pvals = []
    
    for i in range(len(met_cols)):
        mets.append(met_cols[i])
        formula = str(outcomes[k]) + '~ age + sex + bmi + ' + str(met_cols[i])
        model = smf.glm(formula = formula, data = df, family = sm.families.Binomial())
        result = model.fit()
        ors.append(np.exp(result.params.to_frame()).iloc[-1,0])
        lo_ci.append(np.exp(result.conf_int()).iat[-1, 0])
        up_ci.append(np.exp(result.conf_int()).iat[-1, 1])
        pvals.append(result.pvalues.to_frame().iloc[-1,0])
    
    res = {'Metabolite':mets,'OR':ors, 'Lower CI': lo_ci, 'Upper CI': up_ci, 'P-Value': pvals}
    res_df = pd.DataFrame(res)
    res_df['Difference'] = abs(res_df['OR']-1)
    sorted_res_df = res_df.sort_values('Difference', ascending = False)
    sorted_res_df.to_excel(f'[{outcomes[k]}] summary statistics.xlsx', index=False)

