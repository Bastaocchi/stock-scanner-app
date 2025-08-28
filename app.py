import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime

# ==============================
# CONFIG PÁGINA
# ==============================
st.set_page_config(
    page_title="Scanner TheStrat",
    page_icon="📊",
    layout="wide"
)

# ==============================
# CSS PARA MELHORAR DESIGN
# ==============================
st.markdown("""
<style>
/* aumenta fonte global */
html, body, [class*="css"]  {
    font-size: 18px !important;
}

/* aumenta labels dos inputs */
label {
    font-size: 20px !important;
    font-weight: bold;
}

/* aumenta botões */
button[kind="primary"], button[kind="secondary"] {
    font-size: 18px !important;
    font-weight: bold;
}

/* aumenta métricas */
[data-testid="stMetricValue"] {
    font-size: 28px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 18px !important;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÕES BASE
# ==============================
@st.cache_data(ttl=3600)
def load_symbols():
    return ["AAPL","MSFT","TSLA","AMZN","NVDA","META","GOOGL","NFLX","AMD","IBM"]

SYMBOLS = load_symbols()

@st.cache_data(ttl=3600)
def get_stock_data(symbol, period="1y", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        return None if df.empty else df
    except:
        return None

# ==============================
# THESTRAT CLASSIFICAÇÃO
# ==============================
def classify_strat_bar(curr, prev):
    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1"
    elif curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3"
    elif curr["High"] > prev["High"]:
        return "2U"
    elif curr["Low"] < prev["Low"]:
        return "2D"
    return None

def detect_strat_combo(df, lookback=3):
    if len(df) < lookback + 1:
        return None
    
    bars = []
    for i in range(-lookback, 0):
        curr, prev = df.iloc[i], df.iloc[i-1]
        bars.append(classify_strat_bar(curr, prev))
    
    pattern = "-".join(bars)

    combos = {
        "2U-1-2U": "Bullish 2-1-2 Continuation",
        "2D-1-2D": "Bearish 2-1-2 Continuation",
        "2U-1-2D": "2-1-2 Reversal Down",
        "2D-1-2U": "2-1-2 Reversal Up",
        "3-1-2U": "3-1-2 Bullish",
        "3-1-2D": "3-1-2 Bearish",
        "1-2U-2U": "1-2-2 Bullish",
        "1-2D-2D": "1-2-2 Bearish",
        "2U-2D": "2U-2D Reversal",
        "2D-2U": "2D-2U Reversal"
    }
    return combos.get(pattern, None)

# ==============================
# APP PRINCIPAL
# ==============================
def main():
    # ======== FILTROS NO TOPO ========
    col1, col2, col3 = st.columns([2,3,2])

    with col1:
        timeframes = {
            "1D": ("1y", "1d"),
            "1W": ("2y", "1wk"),
            "1M": ("5y", "1mo")
        }
        timeframe = st.radio("Timeframe", list(timeframes.keys()), horizontal=True)

    with col2:
        setups = {
            "Inside Bar": st.checkbox("Inside Bar", value=True),
            "Hammer": st.checkbox("Hammer Setup", value=False),
            "2D Green": st.checkbox("2D Green Monthly", value=False),
            "Combos": st.checkbox("TheStrat Combos", value=True)
        }

    with col3:
        run = st.button("Iniciar Scanner", use_container_width=True)

    st.markdown("---")

    # ======== LOOP PRINCIPAL ========
    if run:
        period, interval = timeframes[timeframe]

        colm1, colm2, colm3 = st.columns(3)
        processed_metric = colm1.metric("Processados", "0")
        found_metric = colm2.metric("Setups", "0")
        progress_metric = colm3.metric("Progresso", "0%")

        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        results = []

        for i, symbol in enumerate(SYMBOLS):
            status_placeholder.text(f"Analisando {symbol}...")
            df = get_stock_data(symbol, period, interval)
            if df is not None and len(df) > 5:
                curr, prev = df.iloc[-1], df.iloc[-2]

                # Inside Bar
                if setups["Inside Bar"]:
                    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
                        results.append({"Symbol": symbol,"Setup": "Inside Bar","Price": f"${curr['Close']:.2f}","Date": df.index[-1].strftime("%Y-%m-%d")})

                # Hammer
                if setups["Hammer"]:
                    body = abs(curr["Close"] - curr["Open"])
                    total = curr["High"] - curr["Low"]
                    lower_shadow = min(curr["Open"], curr["Close"]) - curr["Low"]
                    if body <= 0.4*total and lower_shadow >= 2*body and curr["Close"] > curr["Open"] and curr["Low"] < prev["Low"]:
                        results.append({"Symbol": symbol,"Setup": "Hammer Setup","Price": f"${curr['Close']:.2f}","Date": df.index[-1].strftime("%Y-%m-%d")})

                # 2D Green Monthly
                if setups["2D Green"] and interval == "1mo":
                    if curr["Low"] < prev["Low"] and curr["Close"] > curr["Open"] and curr["High"] <= prev["High"]:
                        results.append({"Symbol": symbol,"Setup": "2D Green Monthly","Price": f"${curr['Close']:.2f}","Date": df.index[-1].strftime("%Y-%m-%d")})

                # Combos
                if setups["Combos"]:
                    combo = detect_strat_combo(df, lookback=3)
                    if combo:
                        results.append({"Symbol": symbol,"Setup": combo,"Price": f"${curr['Close']:.2f}","Date": df.index[-1].strftime("%Y-%m-%d")})

            # Atualiza métricas
            progress = (i+1)/len(SYMBOLS)
            progress_bar.progress(progress)
            processed_metric.metric("Processados", str(i+1))
            found_metric.metric("Setups", str(len(results)))
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            time.sleep(0.05)

        status_placeholder.text("Scanner concluído!")

        if results:
            st.success(f"{len(results)} setups encontrados!")
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True)
            csv = df_results.to_csv(index=False)
            st.download_button("Baixar CSV", csv,
                               file_name=f"strat_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")
        else:
            st.warning("Nenhum setup encontrado.")

if __name__ == "__main__":
    main()
