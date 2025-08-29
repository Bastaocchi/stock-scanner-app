import streamlit as st
import yfinance as yf
import pandas as pd
import time

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(
    page_title="Scanner de Setups - Estilo Gerenciador",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# CSS GLOBAL (Gerenciador)
# =========================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
}
table, th, td {
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    border: none !important;
    outline: none !important;
}
table {
    width: 100% !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
}
th {
    background-color: #2a323b !important;
    color: white !important;
    font-size: 20px !important;
    font-weight: bold !important;
    text-align: center !important;
    padding: 12px !important;
}
td {
    font-size: 18px !important;
    text-align: center !important;
    color: #eee !important;
    padding: 10px !important;
}
tr:nth-child(odd) { background-color: #15191f !important; }
tr:nth-child(even) { background-color: #1b1f24 !important; }
th:nth-child(1), td:nth-child(1) { width: 120px !important; }
th:nth-child(2), td:nth-child(2) { width: 200px !important; }
th:nth-child(3), td:nth-child(3) { width: 150px !important; }
th:nth-child(4), td:nth-child(4) { width: 150px !important; }
th:nth-child(5), td:nth-child(5) { width: 150px !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# FUNÇÕES DE SCAN
# =========================
def detect_inside_bar(df):
    if len(df) < 2:
        return False, None

    current = df.iloc[-1]
    previous = df.iloc[-2]

    high_curr, low_curr = float(current["High"]), float(current["Low"])
    high_prev, low_prev = float(previous["High"]), float(previous["Low"])
    open_curr, close_curr = float(current["Open"]), float(current["Close"])

    if high_curr < high_prev and low_curr > low_prev:
        return True, {
            "type": "Inside Bar",
            "price": close_curr,
            "day_change": ((close_curr - open_curr) / open_curr) * 100
        }
    return False, None


def detect_hammer_setup(df):
    if len(df) < 3:
        return False, None

    current = df.iloc[-1]
    previous = df.iloc[-2]

    open_curr, close_curr = float(current["Open"]), float(current["Close"])
    high_curr, low_curr = float(current["High"]), float(current["Low"])
    low_prev = float(previous["Low"])

    body_size = abs(close_curr - open_curr)
    total_range = high_curr - low_curr
    lower_shadow = min(open_curr, close_curr) - low_curr
    upper_shadow = high_curr - max(open_curr, close_curr)

    is_small_body = body_size <= 0.4 * total_range
    is_long_lower_shadow = lower_shadow >= 2 * body_size
    is_short_upper_shadow = upper_shadow <= body_size
    broke_below = low_curr < low_prev
    closed_green = close_curr > open_curr

    if is_small_body and is_long_lower_shadow and is_short_upper_shadow and broke_below and closed_green:
        return True, {
            "type": "Hammer Setup",
            "price": close_curr,
            "day_change": ((close_curr - open_curr) / open_curr) * 100
        }
    return False, None


@st.cache_data(ttl=3600)
def get_stock_data(symbol, period="1y", interval="1d"):
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False   # 🔹 OHLC real, sem ajuste
        )
        return df if not df.empty else None
    except:
        return None


# 🔹 Carregar símbolos do GitHub
@st.cache_data(ttl=3600)
def load_symbols_from_github():
    url = "https://raw.githubusercontent.com/Bastaocchi/stock-scanner-app/main/symbols.csv"
    df = pd.read_csv(url)
    return df


def render_results_table(df):
    html_table = "<table style='width:100%; border-collapse: collapse;'>"
    html_table += "<tr>" + "".join(f"<th>{col}</th>" for col in df.columns) + "</tr>"
    for idx, row in df.iterrows():
        bg_color = "#15191f" if idx % 2 == 0 else "#1b1f24"
        html_table += f"<tr style='background-color:{bg_color};'>"
        for col in df.columns:
            value = str(row[col]) if pd.notna(row[col]) else ""
            color = "#ffcc00" if col == "Setup" else "#eee"
            html_table += f"<td style='color:{color};'>{value}</td>"
        html_table += "</tr>"
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)


# =========================
# MAIN
# =========================
def main():
    st.markdown('<h2 style="color:#ccc;">🎯 Scanner de Setups (Estilo Gerenciador)</h2>', unsafe_allow_html=True)

    # Carregar lista de símbolos do GitHub
    df_symbols = load_symbols_from_github()
    df_symbols.columns = df_symbols.columns.str.strip().str.lower()

    st.info(f"✅ Carregados {len(df_symbols)} símbolos do GitHub")

    if "symbols" in df_symbols.columns:
        SYMBOLS = df_symbols["symbols"].dropna().tolist()
    elif "symbol" in df_symbols.columns:
        SYMBOLS = df_symbols["symbol"].dropna().tolist()
    else:
        st.error("❌ O CSV precisa ter uma coluna chamada 'symbols' ou 'symbol'")
        return

    if st.button("🚀 Rodar Scanner"):
        results = []

        # Barra de progresso discreta
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, symbol in enumerate(SYMBOLS):
            df = get_stock_data(symbol)
            if df is None or len(df) < 3:
                continue

            found, info = detect_inside_bar(df)
            if found:
                results.append({
                    "Symbol": symbol,
                    "Setup": info["type"],
                    "Price": f"${info['price']:.2f}",
                    "Day%": f"{info['day_change']:.2f}%"
                })
                continue

            found, info = detect_hammer_setup(df)
            if found:
                results.append({
                    "Symbol": symbol,
                    "Setup": info["type"],
                    "Price": f"${info['price']:.2f}",
                    "Day%": f"{info['day_change']:.2f}%"
                })

            # Atualizar progresso + setups em tempo real
            progress = (i + 1) / len(SYMBOLS)
            progress_bar.progress(progress)
            status_text.text(
                f"⏳ Processando {i+1}/{len(SYMBOLS)} símbolos... | 🎯 {len(results)} setups encontrados"
            )
            time.sleep(0.05)  # permite a UI atualizar

        # Limpar barra no final
        progress_bar.empty()
        status_text.empty()

        if results:
            df_results = pd.DataFrame(results)
            render_results_table(df_results)
        else:
            st.warning("❌ Nenhum setup encontrado.")


if __name__ == "__main__":
    main()
