from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd
import time

# Full Watchlist from app.py
WATCHLIST = [
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
    'HBC', 'CTD', 'LCG', 'HHV', 'VCG', 'CII', 'FCN',
    # Industrial & Retail
    'DGC', 'DGW', 'FRT', 'PET', 'PNJ', 'REE', 'SAM', 'ANV', 'ASM', 'BAF',
    'DBC', 'HAG', 'HG', 'PAN', 'VHC', 'IDI',
    # Energy & Utilities
    'GEG', 'GEX', 'NT2', 'PC1', 'PPC', 'VSH', 'BSR', 'OIL', 'PVD', 'PVS',
    'PVC', 'PVT',
    # Others
    'GMD', 'HAH', 'VOS', 'VSC', 'HNG', 'HAG', 'GEE'
]

print(f"Scanning {len(WATCHLIST)} stocks for SELL signals (Golden Sell / Distribution / Warning)...")
print("-" * 80)
print(f"{'Mã':<6} | {'Giá':<10} | {'RSI':<6} | {'Vol/Avg':<8} | {'Tín hiệu':<25} | {'Hành động':<20}")
print("-" * 80)

found_any = False

for symbol in WATCHLIST:
    try:
        df = MarketService.get_history(symbol, period="6mo")
        if df is not None and not df.empty:
            df = SmartMoneyAnalyzer.analyze(df)
            row = df.iloc[-1]
            
            # Check for ANY Sell/Warning signal
            is_sell = False
            signals = []
            
            # 1. Golden Sell
            if row.get('Signal_GoldenSell'):
                signals.append("GOLDEN SELL")
                is_sell = True
                
            # 2. Distribution / Up Bo
            if row.get('Signal_Distribution') or row.get('Signal_UpBo'):
                signals.append("PHÂN PHỐI/UP BÔ")
                is_sell = True
                
            # 3. Overbought / Warning
            if row['RSI'] > 75:
                signals.append("QUÁ MUA (RSI>75)")
                is_sell = True
                
            # 4. Action Recommendation explicitly says SELL
            action = row.get('Action_Recommendation', '').upper()
            if 'BÁN' in action or 'HẠ MARGIN' in action or 'CẮT LỖ' in action:
                 is_sell = True
            
            if is_sell:
                found_any = True
                vol_ratio = row['Volume'] / row['Avg_Vol_20'] if row['Avg_Vol_20'] > 0 else 0
                sig_str = ", ".join(signals) if signals else "Cảnh báo (Downtrend/Cắt lỗ)"
                
                print(f"{symbol:<6} | {row['Close']:<10} | {row['RSI']:.1f}   | {vol_ratio:.1f}x     | {sig_str:<25} | {row['Action_Recommendation']:<20}")
                
    except Exception as e:
        # print(f"Error {symbol}: {e}")
        pass

print("-" * 80)
if not found_any:
    print("Tuyệt vời! Hiếm có khó tìm. Không thấy mã nào báo Bán KHẨN CẤP hôm nay.")
else:
    print("Đã tìm thấy các mã cần chú ý bên trên.")
