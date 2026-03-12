import os
import sys
import logging
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.sql_utils import SQLUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("daily_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DailyAnalysis")

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

def analyze_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        logger.info(f"Analyzing {symbol}...")
        df = MarketService.get_history(symbol, period='6mo')
        
        if df is None or df.empty:
            return None
            
        df = SmartMoneyAnalyzer.analyze(df)
        if df is None or df.empty:
            return None
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row
        
        # Leaderscore as proxy
        idx_df = MarketService.get_history("SSI", period="3mo")
        score_data = SmartMoneyAnalyzer.calc_leader_score(df, index_df=idx_df)
        class_info = SmartMoneyAnalyzer.classify_stock(symbol)
        
        # Determine BuySignalStatus (matches SQL requirements)
        # Based on signals and ActionRecommendation
        action = last_row.get('Action_Recommendation', 'QUAN SÁT').upper()
        buy_signal = 'QUAN SÁT'
        if "MUA" in action or "GIA TĂNG" in action:
            buy_signal = 'MUA'
        elif "BÁN" in action or "HẠ TỶ TRỌNG" in action:
            buy_signal = 'BÁN'
            
        return {
            'symbol': symbol,
            'price': float(last_row['Close']),
            'change': round((last_row['Close'] - prev_row['Close'])/prev_row['Close'] * 100, 2) if prev_row['Close'] > 0 else 0,
            'vol_ratio': round(float(last_row['Vol_Ratio']), 2) if 'Vol_Ratio' in last_row else 0,
            'rsi': round(float(last_row['RSI']), 1) if 'RSI' in last_row else 50,
            'market_phase': last_row['Market_Phase'],
            'action': last_row['Action_Recommendation'],
            'leader_score': score_data['score'],
            'is_shark_dominated': score_data['is_shark_dominated'],
            'is_storm_resistant': score_data['is_storm_resistant'],
            'tag': class_info.get('tag', ''),
            'buy_signal_status': buy_signal,
            # Signals
            'signal_voteo': bool(last_row.get('Signal_VoTeo')),
            'signal_buydip': bool(last_row.get('Signal_BuyDip')),
            'signal_breakout': bool(last_row.get('Signal_Breakout')),
            'signal_goldensell': bool(last_row.get('Signal_GoldenSell')),
            'signal_warning': bool(last_row.get('Signal_Distribution') or last_row.get('Signal_UpBo')),
            # Radar
            'radar_panicsell': bool(last_row.get('Signal_PanicSell')),
            'radar_sangtay': bool(last_row.get('Signal_SangTayNhoLe')),
            'radar_gaynen': bool(last_row.get('Signal_GayNenTestLai')),
            'radar_phankyam': bool(last_row.get('Signal_PhanKyAmMACD')),
            'radar_daodong': bool(last_row.get('Signal_DaoDongLongLeo')),
            'radar_chammay': bool(last_row.get('Signal_ChamMayKenhDuoi')),
            'pyramid_action': last_row.get('Pyramid_Action', 'N/A'),
            'base_distance_pct': float(last_row.get('Base_Distance_Pct', 0))
        }
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
    return None

def run_daily_analysis():
    logger.info("Starting daily market analysis...")
    start_time = datetime.now()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(analyze_symbol, WATCHLIST))
    
    # Filter out None results and sort by LeaderScore for Ranking
    analysis_results = [r for r in results if r is not None]
    analysis_results.sort(key=lambda x: x['leader_score'], reverse=True)
    
    # Assign Ranks
    for i, res in enumerate(analysis_results):
        res['rank'] = i + 1
        
    if analysis_results:
        logger.info(f"Saving {len(analysis_results)} results to database...")
        SQLUtils.save_market_analysis(analysis_results)
        SQLUtils.save_market_analysis_to_history(analysis_results)
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Daily analysis completed. Success: {len(analysis_results)}/{len(WATCHLIST)}. Duration: {duration}")

if __name__ == "__main__":
    run_daily_analysis()
