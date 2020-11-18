import numpy as np
import pandas as pd
import scipy.stats as ss


###################### Main API #########################
## Takes in a df of a price series. Appends to it the period-wise returns and cumulative returns.
## Then calculates the distirbution statistics and evalutaion metrics on a return series.
## - The '_name' variables are your designations of the respective columns.
## - IMPORTANT: both return_df[date_name] and risk_free_df[date_name] must be convertible to datetime64[ns]
def analyze_return(return_df, asset_name,  num_periods_in_a_year=12, risk_free_df=None, return_name='月涨幅', return_price_name='月收盘价',
                   cumulative_return_name='累计涨幅'
                      , risk_free_name='SHIBOR_Trailing_7Days', date_name='交易日期'):
    return_df[date_name] = pd.to_datetime(return_df[date_name])
    return_df.sort_values(by = date_name, inplace=True)
    return_df[return_name] = (return_df[return_price_name] - return_df[return_price_name].shift(1)) / return_df[return_price_name].shift(1)
    return_df[cumulative_return_name] = (return_df[return_price_name] - return_df[return_price_name][0])/return_df[return_price_name][0]
    if risk_free_df is None:
        risk_free_df = pd.DataFrame()
        risk_free_df[date_name] = return_df[date_name]
        risk_free_df[risk_free_name] = 0
    return_df_with_excess = add_excess_return(return_df, num_periods_in_a_year, risk_free_df, return_name,
                                             risk_free_name, date_name)
    sharpe_ratio = SharpeRatio(return_df_with_excess[return_name + '_excess'], num_periods_in_a_year)
    sortino_ratio = SortinoRatio(return_df_with_excess[return_name + '_excess'], num_periods_in_a_year)
    drawdown_details, summary = analyze_drawdown(return_df_with_excess[cumulative_return_name])
    summary['sortino'] = sortino_ratio
    summary['sharpe'] = sharpe_ratio
    summary['kurtosis'] = ss.kurtosis((return_df_with_excess[return_name + '_excess']).dropna())
    summary['skewness'] = ss.skew((return_df_with_excess[return_name + '_excess']).dropna())
    summary['standard_deviation'] = np.std(return_df_with_excess[return_name + '_excess'])
    summary['mean'] = return_df_with_excess[return_name + '_excess'].mean()
    summary['total_return'] = return_df_with_excess[cumulative_return_name][(len(return_df_with_excess[cumulative_return_name]) - 1)]
    summary['asset_name'] = asset_name
    summary_df = (convert_dict_to_column_df(summary))[::-1]
    return summary_df, drawdown_details



def SharpeRatio(excess_returns, num_periods_in_a_year):
    ## For daily data, put num_periods_in_a_year = 252; for monthly put 12; for quarterly put 4
    sd_scaling_ratio = np.sqrt(num_periods_in_a_year)
    sd_excess_returns = np.std(excess_returns)
    mean_excess_returns = np.mean(excess_returns)
    return mean_excess_returns / sd_excess_returns * sd_scaling_ratio

def SortinoRatio(excess_returns, num_periods_in_a_year):
    ## For daily data, put num_periods_in_a_year = 252; for monthly put 12; for quarterly put 4
    sd_scaling_ratio = np.sqrt(num_periods_in_a_year)
    sd_negative_excess_returns = np.std(excess_returns[excess_returns <= 0])
    mean_excess_returns = np.mean(excess_returns)
    return mean_excess_returns / sd_negative_excess_returns * sd_scaling_ratio

def analyze_drawdown(series):
    all_drawdowns = find_all_drawdown_recoveries(series)
    all_drawdowns['drawdown_level_abs'] = all_drawdowns['trough_level'] - all_drawdowns['peak_level']
    all_drawdowns['num_periods_to_recover'] = all_drawdowns['recovery_index'] - all_drawdowns['trough_index']
    all_drawdowns['num_periods_total'] = all_drawdowns['recovery_index'] - all_drawdowns['peak_index']
    num_recovered_drawdowns = all_drawdowns.shape[0] - 1
    max_drawdown = all_drawdowns['drawdown_level_abs'].min()
    average_drawdown = all_drawdowns['drawdown_level_abs'].mean()
    average_periods_to_recover = all_drawdowns['num_periods_to_recover'].mean()
    average_periods_total = all_drawdowns['num_periods_total'].mean()
    drawdown_summary = {'max_drawdown': max_drawdown, 'num_recovered_drawdowns': num_recovered_drawdowns,
            'average_periods_to_recover': average_periods_to_recover, 'average_periods_total': average_periods_total,
                       'average_drawdown': average_drawdown}
    return (all_drawdowns, drawdown_summary)

########################## Below are utilitiy functions #######################


