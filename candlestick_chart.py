#  https://algotrading101.com/learn/yfinance-guide/
#
#  pip3 install yfinance mplfinance analysis_engine


import yfinance as yf
import mplfinance as mpf
import analysis_engine.finviz.fetch_api as fv

url = (
    'https://finviz.com/screener.ashx?'
    'v=111&'
    'f=cap_midunder,exch_nyse,fa_div_o5,idx_sp500'
    '&ft=4')
res = fv.fetch_tickers_from_screener(url=url)
print(res)


ticker = input("Enter the stock name: " ).upper()
df = yf.download( ticker , start='2023-08-01', end ='2025-06-02')
if df is not None:
    df.columns = df.columns.get_level_values(0)  # FLATTEN MULTI-INDEX COLUMNS    
    df['Open'] = df['Open'].astype('float64')
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    mpf.plot( df , ema=[12,52] ,type='candle', style='yahoo', title=f'{ticker} Candlestick Chart', ylabel='Price')
else:
    print('\t Could not download this ticker : ' , ticker)
