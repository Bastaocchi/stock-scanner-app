import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta

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
    """Corrige inconsistências nos dados de candlestick"""
    valid_flag = "OK"
    if open_p > high_p:
        high_p = open_p
        valid_flag = "Adjusted"
    if open_p < low_p:
        low_p = open_p
        valid_flag = "Adjusted"
    if close_p > high_p:
        high_p = close_p
        valid_flag = "Adjusted"
    if close_p < low_p:
        low_p = close_p
        valid_flag = "Adjusted"
    return open_p, high_p, low_p, close_p, valid_flag


def normalize_dataframe(df):
    """Normaliza o DataFrame com nomes de colunas padronizados"""
    if df is None or df.empty:
        return None
    
    # Cria uma cópia para não modificar o original
    df_normalized = df.copy()
    
    # Normaliza os nomes das colunas
    df_normalized.columns = [str(col).lower().replace(' ', '_') for col in df_normalized.columns]
    
    # Mapeia possíveis variações de nomes de colunas
    column_mapping = {
        'adj_close': 'close',
        'adjclose': 'close',
        'adj close': 'close'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df_normalized.columns and new_name not in df_normalized.columns:
            df_normalized[new_name] = df_normalized[old_name]
    
    # Verifica se temos as colunas essenciais
    required_columns = ['open', 'high', 'low', 'close']
    missing_columns = [col for col in required_columns if col not in df_normalized.columns]
    
    if missing_columns:
        st.error(f"Colunas faltando: {missing_columns}")
        return None
    
    return df_normalized


def detect_double_inside_bar(df):
    """Detecta padrão Double Inside Bar"""
    if df is None or len(df) < 3:
        return False, None

    df_norm = normalize_dataframe(df)
    if df_norm is None:
        return False, None

    current = df_norm.iloc[-1]
    previous = df_norm.iloc[-2]
    before_previous = df_norm.iloc[-3]

    try:
        # Corrige dados da barra atual
        open_curr, high_curr, low_curr, close_curr, valid_flag_curr = fix_candle(
            float(current["open"]),
            float(current["high"]),
            float(current["low"]),
            float(current["close"])
        )
        
        # Corrige dados da barra anterior
        open_prev, high_prev, low_prev, close_prev, valid_flag_prev = fix_candle(
            float(previous["open"]),
            float(previous["high"]),
            float(previous["low"]),
            float(previous["close"])
        )
        
        # Dados da barra antes da anterior
        high_before, low_before = float(before_previous["high"]), float(before_previous["low"])

        # Verifica se a barra atual é inside da anterior
        current_inside = high_curr < high_prev and low_curr > low_prev
        
        # Verifica se a barra anterior é inside da que vem antes
        previous_inside = high_prev < high_before and low_prev > low_before

        if current_inside and previous_inside:
            valid_flag = "Adjusted" if valid_flag_curr == "Adjusted" or valid_flag_prev == "Adjusted" else "OK"
            return True, {
                "type": "Double Inside Bar",
                "price": close_curr,
                "valid": valid_flag
            }
            
    except (ValueError, KeyError) as e:
        st.error(f"Erro no Double Inside Bar: {e}")
        return False, None
    
    return False, None


def detect_inside_bar(df):
    """Detecta padrão Inside Bar"""
    if df is None or len(df) < 2:
        return False, None

    df_norm = normalize_dataframe(df)
    if df_norm is None:
        return False, None

    current = df_norm.iloc[-1]
    previous = df_norm.iloc[-2]

    try:
        open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
            float(current["open"]),
            float(current["high"]),
            float(current["low"]),
            float(current["close"])
        )
        high_prev, low_prev = float(previous["high"]), float(previous["low"])

        if high_curr < high_prev and low_curr > low_prev:
            return True, {
                "type": "Inside Bar",
                "price": close_curr,
                "valid": valid_flag
            }
    except (ValueError, KeyError) as e:
        st.error(f"Erro no Inside Bar: {e}")
        return False, None
    
    return False, None


