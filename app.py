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

st.markdown('<h1 style="text-align:center;">Scanner TheStrat 📊</h1>', unsafe_allow_html=True)

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
    # ======== CONTROLES NO TOPO ========
    st.markdown("### ⚙️ Configurações")
    col1, col2, col3 = st.columns([2,2,2])

    with col1:
        timeframes = {
            "Daily (1D)": ("1y", "1d"),
            "Weekly (1W)": ("2y", "1wk"),
            "Monthly (1M)": ("5y", "1mo")
        }
        selected_timeframe = st.selectbox("⏳ Timeframe", list(timeframes.keys()), index=0)

    with col2:
        max_symbols = st.slider("📈 Máximo de símbolos", 5, len(SYMBOLS), min(50, len(SYMBOLS)))

    with col3:
        st.markdown("### 🧩 Setups para Detectar")
        detect_inside_bar = st.checkbox("Inside Bar (1)", value=True)
        detect_hammer = st.checkbox("Hammer Setup", value=False)
        detect_2d_green = st.checkbox("2D Green Monthly", value=False)
        detect_combos = st.checkbox("TheStrat Combos (2-1-2, 3-1-2...)", value=True)

    start_button = st.button("🚀 Iniciar Scanner", use_container_width=True)

    st.markdown("---")

    if start_button:
        period, interval = timeframes[selected_timeframe]

        # ======== MÉTRICAS ========
        colm1, colm2, colm3 = st.columns(3)
        processed_metric = colm1.metric("Processados", "0")
        found_metric = colm2.metric("Setups", "0")
        progress_metric = colm3.metric("Progresso", "0%")

        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        results = []

        # ======== LOOP PRINCIPAL ========
        for i, symbol in enumerate(SYMBOLS[:max_symbols]):
            status_placeholder.text(f"🔍 Analisando {symbol}...")
            df = get_stock_data(symbol, period, interval)
            if df is not None and len(df) > 5:
                # --- Inside Bar
                if detect_inside_bar:
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Inside Bar (1)",
                            "Price": f"${curr['Close']:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })
                # --- Hammer Setup (simples exemplo)
                if detect_hammer:
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    body = abs(curr["Close"] - curr["Open"])
                    total = curr["High"] - curr["Low"]
                    lower_shadow = min(curr["Open"], curr["Close"]) - curr["Low"]
                    if body <= 0.4*total and lower_shadow >= 2*body and curr["Close"] > curr["Open"] and curr["Low"] < prev["Low"]:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Hammer Setup",
                            "Price": f"${curr['Close']:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })
                # --- 2D Green Monthly
                if detect_2d_green and interval == "1mo":
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    if curr["Low"] < prev["Low"] and curr["Close"] > curr["Open"] and curr["High"] <= prev["High"]:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "2D Green Monthly",
                            "Price": f"${curr['Close']:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })
                # --- Combos
                if detect_combos:
                    combo = detect_strat_combo(df, lookback=3)
                    if combo:
                        results.append({
                            "Symbol": symbol,
                            "Setup": combo,
                            "Price": f"${df.iloc[-1]['Close']:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

            progress = (i+1)/max_symbols
            progress_bar.progress(progress)
            processed_metric.metric("Processados", str(i+1))
            found_metric.metric("Setups", str(len(results)))
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            time.sleep(0.05)

        status_placeholder.text("✅ Scanner concluído!")

        # ======== RESULTADOS ========
        if results:
            st.success(f"{len(results)} setups encontrados!")
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True)

            csv = df_results.to_csv(index=False)
            st.download_button("📥 Baixar CSV", csv,
                               file_name=f"strat_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")
        else:
            st.warning("Nenhum setup encontrado.")

if __name__ == "__main__":
    main()
