import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ==============================
# CONFIG PÁGINA
# ==============================
st.set_page_config(page_title="Scanner TheStrat", layout="wide")

# ==============================
# CSS (tipografia + tabela colorida)
# ==============================
st.markdown("""
<style>
html, body, [class*="css"] { font-size: 18px !important; }
label { font-size: 20px !important; font-weight: 700; }
button[kind="primary"], button[kind="secondary"] { font-size: 18px !important; font-weight: 700; }
[data-testid="stMetricValue"] { font-size: 28px !important; }
[data-testid="stMetricLabel"] { font-size: 18px !important; }

/* tabela colorida */
.table-wrap { width: 100%; overflow-x: auto; }
.table { border-collapse: collapse; width: 100%; font-size: 18px; }
.table th { text-align: left; padding: 12px; background: #111827; color: #fff; position: sticky; top: 0; }
.table td { padding: 12px; border-bottom: 1px solid #e5e7eb; }
.row-bullish { background: #e9f7ef; }   /* verde claro */
.row-bearish { background: #fdecea; }   /* vermelho claro */
.row-neutral { background: #f5f5f5; }   /* cinza claro */
.badge { display:inline-block; padding:3px 8px; border-radius:8px; font-weight:600; font-size:14px; }
.badge-bullish { background:#16a34a; color:#fff; }
.badge-bearish { background:#dc2626; color:#fff; }
.badge-neutral { background:#6b7280; color:#fff; }
</style>
""", unsafe_allow_html=True)

# ==============================
# DADOS
# ==============================
@st.cache_data(ttl=3600)
def load_symbols():
    # ajuste para sua fonte (CSV/Sheets) quando quiser
    return [
        "AAPL","MSFT","TSLA","AMZN","NVDA","META","GOOGL","NFLX","AMD","IBM",
        "JPM","BAC","XOM","CVX","KO","PEP","COST","AVGO","ORCL","INTC"
    ]

def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Se vier MultiIndex (ex.: ('AAPL','High')), achata pegando o último nível."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[-1] if isinstance(c, tuple) else c for c in df.columns]
    return df

def _standardize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas comuns para o formato Title e garante numéricos."""
    # normaliza nomes
    rename_map = {c: c.title() for c in df.columns}
    df = df.rename(columns=rename_map)
    # mantém apenas colunas esperadas se existirem
    expected = ["Open","High","Low","Close","Volume"]
    keep = [c for c in expected if c in df.columns]
    df = df[keep].copy()
    # converte para numérico
    for c in keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # remove linhas totalmente NaN
    df = df.dropna(how="all")
    return df

@st.cache_data(ttl=1800)
def get_stock_data(symbol, period="1y", interval="1d"):
    """Download seguro de dados, flatten + padronização."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df = _flatten_columns(df)
        df = _standardize_ohlc(df)
        # precisa pelo menos 2 velas para as comparações
        if len(df) < 2 or not all(col in df.columns for col in ["Open","High","Low","Close"]):
            return None
        return df
    except Exception:
        return None

SYMBOLS = load_symbols()

# ==============================
# THESTRAT
# ==============================
def _scalar(v):
    """Garante escalar (evita 'Series is ambiguous')."""
    if isinstance(v, (pd.Series, np.ndarray, list)):
        return float(v[-1])
    return float(v)

def classify_strat_bar(curr: pd.Series, prev: pd.Series):
    try:
        ch, cl, ph, pl = _scalar(curr["High"]), _scalar(curr["Low"]), _scalar(prev["High"]), _scalar(prev["Low"])
    except Exception:
        return None
    if ch < ph and cl > pl:
        return "1"
    if ch > ph and cl < pl:
        return "3"
    if ch > ph:
        return "2U"
    if cl < pl:
        return "2D"
    return None

def detect_strat_combo(df: pd.DataFrame, lookback=3):
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

def check_ftfc(symbol: str):
    """Full Timeframe Continuity: 1D, 1W, 1M alinhados por cor (Close > Open)."""
    try:
        tf_map = {
            "1D": ("5d", "1d"),
            "1W": ("1y", "1wk"),
            "1M": ("5y", "1mo")
        }
        dirs = {}
        for tf, (period, interval) in tf_map.items():
            df = get_stock_data(symbol, period=period, interval=interval)
            if df is None or df.empty:
                return None
            last = df.iloc[-1]
            o, c = _scalar(last["Open"]), _scalar(last["Close"])
            dirs[tf] = "UP" if c > o else "DOWN"
        return dirs["1D"] if len(set(dirs.values())) == 1 else None
    except Exception:
        return None

def setup_bias(setup_str: str) -> str:
    s = (setup_str or "").lower()
    if "bearish" in s or "ftfc down" in s:
        return "Bearish"
    if "bullish" in s or "2d green monthly" in s or "ftfc up" in s or setup_str == "Hammer Setup":
        return "Bullish"
    if "inside bar" in s:
        return "Neutral"
    return "Neutral"

def badge_for_bias(bias: str) -> str:
    if bias == "Bullish":
        return '<span class="badge badge-bullish">Bullish</span>'
    if bias == "Bearish":
        return '<span class="badge badge-bearish">Bearish</span>'
    return '<span class="badge badge-neutral">Neutral</span>'

def row_class_for_bias(bias: str) -> str:
    return {"Bullish":"row-bullish","Bearish":"row-bearish","Neutral":"row-neutral"}.get(bias,"row-neutral")