def detect_2down_green_3m(df):
    """
    Detecta 2Down Green 3M (trimestral):
    - Vela atual rompeu mínima da vela anterior (low_atual < low_anterior)
    - Vela atual está verde (close_atual > open_atual)
    - Vela atual NÃO rompeu máxima da vela anterior (high_atual < high_anterior)
    """
    if df is None or df.empty:
        return False, None

    try:
        df_norm = normalize_dataframe(df)
        if df_norm is None:
            return False, None

        # Garante que o índice é datetime
        if not isinstance(df_norm.index, pd.DatetimeIndex):
            df_norm = df_norm.reset_index()
            if 'date' in df_norm.columns:
                df_norm['date'] = pd.to_datetime(df_norm['date'])
                df_norm = df_norm.set_index('date')
            else:
                df_norm.index = pd.to_datetime(df_norm.index)

        # Cria dados trimestrais usando 'Q' para trimestres corretos do calendário
        df_quarterly = df_norm.resample('Q').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum' if 'volume' in df_norm.columns else lambda x: 0
        }).dropna()

        if len(df_quarterly) < 2:
            return False, None

        # Analisa as últimas 2 barras trimestrais
        current = df_quarterly.iloc[-1]   # Barra atual
        previous = df_quarterly.iloc[-2]  # Barra anterior

        open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
            float(current["open"]),
            float(current["high"]),
            float(current["low"]),
            float(current["close"])
        )
        
        high_prev = float(previous["high"])
        low_prev = float(previous["low"])

        # Condições do 2Down Green 3M
        rompeu_minima = low_curr < low_prev           # 1. Rompeu mínima anterior
        fechou_verde = close_curr > open_curr         # 2. Fechou verde
        nao_rompeu_maxima = high_curr < high_prev     # 3. NÃO rompeu máxima anterior

        if rompeu_minima and fechou_verde and nao_rompeu_maxima:
            return True, {
                "type": "2Down Green 3M",
                "price": round(close_curr, 2),
                "valid": valid_flag
            }

    except Exception as e:
        st.error(f"Erro no 2Down Green 3M: {e}")
        return False, None

    return False, None


def detect_2down_green_monthly(df):
    """
    Detecta 2Down Green Monthly:
    - Vela atual rompeu mínima da vela anterior (low_atual < low_anterior)
    - Vela atual está verde (close_atual > open_atual)
    - Vela atual NÃO rompeu máxima da vela anterior (high_atual < high_anterior)
    """
    if df is None or df.empty:
        return False, None

    try:
        df_norm = normalize_dataframe(df)
        if df_norm is None:
            return False, None

        # Garante que o índice é datetime
        if not isinstance(df_norm.index, pd.DatetimeIndex):
            df_norm = df_norm.reset_index()
            if 'date' in df_norm.columns:
                df_norm['date'] = pd.to_datetime(df_norm['date'])
                df_norm = df_norm.set_index('date')
            else:
                # Se não há coluna de data, usa o índice atual como data
                df_norm.index = pd.to_datetime(df_norm.index)

        # Cria dados mensais
        df_monthly = df_norm.resample('M').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum' if 'volume' in df_norm.columns else lambda x: 0
        }).dropna()

        if len(df_monthly) < 2:  # Precisamos de pelo menos 2 barras mensais
            return False, None

        # Analisa as últimas 2 barras mensais
        current = df_monthly.iloc[-1]   # Barra atual (em andamento)
        previous = df_monthly.iloc[-2]  # Barra anterior

        open_curr, high_curr, low_curr, close_curr, valid_flag = fix_candle(
            float(current["open"]),
            float(current["high"]),
            float(current["low"]),
            float(current["close"])
        )
        
        high_prev = float(previous["high"])
        low_prev = float(previous["low"])

        # Condições do 2Down Green Monthly
        rompeu_minima = low_curr < low_prev           # 1. Rompeu mínima anterior
        fechou_verde = close_curr > open_curr         # 2. Fechou verde
        nao_rompeu_maxima = high_curr < high_prev     # 3. NÃO rompeu máxima anterior

        if rompeu_minima and fechou_verde and nao_rompeu_maxima:
            return True, {
                "type": "2Down Green Monthly",
                "price": round(close_curr, 2),
                "valid": valid_flag
            }

    except Exception as e:
        st.error(f"Erro no 2Down Green Monthly: {e}")
        return False, None

    return False, None


