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
    # troque pela sua fonte (CSV/Sheets) quando quiser
    return [
        "AAPL","MSFT","TSLA","AMZN","NVDA","META","GOOGL","NFLX","AMD","IBM",
        "JPM","BAC","XOM","CVX","KO","PEP","COST","AVGO","ORCL","INTC",
        "ADBE","CRM","QCOM","TXN","CSCO","SHOP","PFE","MRK","WMT","HD"
    ]

def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[-1] if isinstance(c, tuple) else c for c in df.columns]
    return df

def _standardize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {c: c.title() for c in df.columns}
    df = df.rename(columns=rename_map)
    expected = ["Open","High","Low","Close","Volume"]
    keep = [c for c in expected if c in df.columns]
    df = df[keep].copy()
    for c in keep:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(how="all")
    return df

@st.cache_data(ttl=1800)
def get_stock_data(symbol, period="1y", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return None
        df = _flatten_columns(df)
        df = _standardize_ohlc(df)
        if len(df) < 3 or not all(col in df.columns for col in ["Open","High","Low","Close"]):
            return None
        return df
    except Exception:
        return None

SYMBOLS = load_symbols()

# ==============================
# HELPS
# ==============================
def _scalar(v):
    if isinstance(v, (pd.Series, np.ndarray, list, tuple)):
        return float(v[-1])
    return float(v)

# ==============================
# THESTRAT CLASSIFICAÇÃO
# ==============================
def classify_strat_bar(curr: pd.Series, prev: pd.Series, inside_inclusive: bool = True):
    try:
        ch, cl, ph, pl = _scalar(curr["High"]), _scalar(curr["Low"]), _scalar(prev["High"]), _scalar(prev["Low"])
    except Exception:
        return None
    if inside_inclusive:
        # Inside inclusivo (≤ / ≥) com pelo menos uma desigualdade estrita
        if (ch <= ph) and (cl >= pl) and ((ch < ph) or (cl > pl)):
            return "1"
    else:
        if ch < ph and cl > pl:
            return "1"
    if ch > ph and cl < pl:
        return "3"
    if ch > ph:
        return "2U"
    if cl < pl:
        return "2D"
    return None

def detect_strat_combo_sliding(df: pd.DataFrame, window=3, search_span=6, inside_inclusive=True):
    """
    Varre janelas móveis (últimas 'search_span' barras) e tenta formar um padrão de 'window' barras.
    Retorna o combo encontrado mais recente (ou None).
    """
    if len(df) < window + 1:
        return None, None  # (nome, data)
    start_idx = max(1, len(df) - search_span)  # garante que haja prev para a primeira janela
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
    found_name, found_date = None, None
    for i in range(start_idx, len(df) - (window - 1)):
        seq = []
        # gera tipos para barras i..i+window-1, comparando cada uma com a anterior
        for j in range(i, i + window):
            curr, prev = df.iloc[j], df.iloc[j-1]
            seq.append(classify_strat_bar(curr, prev, inside_inclusive=inside_inclusive))
        pattern = "-".join(seq)
        if pattern in combos:
            found_name = combos[pattern]
            found_date = df.index[i + window - 1]
    return found_name, found_date

def scan_inside_bars(df: pd.DataFrame, lookback=6, inside_inclusive=True):
    """
    Procura Inside Bar nas últimas 'lookback' barras (comparando cada uma com a anterior).
    Retorna (bool, data, preço_close)
    """
    if len(df) < 2:
        return False, None, None
    start = max(1, len(df) - lookback)
    for i in range(len(df) - 1, start - 1, -1):  # do mais recente ao mais antigo dentro do lookback
        curr, prev = df.iloc[i], df.iloc[i-1]
        t = classify_strat_bar(curr, prev, inside_inclusive=inside_inclusive)
        if t == "1":
            try:
                c_close = _scalar(curr["Close"])
            except Exception:
                c_close = None
            return True, df.index[i], c_close
    return False, None, None

def scan_hammer(df: pd.DataFrame, lookback=6):
    """
    Hammer mais permissivo:
      - corpo <= 50% do range
      - sombra inferior >= 1.5x corpo
      - sombra superior <= 1.2x corpo
      - fechamento verde
      - (opcional) rompeu a mínima anterior (mantido para robustez)
    Retorna (bool, data, preço_close)
    """
    if len(df) < 3:
        return False, None, None
    start = max(1, len(df) - lookback)
    for i in range(len(df) - 1, start - 1, -1):
        curr, prev = df.iloc[i], df.iloc[i-1]
        try:
            o, h, l, c = _scalar(curr["Open"]), _scalar(curr["High"]), _scalar(curr["Low"]), _scalar(curr["Close"])
            p_low = _scalar(prev["Low"])
        except Exception:
            continue
        body = abs(c - o)
        total = h - l
        if total <= 0:
            continue
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        is_small_body = body <= 0.5 * total
        long_lower = lower_shadow >= 1.5 * body
        short_upper = upper_shadow <= 1.2 * body
        green = c > o
        broke_prev_low = l < p_low  # mantém para priorizar hammers "úteis"
        if is_small_body and long_lower and short_upper and green and broke_prev_low:
            return True, df.index[i], c
    return False, None, None

def scan_2d_green_monthly(df: pd.DataFrame, lookback=6):
    """
    2D Green Monthly nas últimas 'lookback' barras mensais.
    Retorna (bool, data, preço_close)
    """
    if len(df) < 2:
        return False, None, None
    start = max(1, len(df) - lookback)
    for i in range(len(df) - 1, start - 1, -1):
        curr, prev = df.iloc[i], df.iloc[i-1]
        try:
            ch, cl, co, cc = _scalar(curr["High"]), _scalar(curr["Low"]), _scalar(curr["Open"]), _scalar(curr["Close"])
            ph, pl = _scalar(prev["High"]), _scalar(prev["Low"])
        except Exception:
            continue
        if (cl < pl) and (cc > co) and (ch <= ph):
            return True, df.index[i], cc
    return False, None, None

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
    c1, c2, c3, c4 = st.columns([2,4,2,2])

    with c1:
        timeframes = {"1D": ("1y", "1d"), "1W": ("2y", "1wk"), "1M": ("5y", "1mo")}
        timeframe = st.radio("Timeframe", list(timeframes.keys()), horizontal=True)

    with c2:
        inside = st.checkbox("Inside Bar", value=True)
        hammer = st.checkbox("Hammer Setup", value=True)
        green2d = st.checkbox("2D Green Monthly", value=False)
        combos = st.checkbox("TheStrat Combos", value=True)
        ftfc = st.checkbox("Full Timeframe Continuity", value=True)

    with c3:
        max_symbols = st.slider("Máx. símbolos", 10, len(SYMBOLS), min(60, len(SYMBOLS)))

    with c4:
        run = st.button("Iniciar Scanner", use_container_width=True)

    st.markdown("---")

    if run:
        period, interval = timeframes[timeframe]
        # parâmetros de busca mais amplos para aumentar detecções
        inside_lookback = 8
        hammer_lookback = 8
        combo_window = 3
        combo_search_span = 6
        inside_inclusive = True

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
                # Inside Bar (janela)
                if inside:
                    ok, dt, px = scan_inside_bars(df, lookback=inside_lookback, inside_inclusive=inside_inclusive)
                    if ok:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Inside Bar",
                            "Price": f"${px:.2f}" if px is not None else "",
                            "Date": dt.strftime("%Y-%m-%d")
                        })

                # Hammer (janela)
                if hammer:
                    ok, dt, px = scan_hammer(df, lookback=hammer_lookback)
                    if ok:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "Hammer Setup",
                            "Price": f"${px:.2f}" if px is not None else "",
                            "Date": dt.strftime("%Y-%m-%d")
                        })

                # 2D Green Monthly (janela)
                if green2d and interval == "1mo":
                    ok, dt, px = scan_2d_green_monthly(df, lookback=6)
                    if ok:
                        results.append({
                            "Symbol": symbol,
                            "Setup": "2D Green Monthly",
                            "Price": f"${px:.2f}" if px is not None else "",
                            "Date": dt.strftime("%Y-%m-%d")
                        })

                # Combos TheStrat (janelas móveis)
                if combos:
                    combo_name, dt = detect_strat_combo_sliding(df, window=combo_window, search_span=combo_search_span, inside_inclusive=inside_inclusive)
                    if combo_name and dt is not None:
                        px = float(df.loc[dt, "Close"])
                        results.append({
                            "Symbol": symbol,
                            "Setup": combo_name,
                            "Price": f"${px:.2f}",
                            "Date": dt.strftime("%Y-%m-%d")
                        })

                # FTFC
                if ftfc:
                    direction = check_ftfc(symbol)
                    if direction:
                        last_close = float(df.iloc[-1]["Close"])
                        results.append({
                            "Symbol": symbol,
                            "Setup": f"FTFC {direction}",
                            "Price": f"${last_close:.2f}",
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
            st.warning("Nenhum setup encontrado com as condições atuais. O scanner agora varre múltiplas velas e usa Inside inclusivo; se ainda zerar, aumente o 'Máx. símbolos' ou troque o timeframe.")

if __name__ == "__main__":
    main()
