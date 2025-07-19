import wbdata
import datetime
import pandas as pd

ASEAN_CODES = ["SGP", "MYS", "IDN", "THA", "PHL", "VNM", "BRN", "KHM", "LAO", "MMR"]
ASIA_CODES = ["SGP", "MYS", "IDN", "THA", "PHL", "VNM", "CHN", "IND", "KOR", "JPN", "HKG", "TWN"]

def get_macro_data(countries=None):
    if countries is None:
        countries = ["SGP"]
    indicators = {
        "NY.GDP.MKTP.KD.ZG": "gdp_growth",
        "FP.CPI.TOTL.ZG": "cpi_inflation"
    }
    data = wbdata.get_dataframe(indicators, country=countries,
                               data_date=datetime.datetime(2023, 1, 1))
    macro_data = {}
    if not data.empty:
        for c in countries:
            try:
                recent = data.xs(c).iloc[-1]
                macro_data[c] = {
                    "gdp_growth": f"{recent.get('gdp_growth', ''):.2f}%" if not pd.isna(recent.get('gdp_growth')) else "",
                    "cpi_inflation": f"{recent.get('cpi_inflation', ''):.2f}%" if not pd.isna(recent.get('cpi_inflation')) else "",
                }
            except Exception:
                macro_data[c] = {"gdp_growth": "", "cpi_inflation": ""}
    return macro_data

def get_macro_data_asean():
    return get_macro_data(ASEAN_CODES)

def get_macro_data_asia():
    return get_macro_data(ASIA_CODES)