@st.cache_data(ttl=3600)
def get_stock_data(symbol, period="2y", interval="1d"):
    """Baixa dados do Yahoo Finance com tratamento de erros"""
    try:
        # Aumentei o período para 2 anos para ter mais dados mensais
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=False)
        
        if df is None or df.empty:
            return None
            
        # Remove timezone se presente
        if hasattr(df.index, 'tz_localize'):
            df.index = df.index.tz_localize(None)
            
        return df
    except Exception as e:
        return None


@st.cache_data(ttl=3600)
def load_symbols():
    """Carrega símbolos do arquivo local symbols.csv ou GitHub como fallback"""
    try:
        # Tenta carregar o arquivo local primeiro
        df = pd.read_csv("symbols.csv")
        st.info("📁 Usando arquivo symbols.csv local")
        return df
    except FileNotFoundError:
        st.warning("📁 Arquivo 'symbols.csv' não encontrado localmente. Tentando carregar do GitHub...")
        try:
            # Fallback para GitHub se não encontrar local
            url = "https://raw.githubusercontent.com/Bastaocchi/stock-scanner-app/main/symbols.csv"
            df = pd.read_csv(url)
            st.info("🌐 Usando arquivo symbols.csv do GitHub")
            return df
        except Exception as e:
            st.error(f"Erro ao carregar símbolos do GitHub: {e}")
            # Retorna uma lista padrão em caso de erro
            st.warning("⚠️ Usando lista padrão de símbolos")
            return pd.DataFrame({
                'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                'sector_spdr': ['Technology', 'Technology', 'Technology', 'Consumer Discretionary', 'Consumer Discretionary'],
                'tags': ['Large Cap', 'Large Cap', 'Large Cap', 'Large Cap', 'Large Cap']
            })
    except Exception as e:
        st.error(f"Erro ao ler arquivo symbols.csv: {e}")
        st.warning("⚠️ Usando lista padrão de símbolos")
        return pd.DataFrame({
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
            'sector_spdr': ['Technology', 'Technology', 'Technology', 'Consumer Discretionary', 'Consumer Discretionary'],
            'tags': ['Large Cap', 'Large Cap', 'Large Cap', 'Large Cap', 'Large Cap']
        })


