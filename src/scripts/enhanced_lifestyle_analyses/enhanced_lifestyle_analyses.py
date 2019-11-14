# %% Import Statements
import datetime
import logging
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tlo import Date, Simulation
from tlo.analysis.utils import parse_log_file
from tlo.methods import demography, enhanced_lifestyle

# Where will output go - by default, wherever this script is run
outputpath = ''

# date-stamp to label log files and any other outputs
datestamp = datetime.date.today().strftime("__%Y_%m_%d")

# The resource file for demography module
# assume Python console is started in the top-leve TLOModel directory
resourcefilepath = Path(os.path.dirname(__file__)) / '../../../resources'

# %% Run the Simulation

start_date = Date(2010, 1, 1)
end_date = Date(2050, 1, 1)
popsize = 1000

# add file handler for the purpose of logging
sim = Simulation(start_date=start_date)

# this block of code is to capture the output to file
logfile = outputpath + 'LogFile' + datestamp + '.log'

if os.path.exists(logfile):
    os.remove(logfile)
fh = logging.FileHandler(logfile)
fr = logging.Formatter("%(levelname)s|%(name)s|%(message)s")
fh.setFormatter(fr)
logging.getLogger().addHandler(fh)

logging.getLogger("tlo.methods.demography").setLevel(logging.INFO)
logging.getLogger("tlo.methods.enhanced_lifestyle").setLevel(logging.INFO)

# run the simulation
sim.register(demography.Demography(resourcefilepath=resourcefilepath))
sim.register(enhanced_lifestyle.Lifestyle(resourcefilepath=resourcefilepath))

sim.seed_rngs(1)
sim.make_initial_population(n=popsize)
sim.simulate(end_date=end_date)

# this will make sure that the logging file is complete
fh.flush()

# %% read the results
output = parse_log_file(logfile)


# %% Plot Population Size Over time:

# Load Model Results
pop_df = output['tlo.methods.demography']['population']
Model_Years = pd.to_datetime(pop_df.date)
Model_Pop = pop_df.total
Model_Pop_Normalised = 100 * np.asarray(Model_Pop) / np.asarray(
    Model_Pop[Model_Years == '2010-01-01'])

# Load Data
resourcefile_demography = resourcefilepath / "ResourceFile_Lifestyle_Enhanced.xlsx"
Data = pd.read_excel(resourcefile_demography, sheet_name='Interpolated Pop Structure')
Data_Pop = Data.groupby(by='year')['value'].sum()
Data_Years = Data.groupby(by='year')['year'].mean()
Data_Years = pd.to_datetime(Data_Years, format='%Y')
Data_Pop_Normalised = 100 * Data_Pop / np.asarray(Data_Pop[(Data_Years == Date(2010, 1, 1))])


plt.plot(np.asarray(Model_Years), Model_Pop_Normalised)
plt.plot(Data_Years, Data_Pop_Normalised)
plt.title("Population Size")
plt.xlabel("Year")
plt.ylabel("Population Size (Normalised to 2010)")
plt.gca().set_xlim(Date(2010, 1, 1), Date(2050, 1, 1))
plt.legend(['Model', 'Data'])
plt.savefig(outputpath + 'PopSize' + datestamp + '.pdf')

plt.show()


# %% Population Pyramid in 2015

# Make Dateframe of the relevant output:

# get the dataframe for men and women:
pop_f_df = output['tlo.methods.demography']['age_range_f']
pop_m_df = output['tlo.methods.demography']['age_range_m']

# create mask for the 2015 and 2045 results:
m2015 = ((pd.to_datetime(pop_f_df['date']) >= Date(2015, 1, 1)) &
         (pd.to_datetime(pop_f_df['date']) < Date(2016, 1, 1)))
m2045 = ((pd.to_datetime(pop_f_df['date']) >= Date(2045, 1, 1)) &
         (pd.to_datetime(pop_f_df['date']) < Date(2046, 1, 1)))

# Extract the results for just 2015, and trim off the first two columns
ModelOutput_Women_2015 = (np.asarray((pop_f_df.loc[m2015]).iloc[:, 1:22])).flatten()
ModelOutput_Men_2015 = (np.asarray((pop_m_df.loc[m2015]).iloc[:, 1:22])).flatten()
ModelOutput_Women_2045 = (np.asarray((pop_f_df.loc[m2045]).iloc[:, 1:22])).flatten()
ModelOutput_Men_2045 = (np.asarray((pop_m_df.loc[m2045]).iloc[:, 1:22])).flatten()

# Trim off the last three columns (ages 90-94, 95-99, 100+) and replace the last column with the
# sum of the last four columns in the original output
ModelOutput_Women_2015_trimmed = ModelOutput_Women_2015[0:18]
ModelOutput_Women_2015_trimmed[17] = sum(ModelOutput_Women_2015[18:21])

ModelOutput_Men_2015_trimmed = ModelOutput_Men_2015[0:18]
ModelOutput_Men_2015_trimmed[17] = sum(ModelOutput_Men_2015[18:21])

ModelOutput_Women_2045_trimmed = ModelOutput_Women_2045[0:18]
ModelOutput_Women_2045_trimmed[17] = sum(ModelOutput_Women_2045[18:21])

ModelOutput_Men_2045_trimmed = ModelOutput_Men_2045[0:18]
ModelOutput_Men_2045_trimmed[17] = sum(ModelOutput_Men_2045[18:21])

