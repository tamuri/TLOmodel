"""
TB infections
"""
import os

import pandas as pd

from tlo import DateOffset, Module, Parameter, Property, Types, logging
from tlo.events import Event, IndividualScopeEventMixin, PopulationScopeEventMixin, RegularEvent
from tlo.methods import Metadata, demography
from tlo.methods.healthsystem import HSI_Event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class tb(Module):
    """ Set up the baseline population with TB prevalence
    """

    def __init__(self, name=None, resourcefilepath=None):
        super().__init__(name)
        self.resourcefilepath = resourcefilepath

    # Declare Metadata
    METADATA = {
        Metadata.DISEASE_MODULE,
        Metadata.USES_SYMPTOMMANAGER,
        Metadata.USES_HEALTHSYSTEM,
        Metadata.USES_HEALTHBURDEN
    }

    PARAMETERS = {
        'prop_fast_progressor': Parameter(Types.REAL,
                                          'Proportion of infections that progress directly to active stage'),
        'transmission_rate': Parameter(Types.REAL, 'TB transmission rate, estimated by Juan'),
        'monthly_prob_progr_active': Parameter(Types.REAL,
                                               'Combined rate of progression/reinfection/relapse from Juan'),
        'rr_tb_hiv_stages': Parameter(Types.REAL, 'relative risk of tb in hiv+ compared with hiv- by cd4 stage'),
        'rr_tb_art': Parameter(Types.REAL, 'relative risk of tb in hiv+ on art'),
        'rr_tb_ipt': Parameter(Types.REAL, 'relative risk of tb on ipt'),
        'rr_tb_malnourished': Parameter(Types.REAL, 'relative risk of tb with malnourishment'),
        'rr_tb_diabetes1': Parameter(Types.REAL, 'relative risk of tb with diabetes type 1'),
        'rr_tb_alcohol': Parameter(Types.REAL, 'relative risk of tb with heavy alcohol use'),
        'rr_tb_smoking': Parameter(Types.REAL, 'relative risk of tb with smoking'),
        'rr_tb_pollution': Parameter(Types.REAL, 'relative risk of tb with indoor air pollution'),
        'rel_infectiousness_hiv': Parameter(Types.REAL, 'relative infectiousness of tb in hiv+ compared with hiv-'),
        'monthly_prob_self_cure': Parameter(Types.REAL, 'annual probability of self-cure'),
        'monthly_prob_tb_mortality': Parameter(Types.REAL, 'mortality rate with active tb'),
        'monthly_prob_tb_mortality_hiv': Parameter(Types.REAL, 'mortality from tb with concurrent HIV'),
        'monthly_prob_relapse_tx_complete': Parameter(Types.REAL,
                                                      'annual probability of relapse once treatment complete'),
        'monthly_prob_relapse_tx_incomplete': Parameter(Types.REAL,
                                                        'annual probability of relapse if treatment incomplete'),
        'monthly_prob_relapse_2yrs': Parameter(Types.REAL,
                                               'annual probability of relapse 2 years after treatment complete'),
        'prob_treatment_success': Parameter(Types.REAL,
                                            'probability of treatment completion'),

        'prop_mdr2010': Parameter(Types.REAL, 'prevalence of mdr in TB cases 2010'),
        'prop_mdr_new': Parameter(Types.REAL, 'prevalence of mdr in new tb cases'),
        'prop_mdr_retreated': Parameter(Types.REAL, 'prevalence of mdr in previously treated cases'),
        'tb_testing_coverage': Parameter(Types.REAL, 'proportion of population tested'),
        'prop_smear_positive': Parameter(Types.REAL, 'proportion of TB cases smear positive'),
        'prop_smear_positive_hiv': Parameter(Types.REAL, 'proportion of HIV/TB cases smear positive'),

        'followup_times': Parameter(Types.INT, 'times(weeks) tb treatment monitoring required after tx start'),

        # daly weights, no daly weight for latent tb
        'daly_wt_susc_tb':
            Parameter(Types.REAL, 'Drug-susecptible tuberculosis, not HIV infected'),
        'daly_wt_resistant_tb':
            Parameter(Types.REAL, 'multidrug-resistant tuberculosis, not HIV infected'),
        'daly_wt_susc_tb_hiv_severe_anaemia':
            Parameter(Types.REAL, '# Drug-susecptible Tuberculosis, HIV infected and anemia, severe'),
        'daly_wt_susc_tb_hiv_moderate_anaemia':
            Parameter(Types.REAL, 'Drug-susecptible Tuberculosis, HIV infected and anemia, moderate'),
        'daly_wt_susc_tb_hiv_mild_anaemia':
            Parameter(Types.REAL, 'Drug-susecptible Tuberculosis, HIV infected and anemia, mild'),
        'daly_wt_susc_tb_hiv':
            Parameter(Types.REAL, 'Drug-susecptible Tuberculosis, HIV infected'),
        'daly_wt_resistant_tb_hiv_severe_anaemia':
            Parameter(Types.REAL, 'Multidrug resistant Tuberculosis, HIV infected and anemia, severe'),
        'daly_wt_resistant_tb_hiv':
            Parameter(Types.REAL, 'Multidrug resistant Tuberculosis, HIV infected'),
        'daly_wt_resistant_tb_hiv_moderate_anaemia':
            Parameter(Types.REAL, 'Multidrug resistant Tuberculosis, HIV infected and anemia, moderate'),
        'daly_wt_resistant_tb_hiv_mild_anaemia':
            Parameter(Types.REAL, 'Multidrug resistant Tuberculosis, HIV infected and anemia, mild'),
    }

    PROPERTIES = {
        'tb_inf': Property(Types.CATEGORICAL,
                           categories=['uninfected',
                                       'latent_susc_primary', 'active_susc_primary',
                                       'latent_susc_secondary', 'active_susc_secondary',
                                       'latent_mdr_primary', 'active_mdr_primary',
                                       'latent_mdr_secondary', 'active_mdr_secondary'],
                           description='tb status'),
        'tb_date_active': Property(Types.DATE, 'Date active tb started'),
        'tb_date_latent': Property(Types.DATE, 'Date acquired tb infection (latent stage)'),
        'tb_ever_tb': Property(Types.BOOL, 'if ever had active drug-susceptible tb'),
        'tb_ever_tb_mdr': Property(Types.BOOL, 'if ever had active multi-drug resistant tb'),
        'tb_specific_symptoms': Property(Types.CATEGORICAL, 'Level of symptoms for tb',
                                         categories=['none', 'latent', 'active']),
        'tb_unified_symptom_code': Property(Types.CATEGORICAL, 'level of symptoms on the standardised scale, 0-4',
                                            categories=[0, 1, 2, 3, 4]),
        'tb_ever_tested': Property(Types.BOOL, 'ever had a tb test'),
        'tb_smear_test': Property(Types.BOOL, 'ever had a tb smear test'),
        'tb_result_smear_test': Property(Types.BOOL, 'result from tb smear test'),
        'tb_date_smear_test': Property(Types.DATE, 'date of tb smear test'),
        'tb_xpert_test': Property(Types.BOOL, 'ever had a tb Xpert test'),
        'tb_result_xpert_test': Property(Types.BOOL, 'result from tb Xpert test'),
        'tb_date_xpert_test': Property(Types.DATE, 'date of tb Xpert test'),
        'tb_diagnosed': Property(Types.BOOL, 'current diagnosis of active tb'),
        'tb_mdr_diagnosed': Property(Types.BOOL, 'current diagnosis of active tb_mdr'),
        'tb_on_treatment': Property(Types.BOOL, 'on tb treatment regimen'),
        'tb_date_treated': Property(Types.DATE, 'date tb treatment started'),
        'tb_treatment_failure': Property(Types.BOOL, 'failed first line tb treatment'),
        'tb_treated_mdr': Property(Types.BOOL, 'on tb treatment MDR regimen'),
        'tb_date_treated_mdr': Property(Types.DATE, 'date tb MDR treatment started'),
        'tb_request_mdr_regimen': Property(Types.BOOL, 'request for mdr treatment'),
        'tb_on_ipt': Property(Types.BOOL, 'if currently on ipt'),
        'tb_date_ipt': Property(Types.DATE, 'date ipt started'),
        'tb_date_death': Property(Types.DATE, 'date of death from tb')
    }

    def read_parameters(self, data_folder):

        workbook = pd.read_excel(os.path.join(self.resourcefilepath,
                                              'ResourceFile_TB.xlsx'), sheet_name=None)

        params = self.parameters
        params['param_list'] = workbook['parameters']
        self.param_list.set_index("parameter", inplace=True)

        params['prop_fast_progressor'] = self.param_list.loc['prop_fast_progressor', 'value1']
        params['transmission_rate'] = self.param_list.loc['transmission_rate', 'value1']
        params['monthly_prob_progr_active'] = self.param_list.loc['monthly_prob_progr_active', 'value1']

        params['rr_tb_with_hiv_stages'] = self.param_list.loc['transmission_rate'].values
        params['rr_tb_art'] = self.param_list.loc['rr_tb_art', 'value1']
        params['rr_tb_ipt'] = self.param_list.loc['rr_tb_ipt', 'value1']
        params['rr_tb_malnourished'] = self.param_list.loc['rr_tb_malnourished', 'value1']
        params['rr_tb_diabetes1'] = self.param_list.loc['rr_tb_diabetes1', 'value1']
        params['rr_tb_alcohol'] = self.param_list.loc['rr_tb_alcohol', 'value1']
        params['rr_tb_smoking'] = self.param_list.loc['rr_tb_smoking', 'value1']
        params['rr_tb_pollution'] = self.param_list.loc['rr_tb_pollution', 'value1']
        params['rel_infectiousness_hiv'] = self.param_list.loc['rel_infectiousness_hiv', 'value1']
        params['monthly_prob_self_cure'] = self.param_list.loc['monthly_prob_self_cure', 'value1']
        params['monthly_prob_tb_mortality'] = self.param_list.loc['monthly_prob_tb_mortality', 'value1']
        params['monthly_prob_tb_mortality_hiv'] = self.param_list.loc['monthly_prob_tb_mortality_hiv', 'value1']
        params['prop_mdr2010'] = self.param_list.loc['prop_mdr2010', 'value1']
        params['prop_mdr_new'] = self.param_list.loc['prop_mdr_new', 'value1']
        params['prop_mdr_retreated'] = self.param_list.loc['prop_mdr_retreated', 'value1']
        params['monthly_prob_relapse_tx_complete'] = self.param_list.loc['monthly_prob_relapse_tx_complete', 'value1']
        params['monthly_prob_relapse_tx_incomplete'] = self.param_list.loc[
            'monthly_prob_relapse_tx_incomplete', 'value1']
        params['monthly_prob_relapse_2yrs'] = self.param_list.loc['monthly_prob_relapse_2yrs', 'value1']
        params['prob_treatment_success'] = self.param_list.loc['prob_treatment_success', 'value1']

        params['Active_tb_prob'], params['Latent_tb_prob'] = workbook['Active_TB_prob'], workbook['Latent_TB_prob']

        params['prop_smear_positive'] = self.param_list.loc['prop_smear_positive', 'value1']
        params['prop_smear_positive_hiv'] = self.param_list.loc['prop_smear_positive_hiv', 'value1']

        params['followup_times'] = workbook['followup']

        # get the DALY weight that this module will use from the weight database
        if 'HealthBurden' in self.sim.modules.keys():
            params['daly_wt_susc_tb'] = self.sim.modules['HealthBurden'].get_daly_weight(
                0)  # Drug-susecptible tuberculosis, not HIV infected
            params['daly_wt_resistant_tb'] = self.sim.modules['HealthBurden'].get_daly_weight(
                1)  # multidrug-resistant tuberculosis, not HIV infected
            params['daly_wt_susc_tb_hiv_severe_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                4)  # Drug-susecptible Tuberculosis, HIV infected and anemia, severe
            params['daly_wt_susc_tb_hiv_moderate_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                5)  # Drug-susecptible Tuberculosis, HIV infected and anemia, moderate
            params['daly_wt_susc_tb_hiv_mild_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                6)  # Drug-susecptible Tuberculosis, HIV infected and anemia, mild
            params['daly_wt_susc_tb_hiv'] = self.sim.modules['HealthBurden'].get_daly_weight(
                7)  # Drug-susecptible Tuberculosis, HIV infected
            params['daly_wt_resistant_tb_hiv_severe_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                8)  # Multidrug resistant Tuberculosis, HIV infected and anemia, severe
            params['daly_wt_resistant_tb_hiv'] = self.sim.modules['HealthBurden'].get_daly_weight(
                9)  # Multidrug resistant Tuberculosis, HIV infected
            params['daly_wt_resistant_tb_hiv_moderate_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                10)  # Multidrug resistant Tuberculosis, HIV infected and anemia, moderate
            params['daly_wt_resistant_tb_hiv_mild_anaemia'] = self.sim.modules['HealthBurden'].get_daly_weight(
                11)  # Multidrug resistant Tuberculosis, HIV infected and anemia, mild

    # TODO check malawi clinical guidelines to treatments available
    def initialise_population(self, population):
        """Set our property values for the initial population.
        """
        df = population.props
        now = self.sim.date

        # set-up baseline population
        df['tb_inf'].values[:] = 'uninfected'
        df['tb_date_active'] = pd.NaT
        df['tb_date_latent'] = pd.NaT

        df['tb_ever_tb'] = False
        df['tb_ever_tb_mdr'] = False

        df['tb_specific_symptoms'].values[:] = 'none'
        df['tb_unified_symptom_code'].values[:] = 0

        df['tb_ever_tested'] = False  # default: no individuals tested
        df['tb_smear_test'] = False
        df['tb_result_smear_test'] = False
        df['tb_date_smear_test'] = pd.NaT
        df['tb_xpert_test'] = False
        df['tb_result_xpert_test'] = False
        df['tb_date_xpert_test'] = pd.NaT
        df['tb_diagnosed'] = False
        df['tb_mdr_diagnosed'] = False
        df['tb_on_treatment'] = False
        df['tb_date_treated'] = pd.NaT
        df['tb_treatment_failure'] = False
        df['tb_treated_mdr'] = False
        df['tb_date_treated_mdr'] = pd.NaT
        df['tb_request_mdr_regimen'] = False
        df['tb_on_ipt'] = False
        df['tb_date_ipt'] = pd.NaT
        df['tb_date_death'] = pd.NaT

        # TB infections - active / latent
        # baseline infections not weighted by RR, randomly assigned
        active_tb_data = self.parameters['Active_tb_prob']
        latent_tb_data = self.parameters['Latent_tb_prob']

        active_tb_prob_year = active_tb_data.loc[
            active_tb_data.Year == now.year, ['ages', 'Sex', 'incidence_per_capita']]

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~ LATENT ~~~~~~~~~~~~~~~~~~~~~~~~~~

        # merge all susceptible individuals with their hiv probability based on sex and age
        df_tbprob = df.merge(latent_tb_data, left_on=['age_years', 'sex'],
                             right_on=['age', 'sex'],
                             how='left')

        # fill missing values with 0 (only relevant for age 80+)
        df_tbprob['prob_latent_tb'] = df_tbprob['prob_latent_tb'].fillna(0)

        assert df_tbprob.prob_latent_tb.isna().sum() == 0  # check there is a probability for every individual

        # get a list of random numbers between 0 and 1 for each infected individual
        random_draw = self.rng.random_sample(size=len(df_tbprob))

        tb_idx = df_tbprob.index[df.is_alive & (df_tbprob.prob_latent_tb > random_draw)]
        df.loc[tb_idx, 'tb_inf'] = 'latent_susc_primary'
        df.loc[tb_idx, 'tb_date_latent'] = now
        df.loc[tb_idx, 'tb_specific_symptoms'] = 'latent'
        df.loc[tb_idx, 'tb_unified_symptom_code'] = 0

        # allocate some latent infections as mdr-tb
        if len(df[df.is_alive & (df.tb_inf == 'latent_susc_primary')]) > 10:
            idx_c = df[df.is_alive & (df.tb_inf == 'latent_susc_primary')].sample(
                frac=self.parameters['prop_mdr2010'], random_state=self.rng).index

            df.loc[idx_c, 'tb_inf'] = 'latent_mdr_primary'  # change to mdr-tb
            df.loc[idx_c, 'tb_specific_symptoms'] = 'latent'

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~ ACTIVE ~~~~~~~~~~~~~~~~~~~~~~~~~~

        # select probability of active infection
        # same for all ages and sex so pick value for M age 0
        frac_active_tb = active_tb_prob_year.loc[
            (active_tb_prob_year.Sex == 'M') & (active_tb_prob_year.ages == 0), 'incidence_per_capita']

        active = df[df.is_alive & (df.tb_inf == 'uninfected')].sample(frac=frac_active_tb, random_state=self.rng).index
        # print(active)
        df.loc[active, 'tb_inf'] = 'active_susc_primary'
        df.loc[active, 'tb_date_active'] = now
        df.loc[active, 'tb_specific_symptoms'] = 'active'
        df.loc[tb_idx, 'tb_unified_symptom_code'] = 2

        # allocate some active infections as mdr-tb
        if len(active) > 10:
            idx_c = df[df.is_alive & (df.tb_inf == 'active_susc_primary')].sample(
                frac=self.parameters['prop_mdr2010'], random_state=self.rng).index

            df.loc[idx_c, 'tb_inf'] = 'active_mdr_primary'
            df.loc[idx_c, 'tb_specific_symptoms'] = 'active'

    def initialise_simulation(self, sim):
        sim.schedule_event(TbEvent(self), sim.date + DateOffset(months=12))
        sim.schedule_event(TbActiveEvent(self), sim.date + DateOffset(months=12))
        sim.schedule_event(TbSelfCureEvent(self), sim.date + DateOffset(months=12))

        sim.schedule_event(TbMdrEvent(self), sim.date + DateOffset(months=12))
        sim.schedule_event(TbMdrActiveEvent(self), sim.date + DateOffset(months=12))
        sim.schedule_event(TbMdrSelfCureEvent(self), sim.date + DateOffset(months=12))

        sim.schedule_event(TbDeathEvent(self), sim.date + DateOffset(months=12))

        # Logging
        sim.schedule_event(TbLoggingEvent(self), sim.date + DateOffset(days=0))

    def on_birth(self, mother_id, child_id):
        """Initialise our properties for a newborn individual.
        """
        df = self.sim.population.props

        df.at[child_id, 'tb_inf'] = 'uninfected'
        df.at[child_id, 'tb_date_active'] = pd.NaT
        df.at[child_id, 'tb_date_latent'] = pd.NaT
        df.at[child_id, 'tb_ever_tb'] = False
        df.at[child_id, 'tb_ever_tb_mdr'] = False
        df.at[child_id, 'tb_specific_symptoms'] = 'none'
        df.at[child_id, 'tb_unified_symptom_code'] = 0

        df.at[child_id, 'tb_ever_tested'] = False  # default: no individuals tested
        df.at[child_id, 'tb_smear_test'] = False
        df.at[child_id, 'tb_result_smear_test'] = False
        df.at[child_id, 'tb_date_smear_test'] = pd.NaT
        df.at[child_id, 'tb_xpert_test'] = False
        df.at[child_id, 'tb_result_xpert_test'] = False
        df.at[child_id, 'tb_date_xpert_test'] = pd.NaT
        df.at[child_id, 'tb_diagnosed'] = False
        df.at[child_id, 'tb_mdr_diagnosed'] = False
        df.at[child_id, 'tb_on_treatment'] = False
        df.at[child_id, 'tb_date_treated'] = pd.NaT
        df.at[child_id, 'tb_treatment_failure'] = False
        df.at[child_id, 'tb_treated_mdr'] = False
        df.at[child_id, 'tb_date_treated_mdr'] = pd.NaT
        df.at[child_id, 'tb_request_mdr_regimen'] = False
        df.at[child_id, 'tb_on_ipt'] = False
        df.at[child_id, 'tb_date_ipt'] = pd.NaT

    # TODO: complete this
    def on_hsi_alert(self, person_id, treatment_id):
        """
        This is called whenever there is an HSI event commissioned by one of the other disease modules.
        """

        logger.debug('This is TB, being alerted about a health system interaction '
                     'person %d for: %s', person_id, treatment_id)

        if treatment_id == 'Tb_screening':
            piggy_back_dx_at_appt = HSI_TbScreening(self, person_id)
            piggy_back_dx_at_appt.TREATMENT_ID = 'ChronicSyndrome_PiggybackAppt'

            # Arbitrarily reduce the size of appt footprint to reflect that this is a piggy back appt
            for key in piggy_back_dx_at_appt.EXPECTED_APPT_FOOTPRINT:
                piggy_back_dx_at_appt.EXPECTED_APPT_FOOTPRINT[key] = piggy_back_dx_at_appt.EXPECTED_APPT_FOOTPRINT[
                                                                         key] * 0.25

            self.sim.modules['HealthSystem'].schedule_hsi_event(piggy_back_dx_at_appt,
                                                                priority=0,
                                                                topen=self.sim.date,
                                                                tclose=None)

    # TODO include all DALY weights and map to more levels of specific symptoms
    def report_daly_values(self):
        # This must send back a pd.Series or pd.DataFrame that reports on the average daly-weights that have been
        # experienced by persons in the previous month. Only rows for alive-persons must be returned.
        # The names of the series of columns is taken to be the label of the cause of this disability.
        # It will be recorded by the healthburden module as <ModuleName>_<Cause>.
        # TODO: add co-infection hiv/tb
        logger.debug('This is tb reporting my health values')

        df = self.sim.population.props  # shortcut to population properties dataframe
        params = self.parameters

        health_values = df.loc[df.is_alive, 'tb_specific_symptoms'].map({
            'none': 0,
            'latent': 0,
            'active': params['daly_wt_susc_tb']
        })
        health_values.name = 'tb Symptoms'  # label the cause of this disability

        return health_values.loc[df.is_alive]


# ---------------------------------------------------------------------------
#   TB infection event
# ---------------------------------------------------------------------------

class TbEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb infection events
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date
        rng = self.module.rng

        df = population.props

        # ----------------------------------- FORCE OF INFECTION -----------------------------------

        # apply a force of infection to produce new latent cases
        # no age distribution for FOI but the relative risks would affect distribution of active infections
        active_hiv_neg = len(df[df['tb_inf'].str.contains('active_susc') & ~df.hv_inf & df.is_alive])

        active_hiv_pos = len(df[df['tb_inf'].str.contains('active_susc') & df.hv_inf & df.is_alive])

        # population at-risk = uninfected (new infection), latent_mdr (primary & secondary)
        uninfected_total = len(df[~df['tb_inf'].str.contains('active_susc') & df.is_alive])
        total_population = len(df[df.is_alive])

        force_of_infection = (params['transmission_rate'] * active_hiv_neg * (active_hiv_pos * params[
            'rel_infectiousness_hiv']) * uninfected_total) / total_population
        # print('force_of_infection: ', force_of_infection)

        # ----------------------------------- NEW INFECTIONS -----------------------------------

        # pop at risk = uninfected only
        at_risk = df[(df.tb_inf == 'uninfected') & df.is_alive].index

        #  no age/sex effect on risk of latent infection
        prob_tb_new = pd.Series(force_of_infection, index=at_risk)
        # print('prob_tb_new: ', prob_tb_new)

        is_newly_infected = prob_tb_new > rng.rand(len(prob_tb_new))
        new_case = is_newly_infected[is_newly_infected].index
        df.loc[new_case, 'tb_inf'] = 'latent_susc_primary'
        df.loc[new_case, 'tb_date_latent'] = now
        df.loc[new_case, 'tb_specific_symptoms'] = 'latent'
        df.loc[new_case, 'tb_unified_symptom_code'] = 0

        # ----------------------------------- RE-INFECTIONS -----------------------------------

        # pop at risk = latent_susc_secondary and latent_mdr (primary & secondary)
        at_risk = df[
            (df.tb_inf == 'latent_susc_secondary') | df['tb_inf'].str.contains('latent_mdr') & df.is_alive].index

        #  no age/sex effect on risk of latent infection
        prob_tb_new = pd.Series(force_of_infection, index=at_risk)
        # print('prob_tb_new: ', prob_tb_new)

        repeat_infected = prob_tb_new > rng.rand(len(prob_tb_new))
        repeat_case = repeat_infected[repeat_infected].index

        # unchanged status, high risk of relapse as if just recovered
        df.loc[repeat_case, 'tb_inf'] = 'latent_susc_secondary'

        df.loc[repeat_case, 'tb_date_latent'] = now
        df.loc[repeat_case, 'tb_specific_symptoms'] = 'latent'
        df.loc[repeat_case, 'tb_unified_symptom_code'] = 0


class TbActiveEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb progression from latent to active infection
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date
        rng = self.module.rng

        df = population.props
        # ----------------------------------- FAST PROGRESSORS TO ACTIVE DISEASE -----------------------------------

        # if any newly infected latent cases, 14% become active directly, only for primary infection
        new_latent = df[
            (df.tb_inf == 'latent_susc_primary') & (df.tb_date_latent == now) & ~df.tb_on_ipt & df.is_alive].sum()
        # print(new_latent)

        if new_latent.any():
            fast_progression = df[
                (df.tb_inf == 'latent_susc_primary') & (df.tb_date_latent == now) & df.is_alive].sample(
                frac=params['prop_fast_progressor'], random_state=self.module.rng).index
            df.loc[fast_progression, 'tb_inf'] = 'active_susc_primary'
            df.loc[fast_progression, 'tb_date_active'] = now
            df.loc[fast_progression, 'tb_ever_tb'] = True
            df.loc[fast_progression, 'tb_specific_symptoms'] = 'active'
            df.loc[fast_progression, 'tb_unified_symptom_code'] = 2

            # ----------------------------------- FAST PROGRESSORS SEEKING CARE -----------------------------------

            # for each person determine whether they will seek care on symptom change
            # get_prob_seek_care will be the healthcare seeking function developed by Wingston
            seeks_care = pd.Series(data=False, index=df.loc[fast_progression].index)
            for i in df.index[fast_progression]:
                prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
                seeks_care[i] = self.module.rng.rand() < prob

            # if seeks_care.sum() > 0:
            #     for person_index in seeks_care.index[seeks_care]:
            #         logger.debug(
            #             'This is TbActiveEvent, scheduling HSI_Tb_SputumTest for person %d',
            #             person_index)
            #         event = HSI_Tb_SputumTest(self.module, person_id=person_index)
            #         self.sim.modules['HealthSystem'].schedule_event(event,
            #                                                         priority=2,
            #                                                         topen=self.sim.date,
            #                                                         tclose=self.sim.date + DateOffset(weeks=2)
            #                                                         )
            # else:
            #     logger.debug(
            #         'This is TbActiveEvent, There is  no one with new active disease so no new healthcare seeking')

        # ----------------------------------- SLOW PROGRESSORS TO ACTIVE DISEASE -----------------------------------

        # slow progressors with latent TB become active
        # random sample with weights for RR of active disease
        # TODO HIV+ on ART should have same progression rates as HIV-
        eff_prob_active_tb = pd.Series(0, index=df.index)
        eff_prob_active_tb.loc[(df.tb_inf == 'latent_susc_primary') & ~df.tb_on_ipt] = params[
            'monthly_prob_progr_active']
        # print('eff_prob_active_tb: ', eff_prob_active_tb)

        hiv_stage1 = df.index[df.hv_inf & (df.tb_inf == 'latent_susc_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 3.33)]
        # print('hiv_stage1', hiv_stage1)

        hiv_stage2 = df.index[df.hv_inf & (df.tb_inf == 'latent_susc_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 3.33) &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 6.67)]
        # print('hiv_stage2', hiv_stage2)

        hiv_stage3 = df.index[df.hv_inf & (df.tb_inf == 'latent_susc_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 6.67) &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 10)]
        # print('hiv_stage3', hiv_stage3)

        hiv_stage4 = df.index[df.hv_inf & (df.tb_inf == 'latent_susc_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 10)]
        # print('hiv_stage4', hiv_stage4)

        eff_prob_active_tb.loc[hiv_stage1] *= params['rr_tb_with_hiv_stages'][0]
        eff_prob_active_tb.loc[hiv_stage2] *= params['rr_tb_with_hiv_stages'][1]
        eff_prob_active_tb.loc[hiv_stage3] *= params['rr_tb_with_hiv_stages'][2]
        eff_prob_active_tb.loc[hiv_stage4] *= params['rr_tb_with_hiv_stages'][3]
        eff_prob_active_tb.loc[df.hv_on_art == 2] *= params['rr_tb_art']
        # eff_prob_active_tb.loc[df.is_malnourished] *= params['rr_tb_malnourished']
        # eff_prob_active_tb.loc[df.has_diabetes1] *= params['rr_tb_diabetes1']
        # eff_prob_active_tb.loc[df.high_alcohol] *= params['rr_tb_alcohol']
        # eff_prob_active_tb.loc[df.is_smoker] *= params['rr_tb_smoking']
        # eff_prob_active_tb.loc[df.high_pollution] *= params['rr_tb_pollution']

        prog_to_active = eff_prob_active_tb > rng.rand(len(eff_prob_active_tb))
        # print('prog_to_active: ', prog_to_active )
        new_active_case = prog_to_active[prog_to_active].index
        # print('new_active_case: ', new_active_case)
        df.loc[new_active_case, 'tb_inf'] = 'active_susc_primary'
        df.loc[new_active_case, 'tb_date_active'] = now
        df.loc[new_active_case, 'tb_ever_tb'] = True
        df.loc[new_active_case, 'tb_specific_symptoms'] = 'active'
        df.loc[new_active_case, 'tb_unified_symptom_code'] = 2

        # ----------------------------------- SLOW PROGRESSORS SEEKING CARE -----------------------------------

        # for each person determine whether they will seek care on symptom change
        # get_prob_seek_care will be the healthcare seeking function developed by Wingston
        seeks_care = pd.Series(data=False, index=df.loc[new_active_case].index)
        for i in df.index[new_active_case]:
            prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
            seeks_care[i] = self.module.rng.rand() < prob

        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbActiveEvent, scheduling HSI_Tb_SputumTest for person %d',
        #             person_index)
        #         event = HSI_Tb_SputumTest(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbActiveEvent, There is  no one with new active disease so no new healthcare seeking')

        # ----------------------------------- RELAPSE -----------------------------------
        random_draw = self.module.rng.random_sample(size=len(df))

        # relapse after treatment completion, tb_date_treated + six months
        relapse_tx_complete = df[
            (df.tb_inf == 'latent_susc_secondary') & ~df.tb_on_ipt & df.is_alive & (
                self.sim.date - df.tb_date_treated > pd.to_timedelta(182.625, unit='d')) & (
                self.sim.date - df.tb_date_treated < pd.to_timedelta(732.5, unit='d')) & ~df.tb_treatment_failure & (
                random_draw < params['monthly_prob_relapse_tx_complete'])].index

        # relapse after treatment default, tb_treatment_failure=True, but make sure not tb-mdr
        relapse_tx_incomplete = df[
            (df.tb_inf == 'latent_susc_secondary') & ~df.tb_on_ipt & df.is_alive & df.tb_treatment_failure & (
                self.sim.date - df.tb_date_treated > pd.to_timedelta(182.625, unit='d')) & (
                self.sim.date - df.tb_date_treated < pd.to_timedelta(732.5, unit='d')) & (
                random_draw < params['monthly_prob_relapse_tx_incomplete'])].index

        # relapse after >2 years following completion of treatment (or default)
        # use tb_date_treated + 2 years + 6 months of treatment
        relapse_tx_2yrs = df[
            (df.tb_inf == 'latent_susc_secondary') & ~df.tb_on_ipt & df.is_alive & (
                self.sim.date - df.tb_date_treated >= pd.to_timedelta(732.5, unit='d')) & (
                random_draw < params['monthly_prob_relapse_2yrs'])].index

        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_inf'] = 'active_susc_secondary'
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_date_active'] = now
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_ever_tb'] = True
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_specific_symptoms'] = 'active'
        df.loc[relapse_tx_complete | relapse_tx_incomplete, 'tb_unified_symptom_code'] = 2

        # ----------------------------------- RELAPSE CASES SEEKING CARE -----------------------------------

        # relapse after complete treatment course - refer for xpert testing
        seeks_care = pd.Series(data=False, index=df.loc[relapse_tx_complete].index)
        for i in df.loc[relapse_tx_complete].index:
            prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
            seeks_care[i] = self.module.rng.rand() < prob

        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbActiveEvent, scheduling HSI_Tb_XpertTest for person %d',
        #             person_index)
        #         event = HSI_Tb_XpertTest(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbActiveEvent, There is  no one with new active disease so no new healthcare seeking')
        #
        # # relapse after incomplete treatment course - repeat treatment course
        # seeks_care = pd.Series(data=False, index=df.loc[relapse_tx_incomplete].index)
        # for i in df.loc[relapse_tx_incomplete].index:
        #     prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
        #     seeks_care[i] = self.module.rng.rand() < prob
        #
        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbActiveEvent, scheduling HSI_Tb_StartTreatment for person %d',
        #             person_index)
        #         event = HSI_Tb_StartTreatment(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbActiveEvent, There is  no one with new active disease so no new healthcare seeking')


class TbSelfCureEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb self-cure events
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date
        rng = self.module.rng

        df = population.props

        # self-cure - move from active to latent_secondary, make sure it's not the ones that just became active
        random_draw = rng.random_sample(size=len(df))

        self_cure = df[
            df['tb_inf'].str.contains('active_susc') & df.is_alive & (
                df.tb_date_active < now) & (random_draw < params['monthly_prob_self_cure'])].index
        df.loc[self_cure, 'tb_inf'] = 'latent_susc_secondary'
        df.loc[self_cure, 'tb_specific_symptoms'] = 'latent'
        df.loc[self_cure, 'tb_unified_symptom_code'] = 0


# ---------------------------------------------------------------------------
#   TB MDR infection event
# ---------------------------------------------------------------------------

class TbMdrEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb-mdr infection events
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date
        rng = self.module.rng

        df = population.props

        # ----------------------------------- FORCE OF INFECTION -----------------------------------

        # apply a force of infection to produce new latent cases
        # no age distribution for FOI but the relative risks would affect distribution of active infections
        active_hiv_neg = len(df[df['tb_inf'].str.contains('active_mdr') & ~df.hv_inf & df.is_alive])

        active_hiv_pos = len(df[df['tb_inf'].str.contains('active_mdr') & df.hv_inf & df.is_alive])

        # population at-risk = susceptible (new infection), latent_susc (new infection)

        uninfected_total = len(df[(df.tb_inf == 'uninfected') | df['tb_inf'].str.contains('latent_susc') & df.is_alive])
        total_population = len(df[df.is_alive])

        force_of_infection = (params['transmission_rate'] * active_hiv_neg * (active_hiv_pos * params[
            'rel_infectiousness_hiv']) * uninfected_total) / total_population
        # print('force_of_infection: ', force_of_infection)

        # ----------------------------------- NEW INFECTIONS -----------------------------------

        # pop at risk = susceptible and latent_susc, latent_mdr_primary only
        at_risk = df[(df.tb_inf == 'uninfected') & df.is_alive].index

        #  no age/sex effect on risk of latent infection
        prob_tb_new = pd.Series(force_of_infection, index=at_risk)
        # print('prob_tb_new: ', prob_tb_new)

        is_newly_infected = prob_tb_new > rng.rand(len(prob_tb_new))
        new_case = is_newly_infected[is_newly_infected].index
        df.loc[new_case, 'tb_inf'] = 'latent_mdr_primary'
        df.loc[new_case, 'tb_date_latent'] = now
        df.loc[new_case, 'tb_specific_symptoms'] = 'latent'
        df.loc[new_case, 'tb_unified_symptom_code'] = 0

        # ----------------------------------- RE-INFECTIONS -----------------------------------

        # pop at risk = latent_mdr_secondary, latent_susc (primary & secondary)
        at_risk = df[
            (df.tb_inf == 'latent_mdr_secondary') | df['tb_inf'].str.contains('latent_susc') & df.is_alive].index

        #  no age/sex effect on risk of latent infection
        prob_tb_new = pd.Series(force_of_infection, index=at_risk)
        # print('prob_tb_new: ', prob_tb_new)

        repeat_infected = prob_tb_new > rng.rand(len(prob_tb_new))
        repeat_case = repeat_infected[repeat_infected].index

        # unchanged status, high risk of relapse as if just recovered
        df.loc[repeat_case, 'tb_inf'] = 'latent_mdr_secondary'

        df.loc[repeat_case, 'tb_date_latent'] = now
        df.loc[repeat_case, 'tb_specific_symptoms'] = 'latent'
        df.loc[repeat_case, 'tb_unified_symptom_code'] = 0


class TbMdrActiveEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb-mdr progression from latent to active infection
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date
        rng = self.module.rng

        df = population.props
        # ----------------------------------- FAST PROGRESSORS TO ACTIVE DISEASE -----------------------------------

        # if any newly infected latent cases, 14% become active directly, only for primary infection
        new_latent = df[
            (df.tb_inf == 'latent_mdr_primary') & (df.tb_date_latent == now) & ~df.tb_on_ipt & df.is_alive].sum()
        # print(new_latent)

        if new_latent.any():
            fast_progression = df[
                (df.tb_inf == 'latent_mdr_primary') & (df.tb_date_latent == now) & df.is_alive].sample(
                frac=params['prop_fast_progressor'], random_state=self.module.rng).index
            df.loc[fast_progression, 'tb_inf'] = 'active_mdr_primary'
            df.loc[fast_progression, 'tb_date_active'] = now
            df.loc[fast_progression, 'tb_ever_tb'] = True
            df.loc[fast_progression, 'tb_specific_symptoms'] = 'active'
            df.loc[fast_progression, 'tb_unified_symptom_code'] = 2

            # ----------------------------------- FAST PROGRESSORS SEEKING CARE -----------------------------------

            # for each person determine whether they will seek care on symptom change
            # get_prob_seek_care will be the healthcare seeking function developed by Wingston
            seeks_care = pd.Series(data=False, index=df.loc[fast_progression].index)
            for i in df.index[fast_progression]:
                prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
                seeks_care[i] = self.module.rng.rand() < prob

            # if seeks_care.sum() > 0:
            #     for person_index in seeks_care.index[seeks_care]:
            #         logger.debug(
            #             'This is TbMdrActiveEvent, scheduling HSI_Tb_SputumTest for person %d',
            #             person_index)
            #         event = HSI_Tb_SputumTest(self.module, person_id=person_index)
            #         self.sim.modules['HealthSystem'].schedule_event(event,
            #                                                         priority=2,
            #                                                         topen=self.sim.date,
            #                                                         tclose=self.sim.date + DateOffset(weeks=2)
            #                                                         )
            # else:
            #     logger.debug(
            #         'This is TbMdrActiveEvent, There is  no one with new active disease so no new healthcare seeking')

        # ----------------------------------- SLOW PROGRESSORS TO ACTIVE DISEASE -----------------------------------

        # slow progressors with latent TB become active
        # random sample with weights for RR of active disease
        eff_prob_active_tb = pd.Series(0, index=df.index)
        eff_prob_active_tb.loc[(df.tb_inf == 'latent_mdr_primary') & ~df.tb_on_ipt] = params[
            'monthly_prob_progr_active']
        # print('eff_prob_active_tb: ', eff_prob_active_tb)

        hiv_stage1 = df.index[df.hv_inf & (df.tb_inf == 'latent_mdr_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 3.33)]
        # print('hiv_stage1', hiv_stage1)

        hiv_stage2 = df.index[df.hv_inf & (df.tb_inf == 'latent_mdr_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 3.33) &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 6.67)]
        # print('hiv_stage2', hiv_stage2)

        hiv_stage3 = df.index[df.hv_inf & (df.tb_inf == 'latent_mdr_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 6.67) &
                              (((now - df.hv_date_inf).dt.days / 365.25) < 10)]
        # print('hiv_stage3', hiv_stage3)

        hiv_stage4 = df.index[df.hv_inf & (df.tb_inf == 'latent_mdr_primary') &
                              (((now - df.hv_date_inf).dt.days / 365.25) >= 10)]
        # print('hiv_stage4', hiv_stage4)

        eff_prob_active_tb.loc[hiv_stage1] *= params['rr_tb_with_hiv_stages'][0]
        eff_prob_active_tb.loc[hiv_stage2] *= params['rr_tb_with_hiv_stages'][1]
        eff_prob_active_tb.loc[hiv_stage3] *= params['rr_tb_with_hiv_stages'][2]
        eff_prob_active_tb.loc[hiv_stage4] *= params['rr_tb_with_hiv_stages'][3]
        eff_prob_active_tb.loc[df.hv_on_art == 2] *= params['rr_tb_art']
        # eff_prob_active_tb.loc[df.is_malnourished] *= params['rr_tb_malnourished']
        # eff_prob_active_tb.loc[df.has_diabetes1] *= params['rr_tb_diabetes1']
        # eff_prob_active_tb.loc[df.high_alcohol] *= params['rr_tb_alcohol']
        # eff_prob_active_tb.loc[df.is_smoker] *= params['rr_tb_smoking']
        # eff_prob_active_tb.loc[df.high_pollution] *= params['rr_tb_pollution']

        prog_to_active = eff_prob_active_tb > rng.rand(len(eff_prob_active_tb))
        # print('prog_to_active: ', prog_to_active )
        new_active_case = prog_to_active[prog_to_active].index
        # print('new_active_case: ', new_active_case)
        df.loc[new_active_case, 'tb_inf'] = 'active_mdr_primary'
        df.loc[new_active_case, 'tb_date_active'] = now
        df.loc[new_active_case, 'tb_ever_tb'] = True
        df.loc[new_active_case, 'tb_specific_symptoms'] = 'active'
        df.loc[new_active_case, 'tb_unified_symptom_code'] = 2

        # ----------------------------------- SLOW PROGRESSORS SEEKING CARE -----------------------------------

        # for each person determine whether they will seek care on symptom change
        # get_prob_seek_care will be the healthcare seeking function developed by Wingston
        seeks_care = pd.Series(data=False, index=df.loc[new_active_case].index)
        for i in df.index[new_active_case]:
            prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
            seeks_care[i] = self.module.rng.rand() < prob

        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbMdrActiveEvent, scheduling HSI_Tb_SputumTest for person %d',
        #             person_index)
        #         event = HSI_Tb_SputumTest(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbMdrActiveEvent, There is  no one with new active disease so no new healthcare seeking')

        # ----------------------------------- RELAPSE -----------------------------------
        random_draw = rng.random_sample(size=len(df))

        # relapse after treatment completion, tb_date_treated + six months
        relapse_tx_complete = df[
            (df.tb_inf == 'latent_mdr_secondary') & ~df.tb_on_ipt & df.is_alive & (
                self.sim.date - df.tb_date_treated > pd.to_timedelta(182.625, unit='d')) & (
                self.sim.date - df.tb_date_treated < pd.to_timedelta(732.5, unit='d')) & ~df.tb_treatment_failure & (
                random_draw < params['monthly_prob_relapse_tx_complete'])].index

        # relapse after treatment default, tb_treatment_failure=True, but make sure not tb-mdr
        relapse_tx_incomplete = df[
            (df.tb_inf == 'latent_mdr_secondary') & ~df.tb_on_ipt & df.is_alive & df.tb_treatment_failure & (
                self.sim.date - df.tb_date_treated > pd.to_timedelta(182.625, unit='d')) & (
                self.sim.date - df.tb_date_treated < pd.to_timedelta(732.5, unit='d')) & (
                random_draw < params['monthly_prob_relapse_tx_incomplete'])].index

        # relapse after >2 years following completion of treatment (or default)
        # use tb_date_treated + 2 years + 6 months of treatment
        relapse_tx_2yrs = df[
            (df.tb_inf == 'latent_mdr_secondary') & ~df.tb_on_ipt & df.is_alive & (
                self.sim.date - df.tb_date_treated >= pd.to_timedelta(732.5, unit='d')) & (
                random_draw < params['monthly_prob_relapse_2yrs'])].index

        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_inf'] = 'active_mdr_secondary'
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_date_active'] = now
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_ever_tb'] = True
        df.loc[relapse_tx_complete | relapse_tx_incomplete | relapse_tx_2yrs, 'tb_specific_symptoms'] = 'active'
        df.loc[relapse_tx_complete | relapse_tx_incomplete, 'tb_unified_symptom_code'] = 2

        # ----------------------------------- RELAPSE CASES SEEKING CARE -----------------------------------

        # relapse after complete treatment course - refer for xpert testing
        seeks_care = pd.Series(data=False, index=df.loc[relapse_tx_complete].index)
        for i in df.loc[relapse_tx_complete].index:
            prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
            seeks_care[i] = self.module.rng.rand() < prob

        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbMdrActiveEvent, scheduling HSI_Tb_XpertTest for person %d',
        #             person_index)
        #         event = HSI_Tb_XpertTest(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbMdrActiveEvent, There is  no one with new active disease so no new health care seeking')
        #
        # # relapse after incomplete treatment course - repeat treatment course
        # seeks_care = pd.Series(data=False, index=df.loc[relapse_tx_incomplete].index)
        # for i in df.loc[relapse_tx_incomplete].index:
        #     prob = self.sim.modules['HealthSystem'].get_prob_seek_care(i, symptom_code=2)
        #     seeks_care[i] = self.module.rng.rand() < prob
        #
        # if seeks_care.sum() > 0:
        #     for person_index in seeks_care.index[seeks_care]:
        #         logger.debug(
        #             'This is TbMdrActiveEvent, scheduling HSI_Tb_StartTreatment for person %d',
        #             person_index)
        #         event = HSI_Tb_StartTreatment(self.module, person_id=person_index)
        #         self.sim.modules['HealthSystem'].schedule_event(event,
        #                                                         priority=2,
        #                                                         topen=self.sim.date,
        #                                                         tclose=self.sim.date + DateOffset(weeks=2)
        #                                                         )
        # else:
        #     logger.debug(
        #         'This is TbMdrActiveEvent, There is  no one with new active disease so no new health care seeking')


class TbMdrSelfCureEvent(RegularEvent, PopulationScopeEventMixin):
    """ tb-mdr self-cure events
    """

    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))  # every 1 month

    def apply(self, population):
        params = self.module.parameters
        now = self.sim.date

        df = population.props

        # self-cure - move from active to latent_secondary, make sure it's not the ones that just became active
        random_draw = self.module.rng.random_sample(size=len(df))

        self_cure = df[df['tb_inf'].str.contains('active_mdr') & df.is_alive & (
            df.tb_date_active < now) & (random_draw < params['monthly_prob_self_cure'])].index
        df.loc[self_cure, 'tb_inf'] = 'latent_mdr_secondary'
        df.loc[self_cure, 'tb_specific_symptoms'] = 'latent'
        df.loc[self_cure, 'tb_unified_symptom_code'] = 0


# ---------------------------------------------------------------------------
#   HEALTH SYSTEM INTERACTIONS
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#   Testing
# ---------------------------------------------------------------------------

class HSI_TbScreening(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event.
    It is the screening event that occurs before a sputum smear test or xpert is offered
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['Over5OPD'] = 0.5  # This requires a few minutes of an outpatient appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_Testing'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = ['hiv']

    def apply(self, person_id, squeeze_factor):
        logger.debug('This is HSI_TbScreening, a screening appointment for person %d', person_id)

        df = self.sim.population.props
        # params = self.module.parameters
        # now = self.sim.date

        # check across all disease modules if patient has: cough, fever, night sweat, weight loss
        # if any of the above conditions are present, label as presumptive tb case and request appropriate test
        if (df.at[person_id, 'tb_specific_symptoms'] == 'active') and not (df.at[person_id, 'hv_inf']):
            logger.debug("This is HSI_Tb_SputumTest scheduling xpert test for person %d", person_id)

            test = HSI_Tb_SputumTest(self.module, person_id=person_id)

            # Request the health system to give xpert test
            self.sim.modules['HealthSystem'].schedule_event(test,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        elif (df.at[person_id, 'tb_specific_symptoms'] == 'active') and (df.at[person_id, 'hv_inf']):
            logger.debug("This is HSI_Tb_SputumTest scheduling xpert test for person %d", person_id)

            test = HSI_Tb_XpertTest(self.module, person_id=person_id)

            # Request the health system to give xpert test
            self.sim.modules['HealthSystem'].schedule_event(test,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

    def did_not_run(self):
        pass


class HSI_Tb_SputumTest(HSI_Event, IndividualScopeEventMixin):
    """
    This is a sputum test for presumptive tb cases
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['ConWithDCSA'] = 1  # This requires one generic outpatient appt
        the_appt_footprint['LabTBMicro'] = 1  # This requires one lab appt for microscopy

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_SputumTest'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = ['hiv']

    def apply(self, person_id, squeeze_factor):
        logger.debug('This is HSI_Tb_SputumTest, a first appointment for person %d', person_id)

        # log the consumables being used
        # Get the consumables required
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = \
            pd.unique(
                consumables.loc[consumables['Intervention_Pkg'] == 'Microscopy Test', 'Intervention_Pkg_Code'])[
                0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

        df = self.sim.population.props
        params = self.module.parameters
        now = self.sim.date

        df.at[person_id, 'tb_ever_tested'] = True
        df.at[person_id, 'tb_smear_test'] = True
        df.at[person_id, 'tb_date_smear_test'] = now
        df.at[person_id, 'tb_result_smear_test'] = False
        df.at[person_id, 'tb_diagnosed'] = False

        # ----------------------------------- OUTCOME OF TEST -----------------------------------

        # active tb, hiv-negative
        if (df.at[person_id, 'tb_specific_symptoms'] == 'active') and not df.at[person_id, 'hv_inf']:
            diagnosed = self.module.rng.choice([True, False], size=1, p=[params['prop_smear_positive'],
                                                                         (1 - params['prop_smear_positive'])])
            if diagnosed:
                df.at[person_id, 'tb_result_smear_test'] = True
                df.at[person_id, 'tb_diagnosed'] = True

        # hiv+, 80% of smear tests will be negative - extrapulmonary
        elif (df.at[person_id, 'tb_specific_symptoms'] == 'active') and df.at[person_id, 'hv_inf']:
            diagnosed = self.module.rng.choice([True, False], size=1, p=[params['prop_smear_positive_hiv'],
                                                                         (1 - params['prop_smear_positive_hiv'])])

            if diagnosed:
                df.at[person_id, 'tb_result_smear_test'] = True
                df.at[person_id, 'tb_diagnosed'] = True

        # ----------------------------------- REFERRALS FOR SECONDARY TESTING -----------------------------------

        # remaining 20% of active cases and negative cases referred for xpert testing
        # schedule xpert testing
        if not df.at[person_id, 'tb_diagnosed']:
            logger.debug("This is HSI_Tb_SputumTest scheduling xpert test for person %d", person_id)

            secondary_test = HSI_Tb_XpertTest(self.module, person_id=person_id)

            # Request the health system to give xpert test
            self.sim.modules['HealthSystem'].schedule_event(secondary_test,
                                                            priority=1,
                                                            topen=self.sim.date + DateOffset(days=1),
                                                            tclose=None)

        # ----------------------------------- REFERRALS FOR TREATMENT -----------------------------------

        if (df.at[person_id, 'tb_diagnosed'] & (
            df.at[person_id, 'tb_inf'] == 'active_susc_primary') & (
                df.at[person_id, 'age_years'] < 15)):
            # request child treatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentChild for person %d", person_id)

            treatment = HSI_Tb_StartTreatmentChild(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date + DateOffset(days=1),
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] & (
            df.at[person_id, 'tb_inf'] == 'active_susc_primary') & (
                df.at[person_id, 'age_years'] >= 15)):
            # request adult treatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentAdult for person %d", person_id)

            treatment = HSI_Tb_StartTreatmentAdult(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date + DateOffset(days=1),
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] & (
            df.at[person_id, 'tb_inf'] == 'active_susc_secondary') & (
                df.at[person_id, 'age_years'] < 15)):
            # request child retreatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_RetreatmentChild for person %d", person_id)

            treatment = HSI_Tb_RetreatmentChild(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date + DateOffset(days=1),
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] & (
            df.at[person_id, 'tb_inf'] == 'active_susc_secondary') & (
                df.at[person_id, 'age_years'] >= 15)):
            # request adult retreatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_RetreatmentAdult for person %d", person_id)

            treatment = HSI_Tb_RetreatmentAdult(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date + DateOffset(days=1),
                                                            tclose=None)

            # ----------------------------------- REFERRALS FOR IPT -----------------------------------

            # trigger ipt outreach event for all paediatric contacts of diagnosed case
            # randomly sample from <5 yr olds, match by district
            district = df.at[person_id, 'district_of_residence']

            if len(df.index[(df.age_years <= 5) & ~df.ever_tb & ~df.ever_tb_mdr &
                            df.is_alive & df.district_of_residence == district] > 5):
                ipt_sample = df[(df.age_years <= 5) &
                                ~df.ever_tb &
                                ~df.ever_tb_mdr &
                                df.is_alive &
                                df.district_of_residence == district].sample(n=5, replace=False,
                                                                             random_state=self.module.rng).index
                # need to pass pd.Series length (df.is_alive) to outreach event
                test = pd.Series(False, index=df.index)
                test.loc[ipt_sample] = True

                ipt_event = HSI_Tb_Ipt(self.module, person_id=person_id)
                self.sim.modules['HealthSystem'].schedule_event(ipt_event,
                                                                priority=1,
                                                                topen=self.sim.date + DateOffset(days=1),
                                                                tclose=None)

    def did_not_run(self):
        pass


class HSI_Tb_XpertTest(HSI_Event, IndividualScopeEventMixin):
    """
        This is a Health System Interaction Event - tb xpert test
        """

    # TODO if xpert test not available then request sputum test or clinical diagnosis / chest x-ray

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBFollowUp'] = 1
        the_appt_footprint['LabSero'] = 1

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_XpertTest'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = ['hiv']

    def apply(self, person_id, squeeze_factor):
        logger.debug("This is HSI_Tb_XpertTest giving xpert test for person %d", person_id)

        df = self.sim.population.props
        now = self.sim.date

        df.at[person_id, 'tb_ever_tested'] = True
        df.at[person_id, 'tb_xpert_test'] = True
        df.at[person_id, 'tb_date_xpert_test'] = now
        df.at[person_id, 'tb_result_xpert_test'] = False
        df.at[person_id, 'tb_diagnosed_mdr'] = False  # default

        # a further 10% of TB cases fail to be diagnosed with Xpert (smear-negative + sensitivity of test)
        # they will present back to the health system with some delay (2-4 weeks)
        if df.at[person_id, 'tb_inf'].startswith("active"):

            diagnosed = self.module.rng.choice([True, False], size=1, p=[0.9, 0.1])

            if diagnosed:
                df.at[person_id, 'tb_result_xpert_test'] = True
                df.at[person_id, 'tb_diagnosed'] = True

                if df.at[person_id, 'tb_inf'].startswith('active_mdr'):
                    df.at[person_id, 'tb_diagnosed_mdr'] = True

            # trigger ipt outreach event for all paediatric contacts of case
            # randomly sample from <5 yr olds
            district = df.at[person_id, 'district_of_residence']

            if len(df.index[(df.age_years <= 5) &
                            ~df.ever_tb &
                            ~df.ever_tb_mdr &
                            df.is_alive &
                            df.district_of_residence == district] > 5):
                ipt_sample = df[(df.age_years <= 5) &
                                ~df.ever_tb &
                                ~df.ever_tb_mdr &
                                df.is_alive &
                                df.district_of_residence == district].sample(
                    n=5,
                    replace=False, random_state=self.module.rng).index
                # need to pass pd.Series length (df.is_alive) to outreach event
                test = pd.Series(False, index=df.index)
                test.loc[ipt_sample] = True

                ipt_event = HSI_Tb_Ipt(self.module, person_id=person_id)
                self.sim.modules['HealthSystem'].schedule_event(ipt_event,
                                                                priority=1,
                                                                topen=self.sim.date,
                                                                tclose=None)

            else:
                # Request the health system to give repeat xpert test
                logger.debug("This is HSI_Tb_XpertTest with negative result for person %d", person_id)

                secondary_test = HSI_Tb_XpertTest(self.module, person_id=person_id)

                # Request the health system to give xpert test
                self.sim.modules['HealthSystem'].schedule_event(secondary_test,
                                                                priority=1,
                                                                topen=self.sim.date,
                                                                tclose=None)

        # ----------------------------------- REFERRALS FOR TREATMENT -----------------------------------
        if (df.at[person_id, 'tb_diagnosed'] &
            (df.at[person_id, 'tb_inf'] == 'active_susc_primary') & (
                df.at[person_id, 'age_years'] < 15)):
            # request child treatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentChild for person %d", person_id)

            treatment = HSI_Tb_StartTreatmentChild(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] &
            (df.at[person_id, 'tb_inf'] == 'active_susc_primary') & (
                df.at[person_id, 'age_years'] >= 15)):
            # request adult treatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentAdult for person %d", person_id)

            treatment = HSI_Tb_StartTreatmentAdult(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] &
            (df.at[person_id, 'tb_inf'] == 'active_susc_secondary') & (
                df.at[person_id, 'age_years'] < 15)):
            # request child retreatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentChild for person %d", person_id)

            treatment = HSI_Tb_RetreatmentChild(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        if (df.at[person_id, 'tb_diagnosed'] &
            (df.at[person_id, 'tb_inf'] == 'active_susc_secondary') & (
                df.at[person_id, 'age_years'] >= 15)):
            # request adult retreatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartTreatmentAdult for person %d", person_id)

            treatment = HSI_Tb_RetreatmentAdult(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        if df.at[person_id, 'tb_diagnosed'] & df.at[person_id, 'tb_inf'].startswith("active_mdr"):
            # request treatment
            logger.debug("This is HSI_Tb_XpertTest scheduling HSI_Tb_StartMdrTreatment for person %d", person_id)

            treatment = HSI_Tb_StartMdrTreatment(self.module, person_id=person_id)
            self.sim.modules['HealthSystem'].schedule_event(treatment,
                                                            priority=1,
                                                            topen=self.sim.date,
                                                            tclose=None)

        # log the consumables being used
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'Xpert test',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


# ---------------------------------------------------------------------------
#   Treatment
# ---------------------------------------------------------------------------
# the consumables at treatment initiation include the cost for the full course of treatment
# so the follow-up appts don't need to account for consumables, just appt time

class HSI_Tb_StartTreatmentAdult(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBNew'] = 1  # New tb treatment initiation appt, this include pharmacist time

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_TreatmentInitiationAdult'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("We are now ready to treat this tb case %d", person_id)

        now = self.sim.date
        df = self.sim.population.props
        params = self.module.parameters

        # treatment allocated
        if df.at[person_id, 'is_alive'] and df.at[person_id, 'tb_diagnosed']:
            df.at[person_id, 'tb_on_treatment'] = True
            df.at[person_id, 'date_tb_treated'] = now

        # schedule a 6-month event where people are cured, symptoms return to latent or not cured
        self.sim.schedule_event(TbCureEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # follow-up appts
        logger.debug('....This is HSI_Tb_StartTreatmentAdult: scheduling follow-up appointments for person %d',
                     person_id)

        followup_appt = HSI_Tb_FollowUp(self.module, person_id=person_id)

        # Request the health system to have this follow-up appointment
        weeks = params['followup_times'].loc['treatment']

        for i in range(0, len(weeks)):
            followup_appt_date = self.sim.date + DateOffset(months=weeks[i])
            self.sim.modules['HealthSystem'].schedule_hsi_event(followup_appt,
                                                                priority=1,
                                                                topen=followup_appt_date,
                                                                tclose=followup_appt_date + DateOffset(days=3)
                                                                )
        # log the consumables being used
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'First line treatment for new TB cases for adults',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


class HSI_Tb_StartTreatmentChild(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBNew'] = 1  # New tb treatment initiation appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_TreatmentInitiationChild'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("We are now ready to treat this tb case %d", person_id)

        now = self.sim.date
        df = self.sim.population.props
        params = self.module.parameters

        # treatment allocated
        if df.at[person_id, 'is_alive'] and df.at[person_id, 'tb_diagnosed']:
            df.at[person_id, 'tb_on_treatment'] = True
            df.at[person_id, 'date_tb_treated'] = now

        # schedule a 6-month event where people are cured, symptoms return to latent or not cured
        self.sim.schedule_event(TbCureEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # follow-up appts
        logger.debug('....This is HSI_Tb_StartTreatmentChild: scheduling follow-up appointments for person %d',
                     person_id)

        followup_appt = HSI_Tb_FollowUp(self.module, person_id=person_id)

        # Request the health system to have this follow-up appointment
        weeks = params['followup_times'].loc['treatment']

        for i in range(0, len(weeks)):
            followup_appt_date = self.sim.date + DateOffset(months=weeks[i])
            self.sim.modules['HealthSystem'].schedule_hsi_event(followup_appt,
                                                                priority=1,
                                                                topen=followup_appt_date,
                                                                tclose=followup_appt_date + DateOffset(days=3)
                                                                )
        # log the consuamables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'First line treatment for new TB cases for children',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


class HSI_Tb_StartMdrTreatment(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb-mdr treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBFollowUp'] = 1

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_MdrTreatmentInitiation'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("We are now ready to treat this tb case %d", person_id)

        now = self.sim.date
        df = self.sim.population.props
        params = self.module.parameters

        # treatment allocated
        if df.at[person_id, 'is_alive'] and df.at[person_id, 'tb_diagnosed']:
            df.at[person_id, 'tb_treated_mdr'] = True
            df.at[person_id, 'date_tb_treated_mdr'] = now

        # schedule a 6-month event where people are cured, symptoms return to latent or not cured
        self.sim.schedule_event(TbCureEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # follow-up appts
        logger.debug('....This is HSI_Tb_StartMdrTreatment: scheduling follow-up appointments for person %d',
                     person_id)

        followup_appt = HSI_Tb_FollowUp(self.module, person_id=person_id)

        # Request the health system to have this follow-up appointment
        weeks = params['followup_times'].loc['treatment']

        for i in range(0, len(weeks)):
            followup_appt_date = self.sim.date + DateOffset(months=weeks[i])
            self.sim.modules['HealthSystem'].schedule_hsi_event(followup_appt,
                                                                priority=1,
                                                                topen=followup_appt_date,
                                                                tclose=followup_appt_date + DateOffset(days=3)
                                                                )
        # log consumables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'Case management of MDR cases',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


class HSI_Tb_RetreatmentAdult(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBNew'] = 1  # This requires one out patient appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_RetreatmentAdult'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("We are now ready to treat this tb case %d", person_id)

        params = self.sim.modules['tb'].parameters
        now = self.sim.date
        df = self.sim.population.props

        # treatment allocated
        if df.at[person_id, 'is_alive'] and df.at[person_id, 'tb_diagnosed']:
            df.at[person_id, 'tb_on_treatment'] = True
            df.at[person_id, 'date_tb_treated'] = now

        # schedule a 6-month event where people are cured, symptoms return to latent or not cured
        self.sim.schedule_event(TbCureEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # follow-up appts
        logger.debug('....This is HSI_Tb_RetreatmentAdult: scheduling follow-up appointments for person %d',
                     person_id)

        followup_appt = HSI_Tb_FollowUp(self.module, person_id=person_id)

        # Request the health system to have this follow-up appointment
        weeks = params['followup_times'].loc['retreatment']

        for i in range(0, len(weeks)):
            followup_appt_date = self.sim.date + DateOffset(months=weeks[i])
            self.sim.modules['HealthSystem'].schedule_hsi_event(followup_appt,
                                                                priority=1,
                                                                topen=followup_appt_date,
                                                                tclose=followup_appt_date + DateOffset(days=3)
                                                                )

        # log consumables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'First line treatment for retreatment TB cases for adults',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


class HSI_Tb_RetreatmentChild(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBNew'] = 1  # New tb treatment initiation appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_RetreatmentChild'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("We are now ready to treat this tb case %d", person_id)

        params = self.sim.modules['tb'].parameters
        now = self.sim.date
        df = self.sim.population.props

        # treatment allocated
        if df.at[person_id, 'is_alive'] and df.at[person_id, 'tb_diagnosed']:
            df.at[person_id, 'tb_on_treatment'] = True
            df.at[person_id, 'date_tb_treated'] = now

        # schedule a 6-month event where people are cured, symptoms return to latent or not cured
        self.sim.schedule_event(TbCureEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # follow-up appts
        logger.debug('....This is HSI_Tb_RetreatmentChild: scheduling follow-up appointments for person %d',
                     person_id)

        followup_appt = HSI_Tb_FollowUp(self.module, person_id=person_id)

        # Request the health system to have this follow-up appointment
        weeks = params['followup_times'].loc['retreatment']

        for i in range(0, len(weeks)):
            followup_appt_date = self.sim.date + DateOffset(months=weeks[i])
            self.sim.modules['HealthSystem'].schedule_hsi_event(followup_appt,
                                                                priority=1,
                                                                topen=followup_appt_date,
                                                                tclose=followup_appt_date + DateOffset(days=3)
                                                                )
        # log the consumables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'First line treatment for retreatment TB cases for children',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


# ---------------------------------------------------------------------------
#   Follow-up appts
# ---------------------------------------------------------------------------
class HSI_Tb_FollowUp(HSI_Event, IndividualScopeEventMixin):
    """
    This is a Health System Interaction Event - start tb treatment
    """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['TBFollowUp'] = 1

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_FollowUp'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        # nothing needs to happen here, just log the appt
        logger.debug("Follow up appt for tb case %d", person_id)

    def did_not_run(self):
        pass


# ---------------------------------------------------------------------------
#   Cure
# ---------------------------------------------------------------------------


class TbCureEvent(Event, IndividualScopeEventMixin):

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

    def apply(self, person_id):
        logger.debug("Stopping tb treatment and curing person %d", person_id)

        df = self.sim.population.props
        params = self.sim.modules['tb'].parameters

        # after six months of treatment, stop
        df.at[person_id, 'tb_on_treatment'] = False

        # if drug-susceptible then probability of successful treatment for both primary and secondary
        if df.at[person_id, 'tb_inf'].startswith("active_susc"):

            cured = self.module.rng.random_sample(size=1) < params['prob_treatment_success']

            if cured:
                df.at[person_id, 'tb_inf'] = 'latent_susc_secondary'
                df.at[person_id, 'tb_diagnosed'] = False
                df.loc[person_id, 'tb_specific_symptoms'] = 'latent'
                df.loc[person_id, 'tb_unified_symptom_code'] = 1

            else:
                # request a repeat / Xpert test - follow-up
                # this will include drug-susceptible treatment failures and mdr-tb cases
                secondary_test = HSI_Tb_XpertTest(self.module, person_id=person_id)

                # Request the health system to give xpert test
                self.sim.modules['HealthSystem'].schedule_event(secondary_test,
                                                                priority=1,
                                                                topen=self.sim.date,
                                                                tclose=None)


class TbCureMdrEvent(Event, IndividualScopeEventMixin):

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

    def apply(self, person_id):
        logger.debug("Stopping tb-mdr treatment and curing person %d", person_id)

        df = self.sim.population.props

        # after six months of treatment, stop
        # assume 100% cure rate with tb-mdr treatment
        df.at[person_id, 'tb_treated_mdr'] = False
        df.at[person_id, 'tb_inf'] = 'latent_mdr_secondary'
        df.at[person_id, 'tb_diagnosed'] = False
        df.loc[person_id, 'tb_specific_symptoms'] = 'latent'
        df.loc[person_id, 'tb_unified_symptom_code'] = 1


#
# ---------------------------------------------------------------------------
#   IPT
# ---------------------------------------------------------------------------
# TODO consumables should be IPT for non-HIV+
class HSI_Tb_Ipt(HSI_Event, IndividualScopeEventMixin):
    """
        This is a Health System Interaction Event - give ipt to contacts of tb cases for 6 months
        """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['Over5OPD'] = 1  # This requires one out patient appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_Ipt'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("Starting IPT for person %d", person_id)

        df = self.sim.population.props

        df.at[person_id, 'tb_on_ipt'] = True
        df.at[person_id, 'tb_date_ipt'] = self.sim.date

        # schedule end date of ipt after six months
        self.sim.schedule_event(TbIptEndEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # log consumables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'Isoniazid preventative therapy for HIV+ no TB',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")

    def did_not_run(self):
        pass


class HSI_Tb_IptHiv(HSI_Event, IndividualScopeEventMixin):
    """
        This is a Health System Interaction Event - give ipt to hiv+ persons
        called by hiv module when starting ART (adults and children)
        """

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

        # Get a blank footprint and then edit to define call on resources of this treatment event
        the_appt_footprint = self.sim.modules['HealthSystem'].get_blank_appt_footprint()
        the_appt_footprint['Over5OPD'] = 1  # This requires one out patient appt

        # Define the necessary information for an HSI
        self.TREATMENT_ID = 'Tb_IptHiv'
        self.EXPECTED_APPT_FOOTPRINT = the_appt_footprint
        self.ACCEPTED_FACILITY_LEVEL = 1
        self.ALERT_OTHER_DISEASES = []

    def apply(self, person_id, squeeze_factor):
        logger.debug("Starting IPT for HIV+ person %d", person_id)

        df = self.sim.population.props

        df.at[person_id, 'tb_on_ipt'] = True
        df.at[person_id, 'tb_date_ipt'] = self.sim.date

        # schedule end date of ipt after six months and repeat call to HS for another prescription
        self.sim.schedule_event(TbIptEndEvent(self, person_id), self.sim.date + DateOffset(months=6))

        # log consumables being used:
        consumables = self.sim.modules['HealthSystem'].parameters['Consumables']
        pkg_code1 = pd.unique(
            consumables.loc[
                consumables['Intervention_Pkg'] == 'Isoniazid preventative therapy for HIV+ no TB',
                'Intervention_Pkg_Code'])[0]

        the_cons_footprint = {
            'Intervention_Package_Code': [{pkg_code1: 1}],
            'Item_Code': []
        }
        is_cons_available = self.sim.modules['HealthSystem'].request_consumables(
            hsi_event=self,
            cons_req_as_footprint=the_cons_footprint)
        logger.warning(f"is_cons_available ({is_cons_available}) should be used in this method")


class TbIptEndEvent(Event, IndividualScopeEventMixin):

    def __init__(self, module, person_id):
        super().__init__(module, person_id=person_id)

    def apply(self, person_id):
        logger.debug("Stopping ipt for person %d", person_id)

        df = self.sim.population.props

        df.at[person_id, 'tb_on_ipt'] = False

        # if hiv+ reschedule HSI_Tb_IptHiv to continue IPT
        if df.at[person_id, 'hv_inf']:
            logger.debug(
                '....This is TbIptEndEvent: scheduling further IPT for person %d on date %s',
                person_id, self.sim.date)

            ipt_start = HSI_Tb_IptHiv(self.module, person_id=person_id)

            # Request the health system to have this follow-up appointment
            self.sim.modules['HealthSystem'].schedule_hsi_event(ipt_start,
                                                                priority=1,
                                                                topen=self.sim.date,
                                                                tclose=None
                                                                )


# ---------------------------------------------------------------------------
#   Deaths
# ---------------------------------------------------------------------------
class TbDeathEvent(RegularEvent, PopulationScopeEventMixin):
    """The regular event that kills people.
    """

    # TODO: if HIV+, cause of death should be HIV as hiv/tb deaths are counted in hiv data
    def __init__(self, module):
        super().__init__(module, frequency=DateOffset(months=1))

    def apply(self, population):
        params = self.module.parameters
        df = population.props
        now = self.sim.date
        rng = self.module.rng

        # only active infections result in death, no deaths on treatment
        mortality_rate = pd.Series(0, index=df.index)

        mortality_rate.loc[df['tb_inf'].str.contains('active') & ~df.hv_inf & (
            ~df.tb_on_treatment | ~df.tb_treated_mdr)] = params[
            'monthly_prob_tb_mortality']

        mortality_rate.loc[df['tb_inf'].str.contains('active') & df.hv_inf & (
            ~df.tb_on_treatment | ~df.tb_treated_mdr)] = params[
            'monthly_prob_tb_mortality_hiv']
        # print('mort_rate: ', mortality_rate)

        # Generate a series of random numbers, one per individual
        probs = rng.rand(len(df))
        deaths = df.is_alive & (probs < mortality_rate)
        # print('deaths: ', deaths)
        will_die = (df[deaths]).index
        # print('will_die: ', will_die)

        for person in will_die:
            if df.at[person, 'is_alive']:
                self.sim.schedule_event(demography.InstantaneousDeath(self.module, individual_id=person, cause='tb'),
                                        now)
                df.at[person, 'tb_date_death'] = now


# ---------------------------------------------------------------------------
#   Logging
# ---------------------------------------------------------------------------

class TbLoggingEvent(RegularEvent, PopulationScopeEventMixin):
    def __init__(self, module):
        """ produce some outputs to check
        """
        # run this event every 12 months
        self.repeat = 12
        super().__init__(module, frequency=DateOffset(months=self.repeat))

    def apply(self, population):
        # get some summary statistics
        df = population.props
        now = self.sim.date

        active_susc = len(
            df[df['tb_inf'].str.contains('active_susc') & df.is_alive])

        active_mdr = len(
            df[df['tb_inf'].str.contains('active_mdr') & df.is_alive])

        active_total = active_susc + active_mdr

        ad_prev = len(df[df['tb_inf'].str.contains('active') & df.is_alive & (
            df.age_years >= 15)]) / len(df[df.is_alive & (df.age_years >= 15)])

        child_prev = len(df[df['tb_inf'].str.contains('active') & df.is_alive & (
            df.age_years < 15)]) / len(df[df.is_alive & (df.age_years < 15)])

        ad_prev_latent = len(df[df['tb_inf'].str.contains('latent') & df.is_alive & (
            df.age_years >= 15)]) / len(df[df.is_alive & (df.age_years >= 15)])

        child_prev_latent = len(df[df['tb_inf'].str.contains('latent') & df.is_alive & (
            df.age_years < 15)]) / len(df[df.is_alive & (df.age_years < 15)])

        logger.info('%s|summary|%s', now,
                    {
                        'tbTotalInf': active_total,
                        'tbActiveSusc': active_susc,
                        'tbActiveMdr': active_mdr,
                        'tbLatentAdultPrev': ad_prev_latent,
                        'tbLatentChildPrev': child_prev_latent,
                        'tbAdultActivePrev': ad_prev,
                        'tbChildActivePrev': child_prev,
                    })
