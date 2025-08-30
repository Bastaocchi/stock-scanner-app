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
    """Detecta 2Down Green Monthly na barra atual em andamento"""
    if df is None or df.empty:
        return False, None

    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

    df.columns = [str(c).lower() for c in df.columns]
    if "close" not in df.columns and "adj close" in df.columns:
        df["close"] = df["adj close"]

    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return False, None

    df_monthly = df.resample("M").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    })

    if len(df_monthly) < 2:
        return False, None

    current = df_monthly.iloc[-1]   # barra atual (em andamento)
    previous = df_monthly.iloc[-2]  # barra anterior

    open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
        float(current["open"]),
        float(current["high"]),
        float(current["low"]),
        float(current["close"])
    )
    low_prev = float(previous["low"])

    broke_down = low_curr < low_prev
    closed_green = close_curr > open_curr

    if broke_down and closed_green:
        break_amount = low_prev - low_curr
        break_pct = (break_amount / low_prev) * 100 if low_prev else 0
        monthly_change = ((close_curr - open_curr) / open_curr) * 100 if open_curr else 0

        return True, {
            "type": "2Down Green Monthly",
            "price": round(close_curr, 2),
            "day_change": ((close_curr - open_curr) / open_curr) * 100,
            "valid": valid_flag,
            "break_pct": round(break_pct, 2),
            "monthly_change_pct": round(monthly_change, 2)
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
    timeframe_filter = col3.selectbox("⏳ Timeframe", ["Daily", "Weekly", "Monthly"])

    if timeframe_filter == "Daily":
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar"])
    elif timeframe_filter == "Weekly":
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar"])
    else:  # Monthly
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar", "2Down Green Monthly"])

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

            found, info = False, None

            if timeframe_filter == "Daily":
                if setup_filter == "Inside Bar":
                    found, info = detect_inside_bar(df)

            elif timeframe_filter == "Weekly":
                df_weekly = df.resample("W").agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last"
                })
                if setup_filter == "Inside Bar":
                    found, info = detect_inside_bar(df_weekly)

            elif timeframe_filter == "Monthly":
                if setup_filter == "Inside Bar":
                    df_monthly = df.resample("M").agg({
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last"
                    })
                    found, info = detect_inside_bar(df_monthly)
                elif setup_filter == "2Down Green Monthly":
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

                if setup_filter == "2Down Green Monthly" and info:
                    row["break_pct"] = info.get("break_pct", "")
                    row["monthly_change_pct"] = info.get("monthly_change_pct", "")

                results.append(row)

            progress = (i + 1) / len(SYMBOLS)
            progress_bar.progress(progress)
            status_text.text(f"⏳ {i+1}/{len(SYMBOLS)} símbolos... | 🎯 {len(results)} setups")

        progress_bar.empty()
        status_text.empty()

        if results:
            df_results = pd.DataFrame(results)

            if setor_filter != "Todos":
                df_results = df_results[df_results["sector_spdr"] == setor_filter]
            if tag_filter != "Todos":
                df_results = df_results[df_results["tags"] == tag_filter]

            render_results_table(df_results)
        else:
            st.warning(f"❌ Nenhum setup encontrado em {timeframe_filter} - {setup_filter}")


if __name__ == "__main__":
    main()
