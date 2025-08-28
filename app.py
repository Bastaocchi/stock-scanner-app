import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.markdown("<h1 style='text-align:center;'>📊 Scanner TheStrat</h1>", unsafe_allow_html=True)

# ======== FILTROS NO TOPO ========
col1, col2, col3 = st.columns([2,2,2])

with col1:
    timeframe = st.selectbox("⏳ Timeframe", ["1D","1W","1M"])

with col2:
    setups = st.multiselect("🧩 Setups", ["Inside Bar", "Hammer", "2D Green", "Combos"], default=["Inside Bar"])

with col3:
    run = st.button("🚀 Iniciar Scanner", use_container_width=True)

st.markdown("---")

# ======== MÉTRICAS ========
colA, colB, colC = st.columns(3)
colA.metric("Processados", "120")
colB.metric("Setups", "18")
colC.metric("Progresso", "60%")

# ======== RESULTADOS ========
if run:
    data = {
        "Symbol": ["AAPL","MSFT","TSLA"],
        "Setup": ["Inside Bar","Hammer","2-1-2 Bullish"],
        "Price": ["$180.32","$342.10","$256.44"]
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
