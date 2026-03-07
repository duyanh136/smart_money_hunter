from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd
import time

# Full Watchlist
WATCHLIST = [
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
    'LPB', 'MSB', 'OCB', 'EIB', 'VIX', 'VND', 'ORS', 'CTS', 'FTS', 'BSI', 
    'HCM', 'AGR', 'MBS', 'BVS', 'VDS',
    'DIG', 'CEO', 'DXG', 'PDR', 'NVL', 'KBC', 'IDC', 'SZC', 'VGC', 'DXS',
    'HDG', 'HQC', 'ITA', 'KHG', 'LG', 'SCR', 'TCH', 'CRE', 'IJC', 'L14',
    'HBC', 'CTD', 'LCG', 'HHV', 'VCG', 'CII', 'FCN',
    'DGC', 'DGW', 'FRT', 'PET', 'PNJ', 'REE', 'SAM', 'ANV', 'ASM', 'BAF',
    'DBC', 'HAG', 'HG', 'PAN', 'VHC', 'IDI',
    'GEG', 'GEX', 'NT2', 'PC1', 'PPC', 'VSH', 'BSR', 'OIL', 'PVD', 'PVS',
    'PVC', 'PVT',
    'GMD', 'HAH', 'VOS', 'VSC', 'HNG', 'HAG', 'GEE'
]

import sys
import io

# Force UTF-8 for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("-" * 120)
print(f"{'Mã':<6} | {'Giá':<10} | {'Action (Khuyến nghị)':<30} | {'Phase':<30} | {'Golden':<6} | {'Warning':<7} | {'RSI':<5}")
print("-" * 120)

for symbol in WATCHLIST:
    try:
        df = MarketService.get_history(symbol, period="6mo")
        if df is not None and not df.empty:
            df = SmartMoneyAnalyzer.analyze(df)
            row = df.iloc[-1]
            
            action = row.get('Action_Recommendation', 'N/A')
            phase = row.get('Market_Phase', 'N/A')
            golden = str(bool(row.get('Signal_GoldenSell')))
            warning = str(bool(row.get('Signal_Distribution') or row.get('Signal_UpBo')))
            rsi = f"{row['RSI']:.1f}"
            
            # Filter output to only potential sells or warnings
            is_sell_candidate = 'BÁN' in action.upper() or \
                                'CẮT LỖ' in action.upper() or \
                                'HẠ MARGIN' in action.upper() or \
                                'PHÂN PHỐI' in phase.upper() or \
                                row.get('Signal_GoldenSell') or \
                                row.get('Signal_Distribution') or \
                                row.get('Signal_UpBo') or \
                                row['RSI'] > 75
                                
            if is_sell_candidate:
                # Use simple print, handled by wrapper
                print(f"{symbol:<6} | {row['Close']:<10} | {action:<30} | {phase:<30} | {golden:<6} | {warning:<7} | {rsi:<5}")
                
    except Exception:
        pass

print("-" * 120)
