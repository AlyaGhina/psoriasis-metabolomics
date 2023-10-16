''''
This script is used to:
1. clean up UKB data (phenotype, covariates, metabolites)
2. create a baseline characteristics table

Running this script will produce files containing:
1. cleaned data where the categorical variables are coded in numeric (cleaned_num.csv), e.g. sex = 0, 1
2. cleaned data where the categorical variables are coded in category (cleaned_cat.csv), e.g. sex = male, female
3. baseline characteristics table (baseline_tab.xlsx)

Note:
Structure of the main UKB dataset: https://choishingwan.gitlab.io/ukb-administration/pheno/data_manipulation/
'''

# Loading the dataset
import pandas as pd
import numpy as np

#path = "<file path of the extracted data>.txt.gz"
#data = pd.read_table(path, compression = "gzip", low_memory = True)
data = pd.read_csv('pheno_covar_meta.csv')

# Calling the initial visit data only, ensure the data contains variables that we want the initial visit only 
def initvis(data):
    cols = [col for col in data.columns if col.endswith('.0.0')] 
    data = pd.concat([data['f.eid'], data[cols]], axis=1)
    return data

data_initvis = initvis(data).drop(['f.131742.0.0', #first occurrence date for pso
                                  'f.131720.0.0', #first occurrence date for ad
                                  'f.131894.0.0', #first occurrence date for sle
                                  'f.131626.0.0', #first occurrence date for cd
                                  'f.131628.0.0', #first occurrence date for uc
                                  'f.131848.0.0', #first occurrence date for ra (M05)
                                  'f.131850.0.0', #first occurrence date for ra (M06)
                                  'f.6153.0.0', #self-reported medication for female
                                  'f.6177.0.0', #self-reported medication for male
                                  'f.21000.0.0', #ethnicity data (will be added later after some cleaning)
                                  'f.6138.0.0', #education data (will be added later after some cleaning)
                                  'f.53.0.0' #date of attending the assessment centre
                                  ], axis = 1)

# Calling all variables related to a particular field id
def allfield(data, field_id):
    cols = [col for col in data.columns if col.startswith('f.' + str(field_id))]
    data = data[cols]
    return data

# Cleaning medication data from self-reported questionnaire
# Here, UKB separate the questionnaire for male and female, thus need to be processed separately and then combined
med_f = allfield(data, 6153)
med_f['combined'] = med_f.apply(lambda row: int(1) if 1.0 in [row['f.6153.0.0'],
                                                              row['f.6153.0.1'], 
                                                              row['f.6153.0.2'], 
                                                              row['f.6153.0.3']
                                                              ] else np.nan, axis=1)

med_m = allfield(data, 6177)
med_m['combined'] = med_m.apply(lambda row: int(1) if 1.0 in [row['f.6177.0.0'],
                                                              row['f.6177.0.1'],
                                                              row['f.6177.0.2']
                                                              ] else np.nan, axis=1)

data_initvis['f.6177_6153.0.0'] = med_m['combined'].fillna(med_f['combined']).replace(np.nan, int(0))

# Cleaning ethnicity data
#
# Here we combine values from the initial visit and repeats
# since ethnicity doesn't change and we can fill in data if not captured in the initial visit
# 
# We will also map the values with higher ethnicity category 
# (0 = other, 1 = caucasian, 2 = mixed, 3 = asian non-chinese, 4 = black, 5 = chinese)
# See UKB ethnicity data coding: https://biobank.ndph.ox.ac.uk/showcase/coding.cgi?id=1001
eth = allfield(data, 21000)
eth['combined'] = eth['f.21000.0.0'].fillna(eth['f.21000.1.0'].fillna(eth['f.21000.2.0']))

eth['group'] = np.nan  

for i in range(len(eth)):
    row = eth.iloc[i]  # Get each row in the dataset
    if 1 in row.values or 1001 in row.values or 1002 in row.values or 1003 in row.values:
        eth.at[i, 'group'] = 1 # Caucasian
    elif 2 in row.values or 2001 in row.values or 2002 in row.values or 2003 in row.values or 2004 in row.values:
        eth.at[i, 'group'] = 2 # Mixed
    elif 3 in row.values or 3001 in row.values or 3002 in row.values or 3003 in row.values or 3004 in row.values:
        eth.at[i, 'group'] = 3 # Asian Non-Chinese
    elif 4 in row.values or 4001 in row.values or 4002 in row.values or 4003 in row.values:
        eth.at[i, 'group'] = 4 # Black
    elif 5 in row.values:
        eth.at[i, 'group'] = 5 # Chinese
    elif 6 in row.values:
        eth.at[i, 'group'] = 0 # Other
    else:
        eth.at[i, 'group'] = np.nan

data_initvis['f.21000.0.0'] = eth['group']

# Cleaning education data
#
# In UKB, this question may have more than 1 answer
# We map the values in the initial visits columns, for the highest education (0 = primary, 1 = secondary, 2 = post-secondary/higher education)
#   Code -7 = primary education (10 years or less)
#   Code 2, 3, 4, and = secondary education (11-13 years)
#   Code 1, 5, 6 = post-secondary and higher education (14 years or more)
# 
# See UKB education data coding: https://biobank.ndph.ox.ac.uk/showcase/coding.cgi?id=100305
edu = allfield(data, 6138)

edu['combined'] = np.nan

