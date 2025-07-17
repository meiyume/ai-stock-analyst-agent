# streamlit_ta.py

import streamlit as st
from streamlit_ta_global import render_global_tab
from streamlit_ta_market import render_market_tab
# from streamlit_ta_sector import render_sector_tab
# from streamlit_ta_commodity import render_commodity_tab
# from streamlit_ta_stock import render_stock_tab

st.set_page_config(page_title="AI Technical Analysis Platform", page_icon="🌍")
st.title("🌍 AI Technical Analysis Platform")

tabs = st.tabs([
    "Market",
    "Global",
    # "Sector",
    # "Commodity",
    # "Stock"
])

with tabs[0]:
    render_market_tab()

with tabs[1]:
    render_global_tab()

# with tabs[2]: render_sector_tab()
# with tabs[3]: render_commodity_tab()
# with tabs[4]: render_stock_tab()

# ---- End ----








