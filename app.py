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
        
        # Criar DataFrame consolidado
        df_results = pd.DataFrame(results_data)
        
        # Exibir tabela HTML principal
        st.markdown("### 📊 Tabela de Resultados")
        html_table = df_results.to_html(escape=False, index=False)
        html_table = html_table.replace('<table', '<table style="font-size: 18px; width: 100%;"')
        html_table = html_table.replace('<th', '<th style="font-size: 20px; font-weight: bold; padding: 12px; background-color: #2196F3; color: white;"')
        html_table = html_table.replace('<td', '<td style="font-size: 18px; padding: 10px; border-bottom: 1px solid #ddd;"')
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Botão de download dos resultados
        csv = df_results.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Resultados CSV",
            data=csv,
            file_name=f"scanner_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
else:
    st.warning("Nenhum setup encontrado com os critérios selecionados. Tente:")
    st.info("• Aumentar o número de símbolos analisados\n• Testar timeframes diferentes\n• Verificar se o mercado teve movimentos recentes")