for i in range(len(edu)):
    row = edu.iloc[i]  # Get each row in the dataset
    if 1.0 in row.values or 5.0 in row.values or 6.0 in row.values:
        edu.at[i, 'combined'] = 2  # Set to 2 if 1.0, 5.0, or 6.0 are present
    elif 2.0 in row.values or 3.0 in row.values or 4.0 in row.values:
        edu.at[i, 'combined'] = 1  # Set to 1 if 2.0, 3.0, or 4.0 are present
    elif -7.0 in row.values:
        edu.at[i, 'combined'] = 0
    else:
        edu.at[i, 'combined'] = np.nan

data_initvis['f.6138.0.0'] = edu['combined']

# Define prevalent cases
# Defined as first occurrence date before attending the assessment centre
# For RA, it can be defined by >1 ICD-10 code
cols_date= ['f.131742.0.0', #first occurrence date for pso
            'f.131720.0.0', #first occurrence date for ad
            'f.131894.0.0', #first occurrence date for sle
            'f.131626.0.0', #first occurrence date for cd
            'f.131628.0.0' #first occurrence date for uc
            ]

imids = ['pso', 'ad', 'sle', 'cd', 'uc']

data[cols_date + ['f.53.0.0']] = data[cols_date + ['f.53.0.0']].apply(pd.to_datetime)

for i in range(len(cols_date)):
    data_initvis[imids[i]] = np.where((data[cols_date[i]] < data['f.53.0.0']) & (data[cols_date[i]].notnull()), 1, 0)

data_initvis['ra'] = ((data['f.131848.0.0'] < data['f.53.0.0']) | (data['f.131850.0.0'] < data['f.53.0.0'])).astype(int)

# Convert codes into name based on a particular dictionary
def convcod(lst, dic):
    update = list((pd.Series(lst)).map(dic))
    return update

# Dictionary of field id names
ids_codes = {'f.eid':'f.eid',
             'f.74.0.0':'fas_t',
             'f.31.0.0':'sex',
             'f.21001.0.0':'bmi',
             'f.738.0.0':'inc',
             'f.20116.0.0':'smo',
             'f.20117.0.0':'alc',
             'f.21003.0.0':'age',
             'f.6177_6153.0.0':'med_chol',
             'f.21000.0.0':'eth',
             'f.6138.0.0':'edu',
             'pso':'pso',
             'ra':'ra',
             'sle':'sle',
             'ad':'ad',
             'uc':'uc',
             'cd':'cd',
            }

# Dictionary of metabolite codes
id_met = pd.read_csv('metabolomics_field_ids.csv')
met_codes = dict(zip(id_met.field, id_met.abbreviation))

# Convert columns with field id codes into field names
data_initvis.columns = convcod(list(data_initvis.columns), {**ids_codes, **met_codes})

#------------------- Cleaning up metabolomics data----------------------#

# Removing rows with missing values >20%
data_initvis = data_initvis.dropna(thresh = 0.8 * len(data_initvis.columns))

# Export to csv
data_initvis.to_csv('data_initvis_num.csv')
# This data will be used for the subsequent analysis

#------------- Creating the baseline characteristics table--------------#
# Dictionary of ethnicity codes
eth_codes = {0: 'other',
             1: 'caucasian',
             2: 'mixed',
             3: 'asian non-chinese',
             4: 'black',
             5: 'chinese',
             }

# Dictionary of income codes
inc_codes = {-1:np.nan, # do not know
             -3:np.nan, # prefer not to answer
             1:'<18k',
             2:'18k-30.9k',
             3:'31k-51.9k',
             4:'52k-100k',
             5:'>100k'
            }

# Dictionary of education level codes
edu_codes = {0:'primary',
             1:'secondary',
             2:'post-secondary'
            }

# Dictionary of smoking and alcohol drinking status codes
smoalc_codes = {-1:np.nan, # do not know
                -3:np.nan, # prefer not to answer
                0:'never',
                1:'previous',
                2:'current'
                }

# Dictionary of sex codes
sex_codes = {0:'female', 1:'male'}

# Dictionary of yes/no codes (med, pso)
oth_codes = {0:'no', 1:'yes'}

data_initvis['eth'] = convcod(data_initvis['eth'], eth_codes)
data_initvis['inc'] = convcod(data_initvis['inc'], inc_codes)
data_initvis['edu'] = convcod(data_initvis['edu'], edu_codes)
data_initvis['sex'] = convcod(data_initvis['sex'], sex_codes)

smoalc_vars = ['smo', 'alc']
for i in range(len(smoalc_vars)):
    data_initvis[smoalc_vars[i]] = convcod(data_initvis[smoalc_vars[i]], smoalc_codes)

oth_vars = ['pso', 'ad', 'ra', 'sle', 'uc', 'cd', 'med_chol']
for i in range(len(oth_vars)):
    data_initvis[oth_vars[i]] = convcod(data_initvis[oth_vars[i]], oth_codes)

# Export to csv
data_initvis.to_csv('data_initvis_cat.csv')

# Create baseline characteristics table
from tableone import TableOne

cat_vars = ['sex', 'inc', 'smo', 'alc', 'med_chol', 'eth', 'edu']
cont_vars = ['fas_t', 'bmi', 'age']
outcomes = ['pso', 'ad', 'ra', 'sle', 'uc', 'cd']

for k in range(len(outcomes)):
    outcome = [outcomes[k]]
    baseline = data_initvis[cat_vars + cont_vars + outcome]
    baseline_table = TableOne(baseline,
                              categorical = cat_vars,
                              groupby = outcome,
                              pval = False)
    baseline_table.to_excel(f'[{outcomes[k]}] baseline_tab.xlsx')