import pandas as pd
import numpy as np

def sma(close, length):
    return close.rolling(window=length).mean()

def rsi(close, length=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({
        f'MACD_{fast}_{slow}_{signal}': macd_line,
        f'MACDh_{fast}_{slow}_{signal}': hist,
        f'MACDs_{fast}_{slow}_{signal}': signal_line
    })

def ichimoku(high, low, close, tenkan=9, kijun=26, senkou=52):
    def get_mid(h, l, n):
        return (h.rolling(window=n).max() + l.rolling(window=n).min()) / 2

    tenkan_sen = get_mid(high, low, tenkan)
    kijun_sen = get_mid(high, low, kijun)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_span_b = get_mid(high, low, senkou).shift(kijun)
    # Note: ichimoku usually returns multiple dataframes or a complex object.
    # Looking at the code: df = pd.concat([df, ichimoku], axis=1) 
    # ISA_9, ISB_26, ITS_9, IKS_26, ICS_26
    return [pd.DataFrame({
        f'ITS_{tenkan}': tenkan_sen,
        f'IKS_{kijun}': kijun_sen,
        f'ISA_{tenkan}': senkou_span_a,
        f'ISB_{kijun}': senkou_span_b,
        f'ICS_{kijun}': close.shift(-kijun)
    })]

def bbands(close, length=20, std=2):
    sma_val = close.rolling(window=length).mean()
    std_val = close.rolling(window=length).std()
    upper = sma_val + (std * std_val)
    lower = sma_val - (std * std_val)
    return pd.DataFrame({
        f'BBL_{length}_{std}.0': lower,
        f'BBM_{length}_{std}.0': sma_val,
        f'BBU_{length}_{std}.0': upper,
        f'BBB_{length}_{std}.0': (upper - lower) / sma_val * 100,
        f'BBP_{length}_{std}.0': (close - lower) / (upper - lower)
    })

def atr(high, low, close, length=14):
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=length).mean()