def add_excess_return(return_df, num_periods_in_a_year=12, risk_free_df=None, return_name='月涨幅'
                      , risk_free_name='SHIBOR_Trailing_7Days', date_name='交易日期'):
    risk_free_df_adjusted = risk_free_df.copy()
    risk_free_df_adjusted['risk_free_per_period'] = risk_free_df_adjusted[risk_free_name] / (100 * num_periods_in_a_year)
    return_df = return_df.merge(risk_free_df_adjusted, how='left', on=date_name)
    return_df[return_name + '_excess'] = return_df[return_name] - return_df['risk_free_per_period']
    return return_df


def find_next_local_max(series, start):
    start += 1   #### This moves the search forward by one step. Makes the iteration look nicer. See below.
    i = start
    while i < len(series) - 1:
        if (series[i] >= series[i + 1] and series[i] >= series[i - 1]):
            return (i, series[i])
        i += 1
    else:
#         print('Conducting the search for the next local_max. \n The current starting index is {}. The length of the series searched is {}. Seach has concluded.'.format(i, len(series)))
        return None


# #### Why plus one? See below
# find_next_local_max(stock_market['累计涨幅'], 0)
# find_next_local_max(stock_market['累计涨幅'], 2)
# find_next_local_max(stock_market['累计涨幅'], 6)

def find_next_local_min(series, start):
    start += 1   #### This moves the search forward by one step. Makes the iteration look nicer. See below.
    i = start
    while i < len(series) - 1:
        if (series[i] <= series[i + 1] and series[i] <= series[i - 1]):
            return (i, series[i])
        i += 1
    else:
#         print('Conducting the search for the next local_min. \n The current starting index is {}. The length of the series searched is {}. Seach has concluded.'.format(i, len(series)))
        return None

def find_next_greater_than(series, start, value):
    start += 1   #### This moves the search forward by one step. Makes the iteration look nicer. See below.
    i = start
    while i < len(series) - 1:
        if (series[i] > value):
            return (i, series[i])
        i += 1
    else:
#         print('Conducting the search for the next greater_than. \n The current starting index is {}. The length of the series searched is {}. Seach has concluded.'.format(i, len(series)))
        return None


def find_next_drawdown_with_recovery(series, start):
    series_with_index = series.copy()
    series_with_index.index = np.arange(series.size)
    try:
        local_peak_index, local_peak = find_next_local_max(series, start)
    except:
        return None
    try:
        recovery_index, recovery_level = find_next_greater_than(series, local_peak_index, local_peak)
    except:
        return None
    series_examined = series_with_index[local_peak_index: (recovery_index + 1)]
    local_trough = series_examined.min()
    local_trough_index = series_examined.index[np.where(series_examined == local_trough)[0][0]]
    item_names = ['peak_index', 'peak_level', 'trough_index', 'trough_level', 'recovery_index', 'recovery_level']
    items = [local_peak_index, local_peak, local_trough_index, local_trough, recovery_index, recovery_level]
    return dict(zip(item_names, items))

def find_next_drawdown_without_recovery(series, start):
    series_with_index = series.copy()
    series_with_index.index = np.arange(series.size)
    try:
        local_peak_index, local_peak = find_next_local_max(series, start)
    except:
        return None
    series_examined = series_with_index[local_peak_index: ]
    local_trough = series_examined.min()
    local_trough_index = series_examined.index[np.where(series_examined == local_trough)[0][0]]
    item_names = ['peak_index', 'peak_level', 'trough_index', 'trough_level', 'recovery_index', 'recovery_level']
    items = [local_peak_index, local_peak, local_trough_index, local_trough, None, None]
    return dict(zip(item_names, items))

def find_next_drawdown_recovery(series, start):
    result = find_next_drawdown_with_recovery(series, start)
    if result is None:
        result = find_next_drawdown_without_recovery(series, start)
    return result

def find_all_drawdown_recoveries(series):
    start = 0
    result = pd.DataFrame()
    while True:
        this_instance = find_next_drawdown_recovery(series, start)
        if not this_instance:
            break
        result = result.append(this_instance, ignore_index=True)
        start = this_instance['recovery_index']
        if start is None:
            break
    return result

def convert_dict_to_column_df(dic):
    result = pd.DataFrame({'value':[]})
    for key, value in dic.items():
        result.loc[key, 'value']  = value
    return result


def add_cumulative_return(df, date_name='交易日期', return_name='月涨幅', cumulative_return_name='累计涨幅', price_name='月收盘价'):
    ### Note the df must have column 月收盘价
    df.dropna(inplace=True)
    df[date_name] = pd.to_datetime(df[date_name])
    df[return_name] = ((df[price_name].shift(-1) - df[price_name]) / df[price_name]).shift(1)
    df[cumulative_return_name] = np.cumprod(df[return_name] + 1) - 1
    return df
