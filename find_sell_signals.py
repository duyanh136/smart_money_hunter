from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import concurrent.futures
import pandas as pd

# Watchlist from app.py
watchlist = [
    # VN30
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
    # Banking & Finance
    'LPB', 'MSB', 'OCB', 'EIB', 'VIX', 'VND', 'ORS', 'CTS', 'FTS', 'BSI', 
    'HCM', 'AGR', 'MBS', 'BVS', 'VDS',
    # Real Estate & Construction
    'DIG', 'CEO', 'DXG', 'PDR', 'NVL', 'KBC', 'IDC', 'SZC', 'VGC', 'DXS',
    'HDG', 'HQC', 'ITA', 'KHG', 'LG', 'SCR', 'TCH', 'CRE', 'IJC', 'L14',
    'HUT', 'CII', 'NBB', 'HTN', 'HBC', 'CTD', 'LCG', 'HHV', 'VCG', 'FCN', 'KSB',
    # Steel & Materials
    'NKG', 'HSG', 'TLH', 'POM', 'TVN', 'SMC',
    # Oil & Gas, Power
    'PVD', 'PVS', 'PVT', 'PVC', 'BSR', 'OIL', 'GEG', 'NT2', 'REE', 'PC1', 'TV2',
    # Retail, Consumer, Agriculture
    'DGW', 'FRT', 'PET', 'PNJ', 'VGI', 'DBC', 'HAG', 'HNG', 'PAN', 'TAR', 'LTG',
    # Chemicals & Fertilizer
    'DGC', 'DPM', 'DCM', 'CSV', 'LAS', 'DDV',
    # Logistics & Others
    'GMD', 'HAH', 'VOS', 'VSC', 'ANV', 'VHC', 'IDI', 'ASM', 'GIL', 'TNG', 'MSH'
]

print("Đang quét toàn thị trường tìm cổ phiếu vùng BÁN/NGUY HIỂM...")
print("-" * 60)
print(f"{'Mã':<6} | {'Giá':<8} | {'Giai đoạn':<30} | {'Khuyến nghị':<20}")
print("-" * 60)

def scan_symbol(symbol):
    try:
        df = MarketService.get_history(symbol, period='6mo')
        if df is not None:
            df = SmartMoneyAnalyzer.analyze(df)
            if df is not None and not df.empty:
                last_row = df.iloc[-1]
                action = last_row['Action_Recommendation']
                phase = last_row['Market_Phase']
                
                # Filter for Sell/Danger signals
                if "BÁN" in action.upper() or \
                   "HẠ MARGIN" in action.upper() or \
                   "PHÂN PHỐI" in phase.upper() or \
                   "QUÁ MUA" in phase.upper() or \
                   last_row['Signal_Distribution'] or \
                   last_row['Signal_UpBo'] or \
                   last_row['RSI'] > 70:
                    
                    return {
                        'symbol': symbol,
                        'price': last_row['Close'],
                        'phase': phase,
                        'action': action
                    }
    except Exception as e:
        pass
    return None

sell_list = []
import sys

with open('scan_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"{'Mã':<6} | {'Giá':<8} | {'Giai đoạn':<40} | {'Khuyến nghị':<30}\n")
    f.write("-" * 90 + "\n")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_symbol, sym): sym for sym in watchlist}
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            sym = futures[future]
            try:
                res = future.result()
                if res:
                    line = f"{res['symbol']:<6} | {res['price']:<8.2f} | {res['phase']:<40} | {res['action']:<30}\n"
                    f.write(line)
                    f.flush()
                    print(f"FOUND: {res['symbol']} - {res['phase']}")
            except Exception as e:
                pass
            
            if i % 10 == 0:
                print(f"Scanned {i}/{len(watchlist)}...")

print("Done scanning.")
