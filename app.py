import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Scanner de Setups Profissional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# CSS PERSONALIZADO
# ==============================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stDataFrame {
        font-size: 20px !important;
    }
    div[data-testid="stDataFrame"] table td,
    div[data-testid="stDataFrame"] table th {
        font-size: 20px !important;
        padding: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
@st.cache_data(ttl=3600)
def load_symbols():
    """Carrega símbolos de CSV local, Google Sheets ou usa lista padrão."""
    try:
        import os
        if os.path.exists('symbols.csv'):
            df = pd.read_csv('symbols.csv')
            if 'Symbol' in df.columns:
                return df['Symbol'].dropna().tolist()
    except:
        pass

    default_symbols = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "JNJ", "XOM"]
    st.sidebar.info(f"📋 Usando lista padrão com {len(default_symbols)} símbolos")
    return default_symbols

SYMBOLS = load_symbols()

def detect_inside_bar(df):
    """Detecta Inside Bar"""
    if len(df) < 2:
        return False, None
    current, previous = df.iloc[-1], df.iloc[-2]
    is_inside = (current['High'] < previous['High']) and (current['Low'] > previous['Low'])
    if is_inside:
        change_pct = ((current['Close'] - current['Open']) / current['Open']) * 100
        return True, {
            'type': 'Inside Bar',
            'price': current['Close'],
            'change_pct': change_pct,
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    return False, None

def detect_hammer_setup(df):
    """Detecta Hammer Setup"""
    if len(df) < 3:
        return False, None
    current, previous = df.iloc[-1], df.iloc[-2]
    body_size = abs(current['Close'] - current['Open'])
    total_range = current['High'] - current['Low']
    lower_shadow = min(current['Open'], current['Close']) - current['Low']
    upper_shadow = current['High'] - max(current['Open'], current['Close'])
    is_small_body = body_size <= 0.4 * total_range
    is_long_lower_shadow = lower_shadow >= 2 * body_size
    is_short_upper_shadow = upper_shadow <= body_size
    broke_below = current['Low'] < previous['Low']
    closed_green = current['Close'] > current['Open']
    is_hammer = is_small_body and is_long_lower_shadow and is_short_upper_shadow
    is_hammer_setup = is_hammer and broke_below and closed_green
    if is_hammer_setup:
        recovery_pct = ((current['Close'] - current['Low']) / current['Low']) * 100
        return True, {
            'type': 'Hammer Setup',
            'price': current['Close'],
            'recovery_pct': recovery_pct,
            'broke_level': previous['Low'],
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    return False, None

def detect_2d_green_monthly(df):
    """Detecta 2D Green Monthly"""
    if len(df) < 2:
        return False, None
    current, previous = df.iloc[-1], df.iloc[-2]
    broke_previous_low = current['Low'] < previous['Low']
    candle_green = current['Close'] > current['Open']
    did_not_exceed_high = current['High'] <= previous['High']
    if broke_previous_low and candle_green and did_not_exceed_high:
        break_amount = previous['Low'] - current['Low']
        monthly_recovery = ((current['Close'] - current['Low']) / current['Low']) * 100
        monthly_change = ((current['Close'] - current['Open']) / current['Open']) * 100
        return True, {
            'type': '2D Green Monthly',
            'price': current['Close'],
            'previous_low': previous['Low'],
            'previous_high': previous['High'],
            'current_low': current['Low'],
            'current_high': current['High'],
            'break_amount': break_amount,
            'monthly_recovery_pct': monthly_recovery,
            'monthly_change_pct': monthly_change,
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    return False, None

@st.cache_data(ttl=3600)
def get_stock_data(symbol, period='1y', interval='1d'):
    try:
        data = yf.Ticker(symbol).history(period=period, interval=interval)
        return None if data.empty else data
    except:
        return None

# ==============================
# MAIN APP
# ==============================
def main():
    st.markdown('<h1 class="main-header">Scanner de Setups Profissional</h1>', unsafe_allow_html=True)
    st.markdown("**Análise automatizada de Inside Bars, Hammer Setups e 2D Green Monthly**")

    st.sidebar.header("Configurações")
    timeframes = {
        "Daily (1D)": ("1y", "1d"),
        "Weekly (1W)": ("2y", "1wk"),
        "Monthly (1M)": ("5y", "1mo")
    }

    detect_inside_bar_flag = st.sidebar.checkbox("Inside Bar", value=True)
    detect_hammer_flag = st.sidebar.checkbox("Hammer Setup", value=True)
    detect_2d_green_flag = st.sidebar.checkbox("2D Green Monthly", value=False)

    if detect_2d_green_flag:
        selected_timeframe = "Monthly (1M)"
        st.sidebar.info("⛔ Timeframe fixado em Monthly para 2D Green")
    else:
        selected_timeframe = st.sidebar.selectbox("Timeframe:", list(timeframes.keys()), index=0)

    max_symbols = st.sidebar.slider("Máximo de símbolos:", 10, len(SYMBOLS), min(100, len(SYMBOLS)))

    if st.sidebar.button("Iniciar Scanner", type="primary"):
        period, interval = timeframes[selected_timeframe]

        col1, col2, col3, col4 = st.columns(4)
        processed_metric = col1.metric("Processados", "0")
        found_metric = col2.metric("Setups", "0")
        errors_metric = col3.metric("Erros", "0")
        progress_metric = col4.metric("Progresso", "0%")

        progress_bar, status_text = st.progress(0), st.empty()
        results_container = st.container()

        processed_count, error_count = 0, 0
        found_setups = []

        for i, symbol in enumerate(SYMBOLS[:max_symbols]):
            status_text.text(f"Analisando {symbol}...")
            try:
                df = get_stock_data(symbol, period, interval)
                if df is not None and len(df) >= 10:
                    if detect_inside_bar_flag:
                        ok, info = detect_inside_bar(df)
                        if ok: found_setups.append({'symbol': symbol, 'setup_info': info})
                    if detect_hammer_flag:
                        ok, info = detect_hammer_setup(df)
                        if ok: found_setups.append({'symbol': symbol, 'setup_info': info})
                    if detect_2d_green_flag:
                        ok, info = detect_2d_green_monthly(df)
                        if ok: found_setups.append({'symbol': symbol, 'setup_info': info})
                processed_count += 1
            except:
                error_count += 1

            progress = (i + 1) / max_symbols
            progress_bar.progress(progress)
            processed_metric.metric("Processados", str(processed_count))
            found_metric.metric("Setups", str(len(found_setups)))
            errors_metric.metric("Erros", str(error_count))
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            time.sleep(0.05)

        status_text.text("✅ Scanner concluído!")

        # Mostrar resultados
        if found_setups:
            results_data = []
            for setup in found_setups:
                s, info = setup['symbol'], setup['setup_info']
                row = {'Symbol': s, 'Setup': info['type'], 'Price': f"${info['price']:.2f}", 'Date': info['date']}
                if info['type'] == "Inside Bar":
                    row['Change %'] = f"{info['change_pct']:.2f}%"
                if info['type'] == "Hammer Setup":
                    row['Recovery %'] = f"{info['recovery_pct']:.2f}%"
                    row['Broke Level'] = f"${info['broke_level']:.2f}"
                if info['type'] == "2D Green Monthly":
                    row['Monthly Change %'] = f"{info['monthly_change_pct']:.2f}%"
                    row['Break Amount'] = f"${info['break_amount']:.2f}"
                results_data.append(row)

            df_results = pd.DataFrame(results_data)
            st.markdown("### 📊 Resultados")
            st.dataframe(df_results, use_container_width=True)

            csv = df_results.to_csv(index=False)
            st.download_button("📥 Baixar Resultados CSV", csv,
                               file_name=f"scanner_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")
        else:
            st.warning("Nenhum setup encontrado.")

if __name__ == "__main__":
    main()
