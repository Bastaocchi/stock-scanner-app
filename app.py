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
        background: linear-gradient(45deg, #2196F3, #1976D2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.2rem;
        display: inline-block;
    }
    /* Aumentar tamanho da fonte das tabelas */
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
    /* Estilo para métricas */
    .metric-container {
        background: #f0f8ff;
        border: 2px solid #2196F3;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Função para carregar símbolos de diferentes fontes
@st.cache_data(ttl=3600)
def load_symbols():
    """Carrega símbolos de CSV local ou Google Sheets"""
    
    # Opção 1: Tentar carregar de arquivo CSV local (se existir)
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
    
    # Opção 2: Google Sheets (se URL fornecida)
    google_sheet_url = st.sidebar.text_input(
        "URL do Google Sheets (opcional):",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Cole a URL pública do seu Google Sheets com os símbolos"
    )
    
    if google_sheet_url:
        try:
            # Converter URL do Google Sheets para CSV
            if '/edit' in google_sheet_url:
                csv_url = google_sheet_url.replace('/edit#gid=', '/export?format=csv&gid=')
                csv_url = csv_url.replace('/edit', '/export?format=csv')
            else:
                csv_url = google_sheet_url
            
            df = pd.read_csv(csv_url)
            
            # Tentar encontrar coluna com símbolos
            symbol_column = None
            for col in ['Symbol', 'symbol', 'Ticker', 'ticker', 'SYMBOL']:
                if col in df.columns:
                    symbol_column = col
                    break
            
            if symbol_column:
                symbols = df[symbol_column].dropna().tolist()
                st.sidebar.success(f"✅ Carregados {len(symbols)} símbolos do Google Sheets")
                return symbols
            else:
                st.sidebar.error("Não foi possível encontrar coluna de símbolos. Use 'Symbol' como cabeçalho.")
                
        except Exception as e:
            st.sidebar.error(f"Erro ao carregar Google Sheets: {e}")
    
    # Fallback: Lista padrão
    default_symbols = ["A","AAL","AAPL","ABBV","ABNB","ABT","ACGL","ACN","ADBE","ADI","ADM","ADP","ADSK","AEE","AEP","AES","AFL","AFRM","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALK","ALL","ALLE","AM","AMAT","AMCR","AMD","AME","AMGN","AMP","AMT","AMZN","ANET","AON","AOS","APA","APD","APH","APO","ARCC","ARE","ARTNA","ASML","ATO","AVB","AVGO","AVY","AWK","AXON","AXP","AZN","AZO","BA","BABA","BAC","BALL","BAX","BBDC","BBY","BDX","BE","BEN","BG","BIDU","BIIB","BILL","BIZD","BK","BKNG","BKR","BLDP","BLK","BMO","BMY","BNS","BP","BR","BRO","BSX","BX","BXP","BXSL","BYND","C","CAG","CAH","CAPL","CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CCO","CDNS","CDW","CDZI","CEG","CF","CFG","CGBD","CHD","CHKP","CHRW","CHTR","CI","CINF","CL","CLX","CM","CMCSA","CME","CMG","CMI","CMS","CNC","CNI","CNP","CNQ","COF","COIN","COO","COP","COR","COST","CP","CPAY","CPB","CPRT","CPT","CRL","CRM","CRWD","CSCO","CSGP","CSIQ","CSX","CTAS","CTRA","CTSH","CTVA","CVLT","CVS","CVX","CWT","CYBR","CZR","D","DAL","DASH","DAY","DD","DDOG","DE","DECK","DELL","DG","DGX","DHI","DHR","DIS","DLR","DLTR","DMLP","DOC","DOCN","DOCU","DOL","DOV","DOW","DPZ","DQ","DRI","DTE","DUK","DVA","DVN","DXCM","EA","EBAY","ECL","ED","EFX","EG","EIX","EL","ELV","EME","EMN","EMR","ENB","ENPH","EOG","EPAM","EPD","EQIX","EQR","EQT","ERIE","ES","ESS","ESTC","ET","ETN","ETR","EVRG","EW","EXC","EXE","EXPD","EXPE","EXR","F","FANG","FAST","FCEL","FCX","FDS","FDX","FE","FFIV","FI","FICO","FIS","FITB","FLEX","FNF","FNV","FOUR","FOX","FOXA","FROG","FRT","FSK","FSLR","FTNT","FTV","GAIN","GBDC","GD","GDDY","GDOT","GE","GEHC","GEL","GEN","GEV","GILD","GIS","GL","GLW","GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GSBD","GSK","GWRE","GWRS","GWW","HAL","HAS","HBAN","HCA","HD","HESM","HIG","HII","HLT","HOLX","HON","HOOD","HPE","HPQ","HRL","HSIC","HST","HSY","HTGC","HUBB","HUM","HWM","HYLN","IBKR","IBM","ICE","IDXX","IESC","IEX","IFF","INCY","INTC","INTU","INVH","IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J","JBHT","JBL","JBLU","JCI","JD","JKHY","JKS","JNJ","JPM","K","KDP","KEY","KEYS","KHC","KIM","KKR","KLAC","KMB","KMI","KMX","KNTK","KO","KR","KVUE","L","LCID","LDOS","LEN","LH","LHX","LI","LII","LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW","LYB","LYV","MA","MAA","MAIN","MAR","MAXN","MCD","MCHP","MCK","MCO","MDB","MDLZ","MDT","MDU","MET","META","MFC","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH","MOS","MPC","MPLX","MPWR","MRK","MRNA","MRVL","MS","MSBI","MSCI","MSEX","MSFT","MSI","MTB","MTCH","MTD","MTZ","MU","NCLH","NDAQ","NDSN","NEE","NEM","NET","NEWT","NFG","NFLX","NI","NIO","NJR","NKE","NOC","NOW","NRG","NSC","NSIT","NTAP","NTES","NTRS","NU","NUE","NVDA","NVO","NVR","NWS","NWSA","NXPI","O","OCCI","ODFL","OGS","OKE","OKTA","OMC","ON","OPEN","ORCL","ORLY","OTEX","OTIS","OXY","PAA","PANW","PAYC","PAYX","PBT","PCAR","PCG","PDD","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PINS","PKG","PLBY","PLD","PLTR","PLUG","PM","PNC","PNR","PNW","PODD","POOL","PPG","PPL","PRIM","PRLB","PRU","PSA","PSEC","PSTG","PSX","PTC","PURE","PWR","PYPL","QCOM","QLYS","QRVO","QSR","RBA","RBLX","RCL","REAL","REG","REGN","RF","RIVN","RJF","RL","RMD","ROAD","ROK","ROKU","ROL","ROP","ROST","RPD","RSG","RTX","RUN","RVTY","RXO","RY","S","SAIA","SAIL","SAP","SBAC","SBUX","SCHW","SEDG","SHEL","SHOP","SHW","SJM","SJT","SKYW","SLB","SLF","SMCI","SNA","SNAP","SNOW","SNPS","SNY","SO","SOFI","SOL","SOLV","SPG","SPGI","SPWR","SRE","STC","STE","STLD","STRL","STT","STX","STZ","SU","SW","SWK","SWKS","SWX","SYF","SYK","SYY","T","TAP","TCEHY","TD","TDG","TDY","TEAM","TECH","TEL","TENB","TER","TFC","TFI","TGT","TJX","TKO","TM","TMO","TMUS","TPL","TPR","TRGP","TRI","TRMB","TROW","TRV","TSCO","TSLA","TSLX","TSM","TSN","TT","TTD","TTE","TTWO","TWLO","TXN","TXT","TYL","U","UAL","UBER","UDR","UGI","UHS","UL","ULTA","UNH","UNP","UPS","UPST","URI","USAC","USB","USFD","V","VEEV","VICI","VLO","VLTO","VMC","VOC","VRNS","VRSK","VRSN","VRTX","VST","VTR","VTRS","VZ","WAB","WAT","WBA","WBD","WCN","WDAY","WDC","WEC","WELL","WES","WFC","WM","WMB","WMT","WPM","WRB","WSM","WSO","WST","WTW","WY","WYNN","XEL","XOM","XPEV","XYL","XYZ","YORW","YUM","ZBH","ZBRA","ZM","ZS","ZTS"]
    
    st.sidebar.info(f"📋 Usando lista padrão com {len(default_symbols)} símbolos")
    return default_symbols

# Carregar símbolos
SYMBOLS = load_symbols()

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
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    
    return False, None

def detect_2d_green_monthly(df):
    """Detecta 2D Green Monthly: rompeu mínima da vela mensal anterior, mas hoje está verde, SEM superar a máxima anterior"""
    if len(df) < 2:
        return False, None
    
    current = df.iloc[-1]  # Vela mensal atual
    previous = df.iloc[-2]  # Vela mensal anterior
    
    # Condições para 2D Green Monthly:
    # 1. Vela mensal atual rompeu a mínima da vela mensal anterior
    # 2. Vela mensal atual fechou verde (close > open)
    # 3. Vela mensal atual NÃO superou a máxima da vela mensal anterior
    
    broke_previous_monthly_low = current['Low'] < previous['Low']
    monthly_candle_is_green = current['Close'] > current['Open']
    did_not_exceed_previous_high = current['High'] <= previous['High']
    
    is_2d_green_monthly = broke_previous_monthly_low and monthly_candle_is_green and did_not_exceed_previous_high
    
    if is_2d_green_monthly:
        # Calcular métricas
        break_amount = previous['Low'] - current['Low']
        break_percentage = (break_amount / previous['Low']) * 100
        
        # Recuperação da vela mensal (do low ao close)
        monthly_recovery = ((current['Close'] - current['Low']) / current['Low']) * 100
        
        # Variação mensal total
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
            'break_pct': break_percentage,
            'monthly_recovery_pct': monthly_recovery,
            'monthly_change_pct': monthly_change,
            'volume': current['Volume'],
            'date': current.name.strftime('%Y-%m-%d')
        }
    
    return False, None
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
        st.sidebar.error(f"Erro em {symbol}: {str(e)}")
        return None

