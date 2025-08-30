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
th:nth-child(6), td:nth-child(6) { width: 150px !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# FUNÇÕES DE SCAN
# =========================
def fix_candle(open_p, high_p, low_p, close_p):
    valid_flag = "OK"
    if open_p > high_p:
        high_p = open_p
        valid_flag = "Adjusted"
    if open_p < low_p:
        low_p = open_p
        valid_flag = "Adjusted"
    return open_p, high_p, low_p, close_p, valid_flag


def detect_inside_bar(df):
    if len(df) < 2:
        return False, None

    current = df.iloc[-1]
    previous = df.iloc[-2]

    open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
        float(current["Open"]),
        float(current["High"]),
        float(current["Low"]),
        float(current["Close"])
    )
    high_prev, low_prev = float(previous["High"]), float(previous["Low"])

    if high_curr < high_prev and low_curr > low_prev:
        return True, {
            "type": "Inside Bar",
            "price": close_curr,
            "day_change": ((close_curr - open_curr) / open_curr) * 100,
            "valid": valid_flag
        }
    return False, None


def detect_2down_green_monthly(df):
    if df is None or df.empty:
        return False, None

    # 🔹 Garantir índice datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

    # 🔹 Padronizar nomes das colunas para minúsculo
    df.columns = [c.lower() for c in df.columns]

    # 🔹 Se não existir 'close', usar 'adj close'
    if "close" not in df.columns and "adj close" in df.columns:
        df["close"] = df["adj close"]

    # 🔹 Verificar se temos todas as OHLC
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return False, None

    # 🔹 Resample para candles mensais
    df_monthly = df.resample("M").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last"
    })

    if len(df_monthly) < 2:
        return False, None

    current = df_monthly.iloc[-1]
    previous = df_monthly.iloc[-2]

    open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
        float(current["open"]),
        float(current["high"]),
        float(current["low"]),
        float(current["close"])
    )
    low_prev, high_prev = float(previous["low"]), float(previous["high"])

    # 📌 Condições TheStrat
    broke_down = low_curr < low_prev        # rompeu mínima anterior
    closed_green = close_curr > open_curr   # candle verde
    no_break_high = high_curr < high_prev   # não rompeu máxima anterior

    if broke_down and closed_green and no_break_high:
        return True, {
            "type": "2Down Green Monthly",
            "price": close_curr,
            "day_change": ((close_curr - open_curr) / open_curr) * 100,
            "valid": valid_flag
        }
    return False, None


@st.cache_data(ttl=3600)
def get_stock_data(symbol, period="1y", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False)
        return df if not df.empty else None
    except:
        return None


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
            color = "#ffcc00" if col == "setup" else "#eee"
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

    # =========================
    # FILTROS NO TOPO
    # =========================
    col1, col2, col3, col4 = st.columns([1,1,1,2])

    setores = ["Todos"] + sorted(df_symbols["sector_spdr"].dropna().unique().tolist()) if "sector_spdr" in df_symbols else ["Todos"]
    tags = ["Todos"] + sorted(df_symbols["tags"].dropna().unique().tolist()) if "tags" in df_symbols else ["Todos"]

    setor_filter = col1.selectbox("📌 Setor", setores)
    tag_filter = col2.selectbox("🏷️ Tag", tags)
    setup_filter = col3.selectbox("⚡ Setup", ["Todos", "Inside Bar", "2Down Green Monthly"])
    search_filter = col4.text_input("🔍 Busca global")

    # =========================
    # BOTÃO SCANNER
    # =========================
    if st.button("🚀 Rodar Scanner"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        SYMBOLS = df_symbols["symbols"].dropna().tolist()

        for i, symbol in enumerate(SYMBOLS):
            df = get_stock_data(symbol)
            if df is None or len(df) < 3:
                continue

            found, info = detect_inside_bar(df)
            if found:
                row = {
                    "symbol": symbol,
                    "setup": info["type"],
                    "price": f"${info['price']:.2f}",
                    "day%": f"{info['day_change']:.2f}%",
                    "valid": info["valid"],
                    "sector_spdr": df_symbols.loc[df_symbols["symbols"] == symbol, "sector_spdr"].values[0] if "sector_spdr" in df_symbols else "",
                    "tags": df_symbols.loc[df_symbols["symbols"] == symbol, "tags"].values[0] if "tags" in df_symbols else ""
                }
                results.append(row)
            else:
                found, info = detect_2down_green_monthly(df)
                if found:
                    row = {
                        "symbol": symbol,
                        "setup": info["type"],
                        "price": f"${info['price']:.2f}",
                        "day%": f"{info['day_change']:.2f}%",
                        "valid": info["valid"],
                        "sector_spdr": df_symbols.loc[df_symbols["symbols"] == symbol, "sector_spdr"].values[0] if "sector_spdr" in df_symbols else "",
                        "tags": df_symbols.loc[df_symbols["symbols"] == symbol, "tags"].values[0] if "tags" in df_symbols else ""
                    }
                    results.append(row)

            progress = (i + 1) / len(SYMBOLS)
            progress_bar.progress(progress)
            status_text.text(f"⏳ {i+1}/{len(SYMBOLS)} símbolos... | 🎯 {len(results)} setups")

        progress_bar.empty()
        status_text.empty()

        if results:
            df_results = pd.DataFrame(results)

            # APLICAR FILTROS
            if setor_filter != "Todos":
                df_results = df_results[df_results["sector_spdr"] == setor_filter]
            if tag_filter != "Todos":
                df_results = df_results[df_results["tags"] == tag_filter]
            if setup_filter != "Todos":
                df_results = df_results[df_results["setup"] == setup_filter]
            if search_filter:
                mask = df_results.apply(lambda row: row.astype(str).str.contains(search_filter, case=False).any(), axis=1)
                df_results = df_results[mask]

            render_results_table(df_results)
        else:
            st.warning("❌ Nenhum setup encontrado.")


if __name__ == "__main__":
    main()
