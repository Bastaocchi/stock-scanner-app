import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import math

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

.table-wrap { width: 100%; overflow-x: auto; }
.table { border-collapse: collapse; width: 100%; font-size: 18px; }
.table th { text-align: left; padding: 12px; background: #111827; color: #fff; position: sticky; top: 0; }
.table td { padding: 12px; border-bottom: 1px solid #e5e7eb; }
.row-bullish { background: #e9f7ef; }
.row-bearish { background: #fdecea; }
.row-neutral { background: #f5f5f5; }
.badge { display:inline-block; padding:3px 8px; border-radius:8px; font-weight:600; font-size:14px; }
.badge-bullish { background:#16a34a; color:#fff; }
.badge-bearish { background:#dc2626; color:#fff; }
.badge-neutral { background:#6b7280; color:#fff; }

.summary-chip { display:inline-block; padding:6px 10px; border-radius:12px; margin-right:8px; background:#f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ==============================
# LISTA DE SÍMBOLOS (ajuste se quiser)
# ==============================
@st.cache_data(ttl=3600)
def load_symbols():
    return [
        "AAPL","MSFT","TSLA","AMZN","NVDA","META","GOOGL","NFLX","AMD","IBM",
        "JPM","BAC","XOM","CVX","KO","PEP","COST","AVGO","ORCL","INTC",
        "ADBE","CRM","QCOM","TXN","CSCO","SHOP","PFE","MRK","WMT","HD",
        "DE","CAT","BA","UNH","V","MA","PYPL","SQ","UBER","ABNB"
    ]

SYMBOLS = load_symbols()

# ==============================
# DOWNLOAD SEGURO (yfinance)
# ==============================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[-1] if isinstance(c, tuple) else c for c in df.columns]
    return df

def _standardize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.title() for c in df.columns})
    cols = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
    df = df[cols].copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=[c for c in ["Open","High","Low","Close"] if c in df.columns], how="any")
    return df

def yf_download_resilient(symbol, period, interval, tries=3, pause=0.4):
    last_exc = None
    for _ in range(tries):
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False, threads=False)
            if df is not None and not df.empty:
                df = _flatten_columns(df)
                df = _standardize_ohlc(df)
                if len(df) >= 3 and all(col in df.columns for col in ["Open","High","Low","Close"]):
                    return df
        except Exception as e:
            last_exc = e
        time.sleep(pause)
    return None

@st.cache_data(ttl=1200)
def get_stock_data(symbol, period="1y", interval="1d"):
    return yf_download_resilient(symbol, period, interval)

# ==============================
# HELPERS
# ==============================
def _scalar(v):
    if isinstance(v, (pd.Series, np.ndarray, list, tuple)):
        return float(v[-1])
    try:
        return float(v)
    except Exception:
        return np.nan

def _classify_vectorized(df: pd.DataFrame, inside_inclusive=True) -> pd.Series:
    """
    Classifica cada barra em relação à anterior: 1, 2U, 2D, 3 (None para a 1ª).
    """
    h, l = df["High"].values, df["Low"].values
    ph = np.roll(h, 1); pl = np.roll(l, 1)
    ph[0] = np.nan; pl[0] = np.nan

    if inside_inclusive:
        inside = (h <= ph) & (l >= pl) & ((h < ph) | (l > pl))
    else:
        inside = (h < ph) & (l > pl)

    outside = (h > ph) & (l < pl)
    two_up  = (h > ph) & ~outside & ~inside
    two_dn  = (l < pl) & ~outside & ~inside

    res = np.full(len(df), None, dtype=object)
    res[inside] = "1"
    res[outside] = "3"
    res[two_up]  = "2U"
    res[two_dn]  = "2D"
    return pd.Series(res, index=df.index)

def detect_inside_in_window(df: pd.DataFrame, lookback=12, inside_inclusive=True):
    kinds = _classify_vectorized(df, inside_inclusive=inside_inclusive)
    tail = kinds.iloc[-lookback:]
    idx = tail[tail.eq("1")].index
    if len(idx):
        i = idx[-1]
        return True, i, float(df.loc[i, "Close"])
    return False, None, None

def detect_hammer_window(df: pd.DataFrame, lookback=12):
    # critérios moderados
    window = df.iloc[-lookback:] if len(df) >= lookback else df
    for i in reversed(range(window.index.start, window.index.stop if hasattr(window.index, "stop") else len(df))):
        try:
            curr = df.iloc[i]
            prev = df.iloc[i-1] if i-1 >= 0 else None
            if prev is None:
                continue
            o, h, l, c = map(_scalar, [curr["Open"], curr["High"], curr["Low"], curr["Close"]])
            p_low = _scalar(prev["Low"])
            body = abs(c - o)
            total = h - l
            if not (total > 0 and body <= 0.5*total):
                continue
            lower_shadow = min(o, c) - l
            upper_shadow = h - max(o, c)
            if lower_shadow >= 1.5*body and upper_shadow <= 1.2*body and c > o and l < p_low:
                return True, df.index[i], c
        except Exception:
            continue
    return False, None, None

def detect_2d_green_monthly_window(df: pd.DataFrame, lookback=12):
    if len(df) < 2:
        return False, None, None
    window_idx = df.index[-lookback:] if len(df) >= lookback else df.index
    for i in reversed(range(len(df))):
        if df.index[i] not in window_idx:
            continue
        if i - 1 < 0:
            continue
        curr, prev = df.iloc[i], df.iloc[i-1]
        ch, cl, co, cc = map(_scalar, [curr["High"], curr["Low"], curr["Open"], curr["Close"]])
        ph, pl = map(_scalar, [prev["High"], prev["Low"]])
        if (cl < pl) and (cc > co) and (ch <= ph):
            return True, df.index[i], cc
    return False, None, None

def detect_combos_window(df: pd.DataFrame, window=3, search_span=12, inside_inclusive=True):
    kinds = _classify_vectorized(df, inside_inclusive=inside_inclusive)
    combos_map = {
        "2U-1-2U": "Bullish 2-1-2 Continuation",
        "2D-1-2D": "Bearish 2-1-2 Continuation",
        "2U-1-2D": "2-1-2 Reversal Down",
        "2D-1-2U": "2-1-2 Reversal Up",
        "3-1-2U": "3-1-2 Bullish",
        "3-1-2D": "3-1-2 Bearish",
        "1-2U-2U": "1-2-2 Bullish",
        "1-2D-2D": "1-2-2 Bearish",
        "2U-2D": "2U-2D Reversal",
        "2D-2U": "2D-2U Reversal",
        # extras úteis
        "1-2U": "1-2 Break Up",
        "1-2D": "1-2 Break Down"
    }
    start = max(1, len(df) - search_span)
    found_name, found_idx = None, None
    for i in range(start, len(df) - (window - 1)):
        seq = kinds.iloc[i:i+window].tolist()
        if any(x is None for x in seq):
            continue
        pattern = "-".join(seq)
        if pattern in combos_map:
            found_name = combos_map[pattern]
            found_idx = df.index[i + window - 1]
    return found_name, found_idx

def check_ftfc(symbol: str):
    try:
        tf_map = {"1D": ("5d", "1d"), "1W": ("1y", "1wk"), "1M": ("5y", "1mo")}
        dirs = {}
        for tf, (p, itv) in tf_map.items():
            df = get_stock_data(symbol, period=p, interval=itv)
            if df is None or df.empty:
                return None
            last = df.iloc[-1]
            o, c = _scalar(last["Open"]), _scalar(last["Close"])
            dirs[tf] = "UP" if c > o else "DOWN"
        return dirs["1D"] if len(set(dirs.values())) == 1 else None
    except Exception:
        return None

def bias_from_setup(name: str) -> str:
    s = (name or "").lower()
    if "bearish" in s or "down" in s or "ftfc down" in s:
        return "Bearish"
    if "bullish" in s or "up" in s or "2d green monthly" in s or "hammer" in s:
        return "Bullish"
    if "inside bar" in s:
        return "Neutral"
    return "Neutral"

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
# SCAN DE UM SÍMBOLO
# ==============================
def scan_symbol(symbol, period, interval, inside, hammer, green2d, combos, ftfc_flag,
                inside_lookback=12, hammer_lookback=12, combo_window=3, combo_span=12, inside_inclusive=True):
    out = []
    df = get_stock_data(symbol, period=period, interval=interval)
    if df is None or df.empty or len(df) < 3:
        return out

    # Inside (janela)
    if inside:
        ok, dt, px = detect_inside_in_window(df, lookback=inside_lookback, inside_inclusive=inside_inclusive)
        if ok:
            out.append({"Symbol": symbol, "Setup": "Inside Bar", "Price": f"${px:.2f}" if px is not None else "",
                        "Date": dt.strftime("%Y-%m-%d")})

    # Hammer (janela)
    if hammer:
        ok, dt, px = detect_hammer_window(df, lookback=hammer_lookback)
        if ok:
            out.append({"Symbol": symbol, "Setup": "Hammer Setup", "Price": f"${px:.2f}" if px is not None else "",
                        "Date": dt.strftime("%Y-%m-%d")})

    # 2D Green Monthly (só se timeframe mensal)
    if green2d and interval == "1mo":
        ok, dt, px = detect_2d_green_monthly_window(df, lookback=12)
        if ok:
            out.append({"Symbol": symbol, "Setup": "2D Green Monthly", "Price": f"${px:.2f}" if px is not None else "",
                        "Date": dt.strftime("%Y-%m-%d")})

    # Combos
    if combos:
        combo_name, dt = detect_combos_window(df, window=combo_window, search_span=combo_span, inside_inclusive=inside_inclusive)
        if combo_name and dt is not None:
            px = float(df.loc[dt, "Close"])
            out.append({"Symbol": symbol, "Setup": combo_name, "Price": f"${px:.2f}", "Date": dt.strftime("%Y-%m-%d")})

    # FTFC
    if ftfc_flag:
        direction = check_ftfc(symbol)
        if direction:
            last_close = float(df.iloc[-1]["Close"])
            out.append({"Symbol": symbol, "Setup": f"FTFC {direction}", "Price": f"${last_close:.2f}",
                        "Date": df.index[-1].strftime("%Y-%m-%d")})

    return out

# ==============================
# UI
# ==============================
def main():
    c1, c2, c3, c4 = st.columns([2,4,2,2])

    with c1:
        timeframes = {"1D": ("1y", "1d"), "1W": ("2y", "1wk"), "1M": ("5y", "1mo")}
        timeframe = st.radio("Timeframe", list(timeframes.keys()), horizontal=True)

    with c2:
        inside = st.checkbox("Inside Bar", value=True)
        hammer = st.checkbox("Hammer Setup", value=True)
        green2d = st.checkbox("2D Green Monthly", value=False)
        combos = st.checkbox("TheStrat Combos", value=True)
        ftfc_flag = st.checkbox("Full Timeframe Continuity", value=True)

    with c3:
        max_symbols = st.slider("Máx. símbolos", 10, len(SYMBOLS), min(60, len(SYMBOLS)))

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
        counts = {"Inside Bar":0, "Hammer Setup":0, "2D Green Monthly":0, "FTFC UP":0, "FTFC DOWN":0,
                  "Bullish 2-1-2 Continuation":0, "Bearish 2-1-2 Continuation":0,
                  "2-1-2 Reversal Down":0, "2-1-2 Reversal Up":0,
                  "3-1-2 Bullish":0, "3-1-2 Bearish":0,
                  "1-2-2 Bullish":0, "1-2-2 Bearish":0,
                  "2U-2D Reversal":0, "2D-2U Reversal":0, "1-2 Break Up":0, "1-2 Break Down":0}

        symbols_to_scan = SYMBOLS[:max_symbols]
        total = len(symbols_to_scan)

        # Paraleliza o scan
        def task(sym):
            return scan_symbol(sym, period, interval, inside, hammer, green2d, combos, ftfc_flag,
                               inside_lookback=14, hammer_lookback=14, combo_window=3, combo_span=12, inside_inclusive=True)

        with ThreadPoolExecutor(max_workers=min(16, max(4, math.ceil(total/5)))) as ex:
            futures = {ex.submit(task, s): s for s in symbols_to_scan}
            for k, fut in enumerate(as_completed(futures)):
                sym = futures[fut]
                status.text(f"Analisando {sym}...")
                try:
                    out = fut.result()
                    if out:
                        results.extend(out)
                        for r in out:
                            nm = r["Setup"]
                            if nm in counts:
                                counts[nm] += 1
                            elif nm.startswith("FTFC"):
                                counts[nm] = counts.get(nm, 0) + 1
                except Exception:
                    pass

                progress = (k + 1) / total
                progress_bar.progress(progress)
                processed_metric.metric("Processados", f"{k+1}")
                found_metric.metric("Setups", f"{len(results)}")
                progress_metric.metric("Progresso", f"{progress*100:.1f}%")

        status.text("Scanner concluído!")

        if results:
            df_results = pd.DataFrame(results)
            df_results["Bias"] = df_results["Setup"].apply(bias_from_setup)

            # Sumário rápido por tipo
            chips = []
            for key, val in counts.items():
                if val > 0:
                    chips.append(f'<span class="summary-chip">{key}: {val}</span>')
            if chips:
                st.markdown("".join(chips), unsafe_allow_html=True)

            # Ordena por Data (desc) e Setup
            try:
                df_results["Date"] = pd.to_datetime(df_results["Date"])
            except Exception:
                pass
            df_results = df_results.sort_values(by=["Date","Symbol","Setup"], ascending=[False, True, True])

            # Render colorido
            cols = ["Symbol","Setup","Bias","Price","Date"]
            st.markdown("Resultados")
            render_colored_table(df_results[cols])

            csv = df_results[cols].to_csv(index=False)
            st.download_button("Baixar CSV", csv,
                               file_name=f"strat_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")
        else:
            st.warning("Nenhum setup encontrado. Já estou varrendo múltiplas velas e combos com inside inclusivo. Aumente 'Máx. símbolos', troque o timeframe ou rode novamente em alguns minutos.")
    else:
        st.info("Defina os filtros e clique em Iniciar Scanner.")

if __name__ == "__main__":
    main()
