import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Configuração da página
st.set_page_config(
    page_title="Scanner de Setups Profissional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
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
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .setup-found {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Lista de símbolos (seus 664 tickers)
SYMBOLS = ["A","AAL","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADP","ADSK","AEE","AEP","AES","AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALL","ALLE","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS","AON","AOS","APA","APD","APH","APTV","ARE","ATO","AVB","AVGO","AVY","AWK","AXON","AXP","AZO","BA","BAC","BALL","BAX","BBWI","BBY","BDX","BEN","BF.B","BIIB","BIO","BK","BKNG","BKR","BLDR","BLK","BMY","BR","BRK.B","BRO","BSX","BWA","BX","BXP","C","CAG","CAH","CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CDAY","CDNS","CDW","CE","CEG","CF","CFG","CHD","CHRW","CHTR","CI","CINF","CL","CLX","CMA","CMCSA","CME","CMG","CMI","CMS","CNC","CNP","COF","COO","COP","COR","COST","COTY","CPB","CPRT","CPT","CRL","CRM","CSCO","CSGP","CSX","CTAS","CTLT","CTRA","CTSH","CTVA","CVS","CVX","CZR","D","DAL","DD","DE","DFS","DG","DGX","DHI","DHR","DIS","DJT","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK","DVA","DVN","DXCM","EA","EBAY","ECL","ED","EFX","EIX","EL","ELV","EMN","EMR","ENPH","EOG","EPAM","EQIX","EQR","EQT","ES","ESS","ETN","ETR","EVRG","EW","EXC","EXPD","EXPE","EXR","F","FANG","FAST","FCX","FDS","FDX","FE","FFIV","FI","FICO","FIS","FITB","FMC","FRT","FSLR","FTNT","FTV","GD","GE","GILD","GIS","GL","GLW","GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW","HAL","HAS","HBAN","HCA","HD","HES","HIG","HII","HLT","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY","HUBB","HUM","HWM","IBM","ICE","IDXX","IEX","IFF","INCY","INTC","INTU","INVH","IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM","K","KDP","KEY","KEYS","KHC","KIM","KLAC","KMB","KMI","KMX","KO","KR","KVUE","L","LAMR","LDOS","LEN","LH","LHX","LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV","MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT","MET","META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH","MOS","MPC","MPWR","MRK","MRNA","MRO","MS","MSCI","MSFT","MSI","MTB","MTCH","MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW","NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA","NXPI","O","ODFL","OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PANW","PARA","PAYC","PAYX","PCAR","PCG","PEAK","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PKG","PKI","PLD","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL","PRU","PSA","PSX","PTC","PWR","PXD","PYPL","QCOM","QRVO","RCL","REG","REGN","RF","RHI","RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC","SBUX","SCHW","SHW","SJM","SLB","SMCI","SNA","SNPS","SO","SOLV","SPG","SPGI","SRE","STE","STLD","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY","T","TAP","TDG","TDY","TECH","TEL","TER","TFC","TFX","TGT","TJX","TMO","TMUS","TPG","TPR","TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL","UAL","UBER","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VICI","VLO","VMEO","VMC","VRSK","VRSN","VTRS","VTR","VRTX","VZ","WAB","WAT","WBA","WBD","WDC","WEC","WELL","WFC","WM","WMB","WMT","WRB","WST","WTW","WY","WYNN","XEL","XOM","XYL","YUM","ZBH","ZION","ZTS"]

def detect_inside_bar(df):
    """Detecta Inside Bar: máxima atual < máxima anterior E mínima atual > mínima anterior"""
    if len(df) < 2:
        return False, None
    
    current = df.iloc[-1]
    previous = df.iloc[-2]
    
    is_inside = (current['High'] < previous['High']) and (current['Low'] > previous['Low'])
    
    if is_inside:
        change_pct = ((current['Close'] - current['Open']) / current['Open']) * 100
        return True, {
            'type': 'Inside Bar',
            'price': current['Close'],
            'change_pct': change_pct,
            'range': f"${current['Low']:.2f} - ${current['High']:.2f}",
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    
    return False, None

def detect_hammer_setup(df):
    """Detecta Hammer Setup: martelo que rompeu mínima anterior e fechou verde"""
    if len(df) < 3:
        return False, None
    
    current = df.iloc[-1]
    previous = df.iloc[-2]
    
    # Condições do hammer
    body_size = abs(current['Close'] - current['Open'])
    total_range = current['High'] - current['Low']
    lower_shadow = min(current['Open'], current['Close']) - current['Low']
    upper_shadow = current['High'] - max(current['Open'], current['Close'])
    
    # Critérios para hammer
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

@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_stock_data(symbol, period='1y', interval='1d'):
    """Busca dados da ação usando yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            return None
        return data
    except Exception as e:
        st.error(f"Erro ao buscar dados para {symbol}: {str(e)}")
        return None

def create_candlestick_chart(df, symbol, setup_info=None):
    """Função removida - não usada mais"""
    pass

def main():
    st.markdown('<h1 class="main-header">Scanner de Setups Profissional</h1>', unsafe_allow_html=True)
    st.markdown("**Análise automatizada de Inside Bars e Hammer Setups em 664 símbolos**")
    
    # Sidebar
    st.sidebar.header("Configurações")
    
    # Seleção de timeframes
    timeframes = {
        "Daily (1D)": ("1y", "1d"),
        "Weekly (1W)": ("2y", "1wk"), 
        "Monthly (1M)": ("5y", "1mo")
    }
    
    selected_timeframe = st.sidebar.selectbox(
        "Timeframe:",
        list(timeframes.keys()),
        index=0
    )
    
    # Seleção de setups
    st.sidebar.subheader("Setups para Detectar:")
    detect_inside_bar_flag = st.sidebar.checkbox("Inside Bar", value=True)
    detect_hammer_flag = st.sidebar.checkbox("Hammer Setup", value=True)
    
    # Limite de símbolos para teste
    max_symbols = st.sidebar.slider("Máximo de símbolos para analisar:", 10, 664, 100)
    
    # Botão para iniciar scan
    if st.sidebar.button("Iniciar Scanner", type="primary"):
        if not detect_inside_bar_flag and not detect_hammer_flag:
            st.error("Selecione pelo menos um setup para detectar!")
            return
            
        period, interval = timeframes[selected_timeframe]
        
        # Métricas em tempo real
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            processed_metric = st.metric("Processados", "0")
        with col2:
            found_metric = st.metric("Setups Encontrados", "0")
        with col3:
            errors_metric = st.metric("Erros", "0")
        with col4:
            progress_metric = st.metric("Progresso", "0%")
        
        # Barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Containers para resultados
        results_container = st.container()
        
        # Variáveis para tracking
        processed_count = 0
        found_setups = []
        error_count = 0
        
        # Processar símbolos
        symbols_to_process = SYMBOLS[:max_symbols]
        
        for i, symbol in enumerate(symbols_to_process):
            status_text.text(f"Analisando {symbol}...")
            
            try:
                # Buscar dados
                df = get_stock_data(symbol, period, interval)
                
                if df is not None and len(df) >= 10:
                    setup_found = False
                    setup_info = None
                    
                    # Detectar Inside Bar
                    if detect_inside_bar_flag:
                        is_inside, info = detect_inside_bar(df)
                        if is_inside:
                            found_setups.append({
                                'symbol': symbol,
                                'setup_info': info
                            })
                            setup_found = True
                            setup_info = info
                    
                    # Detectar Hammer Setup
                    if detect_hammer_flag and not setup_found:
                        is_hammer, info = detect_hammer_setup(df)
                        if is_hammer:
                            found_setups.append({
                                'symbol': symbol,
                                'setup_info': info
                            })
                            setup_found = True
                            setup_info = info
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                st.sidebar.error(f"Erro em {symbol}: {str(e)}")
            
            # Atualizar métricas
            progress = (i + 1) / len(symbols_to_process)
            progress_bar.progress(progress)
            
            processed_metric.metric("Processados", str(processed_count))
            found_metric.metric("Setups Encontrados", str(len(found_setups)))
            errors_metric.metric("Erros", str(error_count))
            progress_metric.metric("Progresso", f"{progress*100:.1f}%")
            
            # Pequena pausa para não sobrecarregar
            time.sleep(0.05)
        
        status_text.text("Scanner concluído!")
        
        # Mostrar resultados em tabela
        if found_setups:
            st.success(f"**{len(found_setups)} setups encontrados!**")
            
            with results_container:
                st.header("Resultados Encontrados")
                
                # Criar DataFrame para exibição
                results_data = []
                for setup in found_setups:
                    symbol = setup['symbol']
                    info = setup['setup_info']
                    
                    if info['type'] == 'Inside Bar':
                        results_data.append({
                            'Symbol': symbol,
                            'Setup': 'Inside Bar',
                            'Price': f"${info['price']:.2f}",
                            'Change %': f"{info['change_pct']:.2f}%",
                            'Range': info['range'],
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date'],
                            'TradingView': f"https://www.tradingview.com/symbols/{symbol}/"
                        })
                    else:  # Hammer Setup
                        results_data.append({
                            'Symbol': symbol,
                            'Setup': 'Hammer Setup',
                            'Price': f"${info['price']:.2f}",
                            'Recovery %': f"+{info['recovery_pct']:.2f}%",
                            'Broke Level': f"${info['broke_level']:.2f}",
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date'],
                            'TradingView': f"https://www.tradingview.com/symbols/{symbol}/"
                        })
                
                # Exibir tabela
                df_results = pd.DataFrame(results_data)
                st.dataframe(df_results, use_container_width=True)
                
                # Separar por tipo
                inside_bars = [s for s in found_setups if s['setup_info']['type'] == 'Inside Bar']
                hammers = [s for s in found_setups if s['setup_info']['type'] == 'Hammer Setup']
                
                if inside_bars:
                    st.subheader(f"Inside Bars ({len(inside_bars)})")
                    inside_data = []
                    for setup in inside_bars:
                        info = setup['setup_info']
                        inside_data.append({
                            'Symbol': setup['symbol'],
                            'Price': f"${info['price']:.2f}",
                            'Change': f"{info['change_pct']:.2f}%",
                            'Range': info['range'],
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                    st.dataframe(pd.DataFrame(inside_data), use_container_width=True)
                
                if hammers:
                    st.subheader(f"Hammer Setups ({len(hammers)})")
                    hammer_data = []
                    for setup in hammers:
                        info = setup['setup_info']
                        hammer_data.append({
                            'Symbol': setup['symbol'],
                            'Price': f"${info['price']:.2f}",
                            'Recovery': f"+{info['recovery_pct']:.2f}%",
                            'Broke Level': f"${info['broke_level']:.2f}",
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                    st.dataframe(pd.DataFrame(hammer_data), use_container_width=True)
                
                # Botão de download dos resultados
                if st.button("Download Resultados CSV"):
                    csv = df_results.to_csv(index=False)
                    st.download_button(
                        label="Baixar CSV",
                        data=csv,
                        file_name=f"scanner_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv"
                    )
        else:
            st.warning("Nenhum setup encontrado com os critérios selecionados. Tente:")
            st.info("• Aumentar o número de símbolos analisados\n• Testar timeframes diferentes\n• Verificar se o mercado teve movimentos recentes")

if __name__ == "__main__":
    main()