def render_results_table(df):
    """Renderiza tabela de resultados"""
    if df.empty:
        st.warning("Nenhum resultado para exibir")
        return
        
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

    try:
        df_symbols = load_symbols()
        df_symbols.columns = df_symbols.columns.str.strip().str.lower()
        st.success(f"✅ Carregados {len(df_symbols)} símbolos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar símbolos: {e}")
        return

    # =========================
    # FILTROS NO TOPO
    # =========================
    col1, col2, col3, col4 = st.columns([1,1,1,2])

    setores = ["Todos"] + sorted(df_symbols["sector_spdr"].dropna().unique().tolist()) if "sector_spdr" in df_symbols.columns else ["Todos"]
    tags = ["Todos"] + sorted(df_symbols["tags"].dropna().unique().tolist()) if "tags" in df_symbols.columns else ["Todos"]

    setor_filter = col1.selectbox("📌 Setor", setores)
    tag_filter = col2.selectbox("🏷️ Tag", tags)
    timeframe_filter = col3.selectbox("⏳ Timeframe", ["Daily", "Weekly", "Monthly", "Quarterly"])

    if timeframe_filter == "Daily":
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar", "Double Inside Bar"])
    elif timeframe_filter == "Weekly":
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar", "Double Inside Bar"])
    elif timeframe_filter == "Monthly":
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar", "2Down Green Monthly"])
    else:  # Quarterly
        setup_filter = col4.selectbox("⚡ Setup", ["Inside Bar", "2Down Green 3M"])

    # =========================
    # BOTÃO SCANNER
    # =========================
    if st.button("🚀 Rodar Scanner"):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        SYMBOLS = df_symbols["symbols"].dropna().tolist()
        total_symbols = len(SYMBOLS)

        for i, symbol in enumerate(SYMBOLS):
            try:
                df = get_stock_data(symbol)
                if df is None or len(df) < 5:  # Precisa de pelo menos 5 dias de dados
                    continue

                found, info = False, None

                if timeframe_filter == "Daily":
                    if setup_filter == "Inside Bar":
                        found, info = detect_inside_bar(df)
                    elif setup_filter == "Double Inside Bar":
                        found, info = detect_double_inside_bar(df)

                elif timeframe_filter == "Weekly":
                    df_norm = normalize_dataframe(df)
                    if df_norm is not None:
                        df_weekly = df_norm.resample("W").agg({
                            "open": "first",
                            "high": "max",
                            "low": "min",
                            "close": "last"
                        }).dropna()
                        if setup_filter == "Inside Bar":
                            found, info = detect_inside_bar(df_weekly)
                        elif setup_filter == "Double Inside Bar":
                            found, info = detect_double_inside_bar(df_weekly)

                elif timeframe_filter == "Monthly":
                    if setup_filter == "Inside Bar":
                        df_norm = normalize_dataframe(df)
                        if df_norm is not None:
                            df_monthly = df_norm.resample("M").agg({
                                "open": "first",
                                "high": "max",
                                "low": "min",
                                "close": "last"
                            }).dropna()
                            found, info = detect_inside_bar(df_monthly)
                    elif setup_filter == "2Down Green Monthly":
                        found, info = detect_2down_green_monthly(df)

                elif timeframe_filter == "Quarterly":
                    if setup_filter == "Inside Bar":
                        df_norm = normalize_dataframe(df)
                        if df_norm is not None:
                            df_quarterly = df_norm.resample("Q").agg({
                                "open": "first",
                                "high": "max",
                                "low": "min",
                                "close": "last"
                            }).dropna()
                            found, info = detect_inside_bar(df_quarterly)
                    elif setup_filter == "2Down Green 3M":
                        found, info = detect_2down_green_3m(df)

                if found and info:
                    # Busca informações adicionais do símbolo
                    symbol_row = df_symbols[df_symbols["symbols"] == symbol]
                    
                    row = {
                        "symbol": symbol,
                        "setup": info["type"],
                        "price": f"${info['price']:.2f}",
                        "valid": info["valid"]
                    }
                    
                    # Adiciona setor e tags se disponíveis
                    if not symbol_row.empty:
                        if "sector_spdr" in df_symbols.columns:
                            row["sector_spdr"] = symbol_row["sector_spdr"].values[0]
                        if "tags" in df_symbols.columns:
                            row["tags"] = symbol_row["tags"].values[0]

                    results.append(row)

            except Exception as e:
                # Log do erro mas continua o scanner
                continue

            # Atualiza progress bar
            progress = (i + 1) / total_symbols
            progress_bar.progress(progress)
            status_text.text(f"⏳ {i+1}/{total_symbols} símbolos... | 🎯 {len(results)} setups encontrados")

        progress_bar.empty()
        status_text.empty()

        if results:
            df_results = pd.DataFrame(results)

            # Aplica filtros
            if setor_filter != "Todos" and "sector_spdr" in df_results.columns:
                df_results = df_results[df_results["sector_spdr"] == setor_filter]
            if tag_filter != "Todos" and "tags" in df_results.columns:
                df_results = df_results[df_results["tags"] == tag_filter]

            st.success(f"✅ {len(df_results)} setups encontrados após filtros!")
            render_results_table(df_results)
        else:
            st.warning(f"❌ Nenhum setup encontrado em {timeframe_filter} - {setup_filter}")


if __name__ == "__main__":
    main()
