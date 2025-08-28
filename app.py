import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# =============================
# Configuração da página
# =============================
st.set_page_config(
    page_title="Scanner de Setups Profissional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================
# CSS personalizado
# =============================
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
        font-size: 16px !important;
    }
    .stDataFrame td {
        font-size: 16px !important;
        padding: 12px !important;
    }
    .stDataFrame th {
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# Função para carregar símbolos
# =============================
@st.cache_data(ttl=3600)
def load_symbols():
    try:
        import os
        if os.path.exists('symbols.csv'):
            df = pd.read_csv('symbols.csv')
            if 'Symbol' in df.columns:
                symbols = df['Symbol'].dropna().tolist()
                st.sidebar.success(f"✅ Carregados {len(symbols)} símbolos do arquivo CSV")
                return symbols
    except Exception as e:
        st.sidebar.warning(f"Não foi possível carregar CSV local: {e}")
    
    default_symbols = ["AAPL","MSFT","AMZN","META","TSLA","NVDA","AMD","NFLX","GOOG","JPM"]
    st.sidebar.info(f"📋 Usando lista padrão com {len(default_symbols)} símbolos")
    return default_symbols

SYMBOLS = load_symbols()

# =============================
# Funções de detecção de setups
# =============================
def detect_inside_bar(df):
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
    if is_hammer and broke_below and closed_green:
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
    if len(df) < 2:
        return False, None
    current, previous = df.iloc[-1], df.iloc[-2]
    broke_previous_low = current['Low'] < previous['Low']
    is_green = current['Close'] > current['Open']
    did_not_exceed_high = current['High'] <= previous['High']
    if broke_previous_low and is_green and did_not_exceed_high:
        break_amount = previous['Low'] - current['Low']
        break_pct = (break_amount / previous['Low']) * 100
        monthly_recovery = ((current['Close'] - current['Low']) / current['Low']) * 100
        monthly_change = ((current['Close'] - current['Open']) / current['Open']) * 100
        return True, {
            'type': '2D Green Monthly',
            'price': current['Close'],
            'open_price': current['Open'],
            'current_low': current['Low'],
            'current_high': current['High'],
            'previous_low': previous['Low'],
            'previous_high': previous['High'],
            'break_amount': break_amount,
            'break_pct': break_pct,
            'monthly_recovery_pct': monthly_recovery,
            'monthly_change_pct': monthly_change,
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    return False, None

# =============================
# Função para buscar dados
# =============================
@st.cache_data(ttl=3600)
def get_stock_data(symbol, period='1y', interval='1d'):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        return data if not data.empty else None
    except Exception as e:
        st.sidebar.error(f"Erro em {symbol}: {str(e)}")
        return None

# =============================
# Main App
# =============================
def main():
    st.markdown('<h1 class="main-header">Scanner de Setups Profissional</h1>', unsafe_allow_html=True)
    st.markdown("**Análise automatizada de Inside Bars, Hammer Setups e 2D Green Monthly**")

    st.sidebar.header("Configurações")
    timeframes = {
        "Daily (1D)": ("1y", "1d"),
        "Weekly (1W)": ("2y", "1wk"),
        "Monthly (1M)": ("5y", "1mo")
    }

    st.sidebar.subheader("Setups para Detectar:")
    detect_inside_bar_flag = st.sidebar.checkbox("Inside Bar", value=True)
    detect_hammer_flag = st.sidebar.checkbox("Hammer Setup", value=True)
    detect_2d_green_flag = st.sidebar.checkbox("2D Green Monthly", value=False)

    if detect_2d_green_flag:
        st.sidebar.info("🔒 2D Green Monthly → Timeframe fixo em Monthly")
        selected_timeframe = "Monthly (1M)"
    else:
        selected_timeframe = st.sidebar.selectbox("Timeframe:", list(timeframes.keys()), index=0)

    max_symbols = st.sidebar.slider("Máximo de símbolos:", 10, len(SYMBOLS), min(50, len(SYMBOLS)))

    if st.sidebar.button("Iniciar Scanner", type="primary"):
        period, interval = timeframes[selected_timeframe]
        col1, col2, col3, col4 = st.columns(4)
        processed_metric = col1.metric("Processados", "0")
        found_metric = col2.metric("Setups Encontrados", "0")
        errors_metric = col3.metric("Erros", "0")
        progress_metric = col4.metric("Progresso", "0%")
        progress_bar, status_text = st.progress(0), st.empty()

        found_setups, processed_count, error_count = [], 0, 0
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
            except Exception as e:
                error_count += 1
                st.sidebar.error(f"Erro em {symbol}: {str(e)}")

            progress = (i+1)/max_symbols
            progress_bar.progress(progress)
            processed_metric.metric("Processados", str(processed_count))
            found_metric.metric("Setups Encontrados", str(len(found_setups)))
            errors_metric.metric("Erros", str(error_count))
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            time.sleep(0.05)

        status_text.text("Scanner concluído!")

        if found_setups:
            st.success(f"✅ {len(found_setups)} setups encontrados!")
            results_data = []
            for setup in found_setups:
                symbol, info = setup['symbol'], setup['setup_info']
                row = {"Symbol": symbol, "Setup": info['type'], "Date": info['date'], "Price": f"${info['price']:.2f}"}
                if info['type'] == "Inside Bar":
                    row.update({"Change %": f"{info['change_pct']:.2f}%", "Volume": f"{info['volume']:,}"})
                elif info['type'] == "Hammer Setup":
                    row.update({"Recovery %": f"{info['recovery_pct']:.2f}%", "Broke Level": f"${info['broke_level']:.2f}", "Volume": f"{info['volume']:,}"})
                elif info['type'] == "2D Green Monthly":
                    row.update({
                        "Monthly Change": f"{info['monthly_change_pct']:.2f}%",
                        "Previous Low": f"${info['previous_low']:.2f}",
                        "Previous High": f"${info['previous_high']:.2f}",
                        "Current Low": f"${info['current_low']:.2f}",
                        "Current High": f"${info['current_high']:.2f}",
                        "Break Amount": f"${info['break_amount']:.2f}",
                        "Recovery": f"{info['monthly_recovery_pct']:.2f}%",
                        "Volume": f"{info['volume']:,}"
                    })
                results_data.append(row)

            df_results = pd.DataFrame(results_data)
            st.dataframe(df_results, use_container_width=True)

            csv = df_results.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Baixar Resultados CSV", csv, f"scanner_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")
        else:
            st.warning("Nenhum setup encontrado.")
            st.info("Tente aumentar o número de símbolos ou trocar timeframe.")

if __name__ == "__main__":
    main()
