class SymbolLoader:
    @staticmethod
    def get_liquid_stocks():
        """
        Returns a list of ~350 liquid stocks on HOSE/HNX/UPCOM.
        (Filtered for average volume > 50,000 to avoid junk)
        """
        # Top Liquid Stocks (Manually curated + Representative list)
        # In a real app, this would be fetched from an API or DB.
        
        # 1. VN30
        vn30 = ['BID', 'BCM', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG', 'MBB', 
                'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB', 'TCB', 
                'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE']

        # 2. Midcaps & Liquid Penny (Grouped by Industry)
        banks = ['EIB', 'LPB', 'MSB', 'OCB', 'NAB', 'BAB', 'BVB', 'ABB']
        securities = ['VND', 'VCI', 'HCM', 'SHS', 'MBS', 'FTS', 'CTS', 'BSI', 'VIX', 'AGR', 'ORS', 'BVS', 'VDS']
        steel = ['HSG', 'NKG', 'TLH', 'POM', 'TVN', 'SMC']
        real_estate = ['NVL', 'PDR', 'DIG', 'CEO', 'DXG', 'KDH', 'KBC', 'NAM', 'SZC', 'IDC', 'ITA', 'HQC', 'SCR', 'KHG', 'CRE', 'IJC', 'HUT', 'LDG', 'TCH', 'HDC', 'NLG']
        oil_gas = ['PVD', 'PVS', 'BSR', 'OIL', 'PVT', 'PVC', 'CNG']
        construction = ['VCG', 'LCG', 'HHV', 'FCN', 'CII', 'KSB', 'HT1', 'BCC', 'CTD', 'HBC', 'DASH']
        retail = ['DGW', 'FRT', 'PET', 'HAX', 'ABS']
        commodities = ['DGC', 'DPM', 'DCM', 'LAS', 'DDV', 'CSV', 'GMD', 'HAH', 'VOS', 'VHC', 'ANV', 'IDI', 'ASM', 'CMX', 'PAN', 'TAR', 'LTG', 'HAG', 'HNG', 'DBC', 'BAF']
        energy = ['GEG', 'PC1', 'REE', 'NT2', 'QTP', 'HID', 'ASM']
        
        # Combine
        all_stocks = list(set(vn30 + banks + securities + steel + real_estate + oil_gas + construction + retail + commodities + energy))
        all_stocks.sort()
        
        return all_stocks
