from services.tcbs_service import tcbs_service
import concurrent.futures

# Copying Watchlist to avoid app import side-effects
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

print(f"Checking data for {len(WATCHLIST)} stocks from TCBS...")

failed_stocks = []

def check_stock(symbol):
    try:
        # Check last 10 days
        df = tcbs_service.get_history(symbol, resolution='D', count_back=10)
        if df is None or df.empty:
            return symbol
    except Exception as e:
        return f"{symbol} ({str(e)})"
    return None

with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_stock, sym): sym for sym in WATCHLIST}
    for i, future in enumerate(concurrent.futures.as_completed(futures)):
        result = future.result()
        if result:
            failed_stocks.append(result)
            print(f"FAILED: {result}")
        
        if (i + 1) % 20 == 0:
            print(f"Checked {i + 1}/{len(WATCHLIST)}...")

print("-" * 30)
if failed_stocks:
    print(f"Found {len(failed_stocks)} stocks with NO DATA from TCBS:")
    print(", ".join(failed_stocks))
else:
    print("All stocks have VALID data from TCBS!")