# TODO: the age-group labels should be picked up in the log-file making process
Age_Group_Labels = ["0-4",
                    "5-9",
                    "10-14",
                    "15-19",
                    "20-24",
                    "25-29",
                    "30-34",
                    "35-39",
                    "40-44",
                    "45-49",
                    "50-54",
                    "55-59",
                    "60-64",
                    "65-69",
                    "70-74",
                    "75-79",
                    "80-84",
                    "85+"]

# Load population data to compare population pyramid
Data = pd.read_excel(resourcefile_demography, sheet_name='Interpolated Pop Structure')

df = Data[Data['year'] == 2015].copy()
df['agegrp'] = np.floor(df.age_to / 5)
df.loc[df.agegrp > 17, 'agegrp'] = 17
tab = df.pivot_table(values="value", index=["gender", "agegrp"], aggfunc=np.sum)
Data_Women_2015 = np.asarray(tab[tab.index.get_level_values('gender') == 'female']).flatten()
Data_Men_2015 = np.asarray(tab[tab.index.get_level_values('gender') == 'male']).flatten()

df = Data[Data['year'] == 2045].copy()
df['agegrp'] = np.floor(df.age_to / 5)
df.loc[df.agegrp > 17, 'agegrp'] = 17
tab = df.pivot_table(values="value", index=["gender", "agegrp"], aggfunc=np.sum)
Data_Women_2045 = np.asarray(tab[tab.index.get_level_values('gender') == 'female']).flatten()
Data_Men_2045 = np.asarray(tab[tab.index.get_level_values('gender') == 'male']).flatten()

# Traditional Populaiton Pyramid: Model Only
fig, axes = plt.subplots(ncols=2, nrows=2, sharey=True)
y = np.arange(len(Age_Group_Labels))
axes[0][0].barh(y, ModelOutput_Women_2015_trimmed / ModelOutput_Women_2015_trimmed.sum(),
                align='center', color='red', zorder=10)
axes[0][0].set(title='Women, 2015')
axes[0][1].barh(y, ModelOutput_Men_2015_trimmed / ModelOutput_Men_2015_trimmed.sum(),
                align='center', color='blue', zorder=10)
axes[0][1].set(title='Men, 2015')
axes[1][0].barh(y, ModelOutput_Women_2045_trimmed / ModelOutput_Women_2045_trimmed.sum(),
                align='center', color='red', zorder=10)
axes[1][0].set(title='Women, 2045')
axes[1][1].barh(y, ModelOutput_Men_2045_trimmed / ModelOutput_Men_2045_trimmed.sum(),
                align='center', color='blue', zorder=10)
axes[1][1].set(title='Men, 2045')
axes[0][0].invert_xaxis()
axes[0][0].set(yticks=y, yticklabels=Age_Group_Labels)
axes[0][0].yaxis.tick_right()
axes[1][0].invert_xaxis()
axes[1][0].set(yticks=y, yticklabels=Age_Group_Labels)
axes[1][0].yaxis.tick_right()

for ax in axes.flat:
    ax.margins(0.03)
    ax.grid(True)

fig.tight_layout()
fig.subplots_adjust(wspace=0.09)
plt.savefig(outputpath + 'PopPyramidModelOnly' + datestamp + '.pdf')
plt.show()

# Model Vs Data Pop Pyramid

fig, axes = plt.subplots(ncols=2, nrows=2, sharey=True)
y = np.arange(len(Age_Group_Labels))
axes[0][0].plot(y, ModelOutput_Women_2015_trimmed / ModelOutput_Women_2015_trimmed.sum())
axes[0][0].plot(y, Data_Women_2015 / Data_Women_2015.sum())
axes[0][0].set(title='Women, 2015')
axes[0][0].legend(['Model', 'Data'])
axes[0][1].plot(y, ModelOutput_Men_2015_trimmed / ModelOutput_Men_2015_trimmed.sum())
axes[0][1].plot(y, Data_Men_2015.flatten() / Data_Men_2015.flatten().sum())
axes[0][1].set(title='Men, 2015')
axes[1][0].plot(y, ModelOutput_Women_2045_trimmed / ModelOutput_Women_2045_trimmed.sum())
axes[1][0].plot(y, Data_Women_2045.flatten() / Data_Women_2045.flatten().sum())
axes[1][0].set(title='Women, 2045')
axes[1][1].plot(y, ModelOutput_Men_2045_trimmed / ModelOutput_Men_2045_trimmed.sum())
axes[1][1].plot(y, Data_Men_2045.flatten() / Data_Men_2045.flatten().sum())
axes[1][1].set(title='Men, 2045')
axes[1][0].set(xticks=y, xticklabels=Age_Group_Labels)
axes[1][1].set(xticks=y, xticklabels=Age_Group_Labels)

for ax in axes.flat:
    ax.margins(0.03)
    ax.grid(True)

fig.tight_layout()
fig.subplots_adjust(wspace=0.09)
plt.savefig(outputpath + 'PopPyramid_ModelVsData' + datestamp + '.pdf')
plt.show()


# %% Plots births ....

births_df = output['tlo.methods.demography']['on_birth']

plt.plot_date(births_df['date'], births_df['mother_age'])
plt.xlabel('Year')
plt.ylabel('Age of Mother')
plt.savefig(outputpath + 'Births' + datestamp + '.pdf')
plt.show()


# %% Plots deaths ...

deaths_df = output['tlo.methods.demography']['death']

plt.plot_date(deaths_df['date'], deaths_df['age'])
plt.xlabel('Year')
plt.ylabel('Age at Death')
plt.savefig(outputpath + 'Deaths' + datestamp + '.pdf')
plt.show()