import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(
    page_title="Scanner TheStrat",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# CSS GLOBAL
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
    font-size: 18px !important;
    font-weight: bold !important;
    text-align: center !important;
    padding: 10px !important;
}
td {
    font-size: 16px !important;
    text-align: center !important;
    color: #eee !important;
    padding: 8px !important;
}
tr:nth-child(odd) { background-color: #15191f !important; }
tr:nth-child(even) { background-color: #1b1f24 !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO COM GOOGLE SHEETS
# =========================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["google_sheets"]), scope)
client = gspread.authorize(creds)

SHEET_ID = "1NMCkkcrTFOm1ZoOiImzzRRFd6NEn5kMPTkuc5j_3DcQ"
worksheet = client.open_by_key(SHEET_ID).sheet1  # primeira aba

# =========================
# FUNÇÕES AUXILIARES
# =========================
def ensure_ohlc(df):
    """Garante que o DataFrame só tenha colunas OHLC com nomes limpos"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Open","High","Low","Close"])
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    keep_cols = [c for c in ["Open","High","Low","Close"] if c in df.columns]
    df = df[keep_cols]
    df = df.dropna()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df

def detect_strat(df):
    """Detecta setups TheStrat na última vela"""
    if df is None or len(df) < 2:
        return None

    df = ensure_ohlc(df)
    if len(df) < 2:
        return None

    c, p = df.iloc[-1], df.iloc[-2]

    try:
        c_high, c_low = float(c["High"]), float(c["Low"])
        p_high, p_low = float(p["High"]), float(p["Low"])
    except Exception:
        return None

    if c_high < p_high and c_low > p_low:
        return "1"   # Inside bar
    elif c_high > p_high and c_low >= p_low:
        return "2u"  # Two Up
    elif c_low < p_low and c_high <= p_high:
        return "2d"  # Two Down
    elif c_high > p_high and c_low < p_low:
        return "3"   # Outside
    return ""

def calc_atr(df, period=14):
    """Calcula ATR"""
    df = ensure_ohlc(df)
    if df.empty: 
        return None
    df["H-L"] = df["High"] - df["Low"]
    df["H-C"] = abs(df["High"] - df["Close"].shift())
    df["L-C"] = abs(df["Low"] - df["Close"].shift())
    tr = df[["H-L", "H-C", "L-C"]].max(axis=1)
    atr = tr.rolling(period).mean()
    return atr.iloc[-1] if not atr.empty else None

def load_symbols():
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if "Symbol" not in df.columns:
        st.error("❌ A planilha precisa ter a coluna 'Symbol'")
        return []
    return df["Symbol"].dropna().unique().tolist()

def color_setup(value):
    mapping = {
        "1": "#FFD700",   # amarelo
        "2u": "#00FF00",  # verde
        "2d": "#FF4500",  # vermelho
        "3": "#1E90FF"    # azul
    }
    return mapping.get(str(value), "#eee")

# =========================
# MAIN APP
# =========================
def main():
    st.markdown('<h4 style="text-align:left; font-size:1.2rem; margin-bottom:1rem; color: #ccc;">Scanner TheStrat</h4>', unsafe_allow_html=True)

    symbols = load_symbols()
    st.info(f"Analisando {len(symbols)} símbolos da planilha")

    results = []

    for sym in symbols[:50]:
        try:
            data_day = ensure_ohlc(yf.download(sym, period="6mo", interval="1d", progress=False))
            data_wk  = ensure_ohlc(yf.download(sym, period="1y", interval="1wk", progress=False))
            data_mo  = ensure_ohlc(yf.download(sym, period="5y", interval="1mo", progress=False))

            if data_day.empty or data_wk.empty or data_mo.empty:
                continue

            setup_day = detect_strat(data_day)
            setup_wk = detect_strat(data_wk)
            setup_mo = detect_strat(data_mo)

            # Qtr
            data_qtr = data_mo.resample("Q").agg({
                "Open":"first","High":"max","Low":"min","Close":"last"
            })
            setup_qtr = detect_strat(data_qtr)

            # Year
            data_yr = data_mo.resample("Y").agg({
                "Open":"first","High":"max","Low":"min","Close":"last"
            })
            setup_yr = detect_strat(data_yr)

            last_price = float(data_day["Close"].iloc[-1])
            net_chg = last_price - float(data_day["Close"].iloc[-2])
            atr = calc_atr(data_day)

            results.append({
                "Symbol": sym,
                "Last": round(last_price, 2),
                "Net Chng": round(net_chg, 2),
                "Day": setup_day,
                "Wk": setup_wk,
                "Month": setup_mo,
                "Qtr": setup_qtr,
                "Year": setup_yr,
                "ATR": round(atr, 2) if atr else None
            })
        except Exception as e:
            st.warning(f"Erro em {sym}: {e}")

    if results:
        df_results = pd.DataFrame(results)

        html_table = "<table>"
        html_table += "<tr>" + "".join(f"<th>{col}</th>" for col in df_results.columns) + "</tr>"

        for _, row in df_results.iterrows():
            html_table += "<tr>"
            for col in df_results.columns:
                value = row[col]
                color = "#eee"
                if col in ["Day", "Wk", "Month", "Qtr", "Year"]:
                    color = color_setup(value)
                html_table += f"<td style='color:{color}'>{value}</td>"
            html_table += "</tr>"

        html_table += "</table>"
        st.markdown(html_table, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
