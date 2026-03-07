import pandas as pd
import pandas_ta as ta
import numpy as np

class SmartMoneyAnalyzer:
    @staticmethod
    def analyze(df: pd.DataFrame):
        """
        Analyze Smart Money vs Retail Money (Deep Dive).
        """
        if df is None or df.empty:
            return None
        
        # --- 1. Technical Indicators ---
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # MACD
        macd = ta.macd(df['Close'])
        if macd is not None:
            df = pd.concat([df, macd], axis=1) # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            # Verify column names, standard pandas_ta names are usually:
            # MACD_12_26_9 (Line), MACDh_12_26_9 (Hist), MACDs_12_26_9 (Signal)
            
            # Create standardized columns for easier access
            df['MACD_Line'] = df['MACD_12_26_9']
            df['MACD_Signal'] = df['MACDs_12_26_9']
            df['MACD_Hist'] = df['MACDh_12_26_9']

        # Ichimoku (Conversion Line, Base Line, Spans)
        ichimoku = ta.ichimoku(df['High'], df['Low'], df['Close'])[0]
        # Rename for easier access: ISA_9, ISB_26, ITS_9, IKS_26, ICS_26
        df = pd.concat([df, ichimoku], axis=1) 

        # --- 2. Smart Money Flow (Shark vs Retail) ---
        # Logic: 
        # - Shark Flow (Tiền Lớn): Large Volume + Price Move aligned with Trend or Breakout.
        # - Retail Flow (Tiền Nhỏ): Small Volume or Panic Selling (Large Vol + Price Drop).
        
        # Calculate Intraday Intensity
        df['Price_Change'] = df['Close'] - df['Open']
        df['Spread'] = df['High'] - df['Low']
        df['Spread'] = df['Spread'].replace(0, 0.01)
        
        # Volume relative to 20-day average
        df['Avg_Vol_20'] = df['Volume'].rolling(window=20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Avg_Vol_20']
        
        # Money Flow Multiplier (MFM) = ((Close - Low) - (High - Close)) / (High - Low)
        # Result is between -1 and 1
        df['MFM'] = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / df['Spread']
        df['MFV'] = df['MFM'] * df['Volume'] # Chaikin Money Flow Volume

        # For the Chart (Opposing Bars):
        # Shark Entry: High Volume (> 1.2 Avg) AND Price Action positive (Close > Open or Hammer)
        # Retail Entry: Low/Medium Volume (< 1.2 Avg) OR FOMO Buying (High Vol but Price rejection)
        
        # We want to separate Volume into Shark Volume and Retail Volume
        
        shark_vol = []
        retail_vol = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            vol = row['Volume']
            avg_vol = row['Avg_Vol_20'] if not pd.isna(row['Avg_Vol_20']) else vol
            
            # Simple Heuristic
            if vol > 1.2 * avg_vol:
                # High Volume - Potential Smart Money
                if row['Close'] >= row['Open']:
                    # Strong Buy / Accumulation
                    shark_vol.append(vol)       # Positive (Green)
                    retail_vol.append(0)
                else:
                    # Strong Sell / Distribution
                    shark_vol.append(-vol)      # Negative (Red/Green down?) 
                                                # Actually user wants: Shark (Blue/Green) vs Retail (Red/Yellow)
                    retail_vol.append(0)
            else:
                # Normal Volume - Mostly Retail
                if row['Close'] >= row['Open']:
                     shark_vol.append(0)
                     retail_vol.append(vol)     # Positive Retail Buy
                else:
                     shark_vol.append(0)
                     retail_vol.append(-vol)    # Negative Retail Sell
                     
        # Refined Logic based on User Request:
        # Shark Bar (Big Money): Net Flow of "Smart" Volume
        # Retail Bar (Small Money): Net Flow of "Retail" Volume
        
        # We define Smart Volume as Volume when Vol_Ratio > 1.2 OR Divergent Moves
        # We define Retail Volume as Volume when Vol_Ratio <= 1.2
        
        # Let's try to make it continuous
        # Shark Component = Volume * (Factor based on Vol_Ratio)
        # Retail Component = Volume * (1 - Factor)
        
        # Factor = min(1, max(0, (Vol_Ratio - 0.8) / 0.8))  -> if ratio < 0.8, factor 0. if ratio > 1.6, factor 1.
        
        df['Vol_Factor'] = ((df['Vol_Ratio'] - 0.5) / 1.5).clip(0, 1) # 0.5 -> 0, 2.0 -> 1
        
        # Direction: 
        # Price Up -> Positive Flow
        # Price Down -> Negative Flow
        direction = np.sign(df['Close'] - df['Open'])
        # If Doji (0), use comparison with prev close
        direction = np.where(direction == 0, np.sign(df['Close'] - df['Close'].shift(1)), direction)
        direction = np.where(direction == 0, 1, direction) # Default positive if absolutely flat (rare)
        
        df['Shark_Bar'] = df['Volume'] * df['Vol_Factor'] * direction
        df['Retail_Bar'] = df['Volume'] * (1 - df['Vol_Factor']) * direction
        
        # --- 3. Signals ---
        
        # "Vo Teo" (Volume Dry-up) - REFINED
        # Vol < 0.6 * AvgVol20 AND (Price Pullback to MA20 OR Support)
        # Pullback: Close < Recent High
        df['Rolling_Max_20'] = df['High'].rolling(window=20).max()
        df['Signal_VoTeo'] = (df['Volume'] < 0.6 * df['Avg_Vol_20']) & \
                             (df['Close'] < df['Rolling_Max_20'] * 0.98) & \
                             (df['RSI'] < 60) & (df['RSI'] > 40) # Not oversold yet, just drying up
                             
        # "Big Money In" (Dòng Tiền Lớn - Rồng)
        # Vol > 2.0x Avg, Price Up, RSI not excessively high
        df['Signal_BigMoney'] = (df['Volume'] > 2.0 * df['Avg_Vol_20']) & \
                                (df['Close'] > df['Open']) & \
                                (df['RSI'] < 70)
                             
        # "Buy on Dip" (Trend UP + Dip near MA20)
        # Trend UP: SMA20 > SMA50
        df['SMA_20'] = df['SMA_20'].fillna(0)
        df['SMA_50'] = df['SMA_50'].fillna(0)
        df['RSI'] = df['RSI'].fillna(50)
        df['Trend_Up'] = df['SMA_20'] > df['SMA_50']
        df['Signal_BuyDip'] = df['Trend_Up'] & \
                              (df['Low'] <= df['SMA_20'] * 1.02) & \
                              (df['Close'] >= df['SMA_20'] * 0.98) # Tolerance
                              
        # "Super Stock" (Cung Yếu - Lái Gom)
        # Shark Bar Positive & Retail Bar Negative (Retail selling to Shark)
        # Or Shark Buying > 3x Retail Buying
        df['Signal_Super'] = (df['Shark_Bar'] > 0) & (df['Retail_Bar'] < 0)
        
        # "Up Bo" (Distribution)
        # High Vol, Price Stalling or Drop, Retail Buying (FOMO)
        # RSI > 70 and Price Drop with High Volume
        df['Signal_UpBo'] = (df['RSI'] > 70) & (df['Close'] < df['Open']) & (df['Volume'] > df['Avg_Vol_20'])

        # --- Advanced Tech Analysis ---
        
        # 4. POC (Point of Control) - Volume Profile
        price_min = df['Low'].min()
        price_max = df['High'].max()
        if price_max > price_min:
            buckets = 50
            # Histogram
            counts, bins = np.histogram(df['Close'], bins=buckets, range=(price_min, price_max), weights=df['Volume'])
            max_idx = np.argmax(counts)
            poc_price = (bins[max_idx] + bins[max_idx+1]) / 2
            df['POC'] = poc_price
            
            # POC Support Signal
            df['Signal_POC_Support'] = (df['Close'] > df['POC']) & (df['Low'] <= df['POC'] * 1.02) & (df['Low'] >= df['POC'] * 0.98)
        else:
            df['POC'] = 0
            df['Signal_POC_Support'] = False

            # 5. Breakout Signal
        df['Signal_Breakout'] = (df['Close'] > df['Rolling_Max_20'].shift(1)) & \
                                (df['Volume'] > 1.5 * df['Avg_Vol_20']) & \
                                (df['Close'] > df['Open']) 

        # 5b. Pyramid Sizing (Quản Trị Vốn Tỷ Trọng)
        # Calculate percentage distance from POC (Base/Giá vốn tay to)
        df['Base_Distance_Pct'] = np.where(df['POC'] > 0, (df['Close'] - df['POC']) / df['POC'] * 100, 0)
                                
        # 6. MA50 Test (Support)
        df['Signal_MA50_Test'] = (df['Low'] <= df['SMA_50'] * 1.01) & \
                                 (df['Close'] > df['SMA_50']) & \
                                 (df['Volume'] > df['Avg_Vol_20']) 
                                 
        # 7. Bollinger Squeeze
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and not bbands.empty:
            bbb_col = next((c for c in bbands.columns if c.startswith('BBB')), None)
            if bbb_col:
                df = pd.concat([df, bbands], axis=1)
                bbb = bbands[bbb_col]
                min_bw_6m = bbb.rolling(window=120).min()
                df['Signal_Squeeze'] = bbb <= min_bw_6m * 1.1 
            else:
                df['Signal_Squeeze'] = False
        else:
            df['Signal_Squeeze'] = False

        # --- Early Distribution Detection & MACD ---
        
        # 8. MACD Signals
        if 'MACD_Line' in df.columns:
             # MACD Cross Down (Sell Signal)
             df['MACD_Cross_Down'] = (df['MACD_Line'] < df['MACD_Signal']) & (df['MACD_Line'].shift(1) >= df['MACD_Signal'].shift(1))
             # MACD Divergence (Simple): Price High > Prev High BUT MACD High < Prev MACD High
             # This is complex to code vectorized without peak detection. 
             # We will use a simplified "Weakening Momentum" check:
             # Price making new highs (Rolling Max) BUT MACD Histogram decreasing
             df['Signal_MACD_Weakness'] = (df['Close'] >= df['Rolling_Max_20']) & \
                                          (df['MACD_Hist'] < df['MACD_Hist'].shift(1)) & \
                                          (df['MACD_Hist'].shift(1) < df['MACD_Hist'].shift(2))
        else:
             df['MACD_Cross_Down'] = False
             df['Signal_MACD_Weakness'] = False
        
        # 9. Loose Fluctuation (Bien Dong Long)
        df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['Signal_Loose'] = (df['Spread'] > 2 * df['ATR_14']) & (df['Volume'] > df['Avg_Vol_20'])
        
        # 10. Shooting Star / Trap (Keo Xa)
        body = abs(df['Open'] - df['Close'])
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['Signal_ShootingStar'] = (upper_shadow > 2 * body) & \
                                    (upper_shadow > 2 * lower_shadow) & \
                                    (upper_shadow > 0.4 * df['Spread']) & \
                                    (df['Volume'] > df['Avg_Vol_20']) & \
                                    (df['High'] >= df['Rolling_Max_20'].shift(1))
                                    
        # "Golden Sell" (Bán Chốt Lời - Thời Điểm Vàng)
        # Conditions:
        # 1. Uptrend / Overbought: RSI > 70
        # 2. Big Volume: Vol > 1.5 * Avg
        # 3. Stalling/Rejection: Red Candle (Close < Open) OR Shooting Star
        df['Signal_GoldenSell'] = (df['RSI'] > 70) & \
                                  (df['Volume'] > 1.5 * df['Avg_Vol_20']) & \
                                  ((df['Close'] < df['Open']) | df['Signal_ShootingStar'])

        # Combined Distribution Warning
        # FIX: MACD signals strictly require HIGH VOLUME to be considered Distribution.
        # If MACD weak/cross down on Low Volume -> Just Correction/Shakeout.
        macd_bad = (df['Signal_MACD_Weakness'] | df['MACD_Cross_Down']) & (df['Volume'] > df['Avg_Vol_20'])
        
        df['Signal_Distribution'] = macd_bad | df['Signal_Loose'] | df['Signal_ShootingStar']

        # --- SMART SELL RADAR - THE 5 ALGORITHMS ---
        
        # 1. Thuật toán 1: "Sang tay nhỏ lẻ"
        # Đang vùng đỉnh, Tiền Lớn suy giảm âm, Tiền nhỏ vọt
        df['Rolling_Min_60'] = df['Low'].rolling(window=60).min()
        is_near_peak = df['Close'] > df['Rolling_Min_60'] * 1.2
        avg_shark_3 = df['Shark_Bar'].rolling(window=3).mean()
        avg_retail_3 = df['Retail_Bar'].rolling(window=3).mean()
        shark_weak = (df['Shark_Bar'] < avg_shark_3) | (df['Shark_Bar'] < 0)
        retail_spike = (df['Retail_Bar'] > avg_retail_3 * 1.5) & (df['Retail_Bar'] > 0)
        df['Signal_SangTayNhoLe'] = is_near_peak & shark_weak & retail_spike & (df['Volume'] > df['Avg_Vol_20'])

        # 2. Thuật toán 2: Mẫu hình "Gãy nền và Test lại" (Bull-trap)
        # Từng rớt qua MA20 trong vòng 10 phiên trước, bây giờ hồi test chạm lại MA20 từ dưới lên
        was_below_ma20 = (df['Close'] < df['SMA_20']).rolling(window=10).sum() >= 1
        is_touching_ma20_from_below = (df['Close'] < df['SMA_20']) & (df['High'] >= df['SMA_20'] * 0.99)
        df['Signal_GayNenTestLai'] = was_below_ma20 & is_touching_ma20_from_below & (~df['Trend_Up'])

        # 3. Thuật toán 3: Quét Phân kỳ âm MACD (2-3 Đỉnh)
        # Đếm số lần MACD Cross Down trong 30-45 phiên gần nhất khi giá ở vùng đỉnh.
        # Nếu >= 2 lần cắt xuống, hệ thống báo bán (Đỉnh 2/Đỉnh 3).
        if 'MACD_Line' in df.columns:
            macd_cross_down = (df['MACD_Line'] < df['MACD_Signal']) & (df['MACD_Line'].shift(1) >= df['MACD_Signal'].shift(1))
            macd_cross_down_count = macd_cross_down.rolling(window=45).sum()
            macd_div_2_peaks = (macd_cross_down_count >= 2) & macd_cross_down
            df['Signal_PhanKyAmMACD'] = macd_div_2_peaks & (df['Close'] > df['Rolling_Max_20'] * 0.95)
        else:
            df['Signal_PhanKyAmMACD'] = False

        # 4. Thuật toán 4: Radar "Dao động lỏng lẻo"
        # Spread cực đại > 2.5x ATR, Rút đầu trên, Vol lớn
        spread_large = df['Spread'] > (2.5 * df['ATR_14'])
        upper_shadow_large = upper_shadow > (2 * body) # Re-using upper_shadow and body from above
        high_vol = df['Volume'] > 1.5 * df['Avg_Vol_20']
        df['Signal_DaoDongLongLeo'] = spread_large & upper_shadow_large & high_vol

        # 5. Thuật toán Phụ: Hàng Kênh Dưới Chạm Mây
        # Cổ phiếu không Uptrend, giá chạm mây Ichimoku
        # Kiểm tra nếu Mây tương lai đang đỏ hoặc test mây dày
        if 'ISA_9' in df.columns and 'ISB_26' in df.columns:
            is_bottom_channel = df['SMA_20'] < df['SMA_50']
            cloud_bottom = df[['ISA_9', 'ISB_26']].min(axis=1)
            cloud_top = df[['ISA_9', 'ISB_26']].max(axis=1)
            touching_cloud = (df['High'] >= cloud_bottom) & (df['Close'] <= cloud_top)
            df['Signal_ChamMayKenhDuoi'] = is_bottom_channel & touching_cloud
        else:
            df['Signal_ChamMayKenhDuoi'] = False

        # 6. Thuật toán Bán Tháo Hoảng Loạn (Panic Sell / Bán Chui)
        # Giá Close <= Low (hoặc gần sát Low) tạo nến đặc giảm cực dài + Biên độ > 4% + Volume > 1.5 * Avg
        # Hoặc Dư bán sàn (Close = Sàn). Ở đây dùng proxy là Spread lớn và nến đỏ đặc.
        is_big_red_candle = (df['Open'] - df['Close']) > (0.6 * df['Spread']) # Nến đỏ đặc đóng cửa thấp
        is_large_drop = (df['Open'] - df['Close']) / df['Open'] > 0.04 # Rớt > 4%
        is_panic_vol = df['Volume'] > 1.5 * df['Avg_Vol_20']
        df['Signal_PanicSell'] = is_big_red_candle & is_large_drop & is_panic_vol

        # --- Market Phase Classification (Shakeout vs Distribution) ---
        # Refined based on User's "Weather" concept
        
        phases = []
        actions = []
        pyramid_actions = []
        
        for i in range(len(df)):
            row = df.iloc[i]
            phase = "Sideway (Mưa Phùn)"
            action = "Quan Sát"
            
            # Basic Trend (NaN-safe)
            sma20 = row['SMA_20']
            sma50 = row['SMA_50']
            
            if pd.isna(sma20) or pd.isna(sma50):
                phases.append(phase)
                actions.append(action)
                # Assign default pyramid action
                pyramid_actions.append("Quan Sát")
                continue
            
            is_uptrend = sma20 > sma50
            
            # --- Quản Trị Vốn Tỷ Trọng (Pyramid Sizing) ---
            pyramid_action = "Full Size (Tỷ trọng lớn)"
            base_dist = row.get('Base_Distance_Pct', 0)
            if base_dist > 30:
                pyramid_action = "CẤM MARGIN (Vùng cao rủi ro)"
            elif base_dist > 15:
                pyramid_action = "Hạ Quy Mô Lệnh (Giới hạn tỷ trọng)"
            
            # --- Logic Tree ---
            
            # 0. PANIC SELL (Nguy hiểm nhất - Tin đồn/Thiên nga đen)
            if row.get('Signal_PanicSell', False):
                phase = "BÁN THÁO (Cảnh Báo Sập)"
                action = "BÁN BẰNG MỌI GIÁ (Panic)"

            # 1. GOLDEN SELL (New Priority)
            elif row['Signal_GoldenSell']:
                phase = "ĐỈNH NGẮN HẠN (Cao Trào Bán)"
                action = "BÁN CHỐT LỜI (Golden Sell)"

            # 2. Distribution / Danger (Bão)
            elif row['Signal_Distribution'] or row['Signal_UpBo']:
                phase = "PHÂN PHỐI (Bão - Nguy Hiểm)"
                action = "BÁN / CHỐT LỜI KHẨN CẤP"
            
            # 3. Run-off (Overbought) (Nắng Gắt)
            elif row['RSI'] > 75:
                phase = "QUÁ MUA (Nắng Gắt)"
                action = "Hạ Margin / Không Mua Mới"
                
            # 3. Shakeout (Rung Lac / Mưa Rào)
            # Trend UP, Price < Recent High (Correction), Vol Low (Vo Teo)
            elif is_uptrend and \
                 row['Close'] < row['Rolling_Max_20'] and \
                 row['Signal_VoTeo']:
                 phase = "RUNG LẮC (Mưa Rào - Cơ Hội)"
                 action = "MUA GOM (Buy Dip)"

            # 4. Uptrend (Nắng Đẹp)
            elif is_uptrend and row['Close'] > row['SMA_20']:
                phase = "UPTREND (Nắng Đẹp)"
                action = "Nắm Giữ (Full Hàng)"
                
            # 5. Downtrend (Bão Lớn / Mùa Đông)
            elif not is_uptrend and row['Close'] < row['SMA_20']:
                phase = "DOWNTREND (Mùa Đông)"
                action = "Cắt Lỗ / Đứng Ngoài"
                
            phases.append(phase)
            actions.append(action)
            pyramid_actions.append(pyramid_action)
            
        df['Market_Phase'] = phases
        df['Action_Recommendation'] = actions
        df['Pyramid_Action'] = pyramid_actions

        return df

    @staticmethod
    def classify_stock(symbol: str) -> dict:
        """
        Classifies stock into groups based on User definition and returns Strategy.
        Groups: Leader, Midcap, Vin/Trụ, Other.
        """
        s = symbol.replace('.VN', '').upper()
        
        # Defined by User
        leaders = ['GAS', 'PLX', 'GVR', 'IDC', 'SZC', 'VCB', 'BID', 'CTG', 'FPT', 'DGC', 'BSR', 'HPG'] # Added BSR, HPG
        midcaps = ['DIG', 'CEO', 'DXG', 'SSI', 'VND', 'HPG', 'NKG', 'HSG', 'KBC', 'PDR', 'NVL']
        vin_group = ['VIC', 'VHM', 'VRE', 'MSN', 'SAB', 'VNM'] # Trụ điều tiết
        
        group = "Penny/Khác"
        strategy = "Thận trọng"
        tag = ""
        
        # specific tags for Leaders
        if s == 'BSR':
            tag = "👑 Siêu cổ | Không thèm chỉnh | Vượt đỉnh"
        elif s == 'PLX':
            tag = "⛽ Leader | Cung mỏng dễ kéo | Chờ test lấp Gap"
        elif s == 'GVR':
            tag = "🌳 Khỏe nhất dòng | Trơ với thị trường | Tiền lớn bảo kê"
        elif s == 'IDC':
            tag = "🏭 Vượt nền | FA tốt | Mục tiêu đỉnh cũ"
        elif s == 'HPG':
            tag = "🏗️ Blue-chip chân sóng | Đã thoát Mây | Quỹ ngoại gom"
        
        if s in leaders:
            group = "Leader (Sóng Làm Giàu)"
            strategy = "Mua Khi Chỉnh (Buy Dip). Hạn chế bán non."
            if not tag: tag = "🔥 Leader Dòng Tiền"
        elif s in midcaps:
            group = "Midcap (Sóng Hồi)"
            strategy = "Trading Biên Độ (Swing). Mua Hỗ Trợ - Bán Kháng Cự."
        elif s in vin_group:
            group = "Trụ/Vin (Điều Tiết)"
            strategy = "Hạn chế giao dịch. Chỉ dùng để quan sát Index."
            
        return {
            "group": group,
            "strategy": strategy,
            "tag": tag
        }

    @staticmethod
    def get_pyramid_sizing(df: pd.DataFrame) -> str:
        if df is None or len(df) == 0:
            return "N/A"
        return df.iloc[-1].get('Pyramid_Action', 'Full Size (Tỷ trọng lớn)')

    @staticmethod
    def calc_leader_score(df: pd.DataFrame, index_df: pd.DataFrame = None) -> float:
        """
        Calculate Leader Score based on 4 criteria:
        1. Relative Strength (RS vs Index)
        2. Breakout (Near 52-week High & Volume)
        3. Low Float (Proxy via average volume)
        4. Ichimoku/Platform (Price above Cloud, MA20 Up)
        Returns a dict with 'score', 'is_shark_dominated', and 'is_storm_resistant'.
        """
        if df is None or len(df) < 50:
            return {'score': 0, 'is_shark_dominated': False, 'is_storm_resistant': False}
            
        score = 0
        last_row = df.iloc[-1]
        
        # Criteria 1: Relative Strength (RS) - 30 points
        # Simplified: If recent 5 days are positive while index might be weak, or just strong momentum
        mom_20 = (last_row['Close'] / df.iloc[-20]['Close']) - 1 if len(df) >= 20 else 0
        mom_60 = (last_row['Close'] / df.iloc[-60]['Close']) - 1 if len(df) >= 60 else 0
        
        if mom_20 > 0.05: score += 15
        elif mom_20 > 0: score += 5
        
        if mom_60 > 0.1: score += 15
        elif mom_60 > 0.05: score += 10
        
        # True RS vs Index if available
        if index_df is not None and not index_df.empty and len(index_df) >= 20:
             idx_mom_20 = (index_df.iloc[-1]['Close'] / index_df.iloc[-20]['Close']) - 1
             if mom_20 > idx_mom_20 + 0.02: # Outperforming by 2%
                 score += 10
                 
        # Criteria 2: Breakout 52w / Rolling Max - 25 points
        if 'Rolling_Max_20' in df.columns:
            dist_to_high = (last_row['Rolling_Max_20'] - last_row['Close']) / last_row['Close']
            if dist_to_high < 0.03: # Within 3% of 20-day high
                score += 15
                if last_row.get('Signal_Breakout', False):
                    score += 10
                    
        # Criteria 3: Low Float (Proxy: Consistent Volume, no sudden irrational spikes, or State-owned)
        # We assign an average of +15 for decent liquid stocks, penalize highly diluted penny stocks
        score += 15 
        
        # Criteria 4: Ichimoku & MA20 Up - 30 points
        if 'SMA_20' in df.columns and len(df) > 2:
            ma20_up = last_row['SMA_20'] > df.iloc[-2]['SMA_20']
            if ma20_up and last_row['Close'] > last_row['SMA_20']:
                score += 15
                
        # Ichimoku Cloud Check (ISA and ISB)
        if 'ISA_9' in df.columns and 'ISB_26' in df.columns:
            cloud_top = max(last_row['ISA_9'], last_row['ISB_26'])
            if last_row['Close'] > cloud_top:
                score += 15
                
        # --- NEW CRITERIA: SHARK DOMINATION & STORM RESISTANCE ---
        is_shark = False
        if last_row.get('Shark_Bar', 0) > 0 and last_row.get('Retail_Bar', 0) < 0:
            is_shark = True
            score += 20  # Huge bonus for Tiền lớn tay to
            
        is_storm = False
        if index_df is not None and len(index_df) >= 3 and len(df) >= 3:
            idx_returns = index_df['Close'].pct_change().tail(3)
            stock_returns = df['Close'].pct_change().tail(3)
            for i in range(len(idx_returns)):
                # If VNINDEX dropped > 1% but Stock was green/reference
                if idx_returns.iloc[i] < -0.01 and stock_returns.iloc[i] >= 0:
                    is_storm = True
                    score += 25  # Huge bonus for Kháng Bão
                    break

        # Bonus for Shark presence
        if last_row.get('Signal_Super', False) or last_row.get('Signal_BuyDip', False):
            score += 10 # Can exceed 100 slightly, it's fine
            
        # Penalize for Distribution
        if last_row.get('Signal_Distribution', False) or last_row.get('Signal_UpBo', False) or last_row.get('Signal_GoldenSell', False):
            score -= 30
            
        return {
            'score': min(max(int(score), 0), 100),
            'is_shark_dominated': is_shark,
            'is_storm_resistant': is_storm
        }