def render_colored_table(df: pd.DataFrame):
    headers = "".join([f"<th>{col}</th>" for col in df.columns])
    rows_html = []
    for _, row in df.iterrows():
        cls = row_class_for_bias(row["Bias"])
        tds = "".join([f"<td>{row[col]}</td>" for col in df.columns])
        rows_html.append(f'<tr class="{cls}">{tds}</tr>')
    table_html = f"""
    <div class="table-wrap">
      <table class="table">
        <thead><tr>{headers}</tr></thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# ==============================
# APP
# ==============================
def main():
    # Filtros horizontais
    c1, c2, c3, c4 = st.columns([2,3,2,2])

    with c1:
        timeframes = {"1D": ("1y", "1d"), "1W": ("2y", "1wk"), "1M": ("5y", "1mo")}
        timeframe = st.radio("Timeframe", list(timeframes.keys()), horizontal=True)

    with c2:
        inside = st.checkbox("Inside Bar", value=True)
        hammer = st.checkbox("Hammer Setup", value=False)
        green2d = st.checkbox("2D Green Monthly", value=False)
        combos = st.checkbox("TheStrat Combos", value=True)
        ftfc = st.checkbox("Full Timeframe Continuity", value=False)

    with c3:
        max_symbols = st.slider("Máx. símbolos", 5, len(SYMBOLS), min(50, len(SYMBOLS)))

    with c4:
        run = st.button("Iniciar Scanner", use_container_width=True)

    st.markdown("---")

    if run:
        period, interval = timeframes[timeframe]

        m1, m2, m3 = st.columns(3)
        processed_metric = m1.metric("Processados", "0")
        found_metric = m2.metric("Setups", "0")
        progress_metric = m3.metric("Progresso", "0%")

        progress_bar = st.progress(0)
        status = st.empty()

        results = []
        symbols_to_scan = SYMBOLS[:max_symbols]
        total = len(symbols_to_scan)

        for i, symbol in enumerate(symbols_to_scan):
            status.text(f"Analisando {symbol}...")
            df = get_stock_data(symbol, period=period, interval=interval)

            if df is not None and len(df) > 5:
                curr, prev = df.iloc[-1], df.iloc[-2]

                # Extrai escalares seguros
                try:
                    c_high, c_low = _scalar(curr["High"]), _scalar(curr["Low"])
                    p_high, p_low = _scalar(prev["High"]), _scalar(prev["Low"])
                    c_open, c_close = _scalar(curr["Open"]), _scalar(curr["Close"])
                    p_low_scalar = p_low
                except Exception:
                    c_high = c_low = p_high = p_low = c_open = c_close = None

                # Inside Bar
                if inside and None not in (c_high, c_low, p_high, p_low):
                    if (c_high < p_high) and (c_low > p_low):
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Inside Bar",
                            "Price": f"${c_close:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

                # Hammer
                if hammer and None not in (c_high, c_low, c_open, c_close, p_low_scalar):
                    body = abs(c_close - c_open)
                    total_range = c_high - c_low
                    lower_shadow = min(c_open, c_close) - c_low
                    if total_range > 0 and body <= 0.4*total_range and lower_shadow >= 2*body \
                       and (c_close > c_open) and (c_low < p_low_scalar):
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Hammer Setup",
                            "Price": f"${c_close:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

                # 2D Green Monthly (somente no timeframe mensal)
                if green2d and interval == "1mo" and None not in (c_high, c_low, c_open, c_close, p_high, p_low):
                    if (c_low < p_low) and (c_close > c_open) and (c_high <= p_high):
                        results.append({
                            "Symbol": symbol,
                            "Setup": "2D Green Monthly",
                            "Price": f"${c_close:.2f}",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

                # Combos TheStrat
                if combos:
                    combo_name = detect_strat_combo(df, lookback=3)
                    if combo_name:
                        results.append({
                            "Symbol": symbol,
                            "Setup": combo_name,
                            "Price": f"${c_close:.2f}" if c_close is not None else "",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

                # FTFC
                if ftfc:
                    direction = check_ftfc(symbol)
                    if direction:
                        results.append({
                            "Symbol": symbol,
                            "Setup": f"FTFC {direction}",
                            "Price": f"${c_close:.2f}" if c_close is not None else "",
                            "Date": df.index[-1].strftime("%Y-%m-%d")
                        })

            # métricas / progresso
            progress = (i + 1) / total
            progress_bar.progress(progress)
            processed_metric.metric("Processados", f"{i+1}")
            found_metric.metric("Setups", f"{len(results)}")
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            time.sleep(0.02)

        status.text("Scanner concluído!")

        if results:
            df_results = pd.DataFrame(results)

            # Bias + badge
            df_results["Bias"] = df_results["Setup"].apply(setup_bias)
            df_results["Bias Badge"] = df_results["Bias"].apply(badge_for_bias)

            # Reordena colunas
            cols = ["Symbol", "Setup", "Bias", "Bias Badge", "Price", "Date"]
            df_results = df_results[cols]

            st.markdown("Resultados")
            render_colored_table(
                df_results.drop(columns=["Bias Badge"]).assign(**{"Bias": df_results["Bias Badge"]})
            )

            csv = df_results.drop(columns=["Bias Badge"]).to_csv(index=False)
            st.download_button(
                "Baixar CSV",
                csv,
                file_name=f"strat_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum setup encontrado.")

if __name__ == "__main__":
    main()