def main():
    st.markdown('<h1 class="main-header">Scanner de Setups Profissional</h1>', unsafe_allow_html=True)
    st.markdown("**Análise automatizada de Inside Bars, Hammer Setups e 2D Green Monthly em até 664 símbolos**")
    
    # Sidebar
    st.sidebar.header("Configurações")
    
    # Seleção de timeframes
    timeframes = {
        "Daily (1D)": ("1y", "1d"),
        "Weekly (1W)": ("2y", "1wk"), 
        "Monthly (1M)": ("5y", "1mo")
    }
    
    # Seleção de setups primeiro para condicionar timeframes
    st.sidebar.subheader("Setups para Detectar:")
    detect_inside_bar_flag = st.sidebar.checkbox("Inside Bar", value=True)
    detect_hammer_flag = st.sidebar.checkbox("Hammer Setup", value=True)
    detect_2d_green_flag = st.sidebar.checkbox("2D Green Monthly", value=False)
    
    # Condicionar seleção de timeframe baseado no setup 2D Green Monthly
    if detect_2d_green_flag:
        st.sidebar.info("🔒 2D Green Monthly selecionado - Timeframe fixado em Monthly")
        selected_timeframe = "Monthly (1M)"
        st.sidebar.markdown("**Timeframe: Monthly (1M)** *(fixo para 2D Green)*")
    else:
        selected_timeframe = st.sidebar.selectbox(
            "Timeframe:",
            list(timeframes.keys()),
            index=0
        )
    
    # Limite de símbolos para análise
    max_symbols = st.sidebar.slider("Máximo de símbolos para analisar:", 10, len(SYMBOLS), min(100, len(SYMBOLS)))
    
    # Botão para iniciar scan
    if st.sidebar.button("Iniciar Scanner", type="primary"):
        if not detect_inside_bar_flag and not detect_hammer_flag and not detect_2d_green_flag:
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
                    
                    # Detectar Inside Bar
                    if detect_inside_bar_flag:
                        is_inside, info = detect_inside_bar(df)
                        if is_inside:
                            found_setups.append({
                                'symbol': symbol,
                                'setup_info': info
                            })
                            setup_found = True
                    
                    # Detectar Hammer Setup
                    if detect_hammer_flag and not setup_found:
                        is_hammer, info = detect_hammer_setup(df)
                        if is_hammer:
                            found_setups.append({
                                'symbol': symbol,
                                'setup_info': info
                            })
                            setup_found = True
                    
                    # Detectar 2D Green Monthly
                    if detect_2d_green_flag and not setup_found:
                        is_2d_green, info = detect_2d_green_monthly(df)
                        if is_2d_green:
                            found_setups.append({
                                'symbol': symbol,
                                'setup_info': info
                            })
                            setup_found = True
                
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
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                    elif info['type'] == 'Hammer Setup':
                        results_data.append({
                            'Symbol': symbol,
                            'Setup': 'Hammer Setup',
                            'Price': f"${info['price']:.2f}",
                            'Recovery %': f"+{info['recovery_pct']:.2f}%",
                            'Broke Level': f"${info['broke_level']:.2f}",
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                    elif info['type'] == '2D Green Monthly':
                        results_data.append({
                            'Symbol': symbol,
                            'Setup': '2D Green Monthly',
                            'Price': f"${info['price']:.2f}",
                            'Monthly Change': f"+{info['monthly_change_pct']:.2f}%",
                            'Previous Low': f"${info['previous_low']:.2f}",
                            'Previous High': f"${info['previous_high']:.2f}",
                            'Current Low': f"${info['current_low']:.2f}",
                            'Current High': f"${info['current_high']:.2f}",
                            'Break Amount': f"${info['break_amount']:.2f}",
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                
                # Exibir tabela
                df_results = pd.DataFrame(results_data)
                st.dataframe(df_results, use_container_width=True)
                
                # Separar por tipo
                inside_bars = [s for s in found_setups if s['setup_info']['type'] == 'Inside Bar']
                hammers = [s for s in found_setups if s['setup_info']['type'] == 'Hammer Setup']
                green_2d = [s for s in found_setups if s['setup_info']['type'] == '2D Green Monthly']
                
                if inside_bars:
                    st.subheader(f"Inside Bars ({len(inside_bars)})")
                    inside_data = []
                    for setup in inside_bars:
                        info = setup['setup_info']
                        inside_data.append({
                            'Symbol': setup['symbol'],
                            'Price': f"${info['price']:.2f}",
                            'Change': f"{info['change_pct']:.2f}%",
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
                
                if green_2d:
                    st.subheader(f"2D Green Monthly ({len(green_2d)})")
                    green_2d_data = []
                    for setup in green_2d:
                        info = setup['setup_info']
                        green_2d_data.append({
                            'Symbol': setup['symbol'],
                            'Price': f"${info['price']:.2f}",
                            'Monthly Change': f"+{info['monthly_change_pct']:.2f}%",
                            'Previous Low': f"${info['previous_low']:.2f}",
                            'Previous High': f"${info['previous_high']:.2f}",
                            'Current Low': f"${info['current_low']:.2f}",
                            'Current High': f"${info['current_high']:.2f}",
                            'Break Amount': f"${info['break_amount']:.2f}",
                            'Recovery': f"+{info['monthly_recovery_pct']:.2f}%",
                            'Volume': f"{info['volume']:,}",
                            'Date': info['date']
                        })
                    st.dataframe(pd.DataFrame(green_2d_data), use_container_width=True)
                
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
