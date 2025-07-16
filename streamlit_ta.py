import streamlit as st
from agents.ta_global import ta_global

st.set_page_config(page_title="DEBUG: Global TA Raw Output", page_icon="🔍")
st.title("Debug: Global Technical Analyst Data Output")

# --- Call ta_global and display result ---
with st.spinner("Calling ta_global()..."):
    summary = ta_global()

st.subheader("Summary Keys")
st.write(list(summary.keys()))

# --- Show the full summary dict ---
st.subheader("Full Summary (expand to view)")
with st.expander("Show raw summary dict"):
    st.json(summary)

out = summary.get("out", {})

st.subheader("Keys in summary['out']")
st.write(list(out.keys()))

major_indices = ["S&P500", "Nasdaq", "EuroStoxx50", "Nikkei", "HangSeng", "FTSE100"]

st.subheader("Major Indices Data Dump")
for idx in major_indices:
    st.markdown(f"**{idx}**")
    st.write(out.get(idx, f"(No data found for key: {idx})"))

st.info("Review the keys and data above. If you see '(No data found for key: ...)', there may be a key mismatch. If you see error messages in the values, it's a backend data fetch problem.")

# Optionally, print everything in 'out' for further inspection
st.subheader("Full Index Data")
for k, v in out.items():
    st.markdown(f"**{k}**")
    st.write(v)
