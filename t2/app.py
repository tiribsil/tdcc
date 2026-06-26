import streamlit as st
import pandas as pd
import numpy as np
from even_swap import verificar_dominacao, remover_alternativas_dominadas, detectar_quase_dominacoes

def estilizar_tabela(df, objetivos, alternativas_removidas=None, celulas_alteradas=None):
    if alternativas_removidas is None:
        alternativas_removidas = []

    # Copy DataFrame to avoid mutating the original index in-place
    df_copy = df.copy()
    
    if alternativas_removidas:
        new_index = [
            "".join([char + '\u0336' for char in name]) if name in alternativas_removidas else name
            for name in df_copy.index
        ]
        df_copy.index = new_index

    styler = df_copy.style

    def highlight_best(col):
        obj = objetivos.get(col.name)
        is_best = [False] * len(col)
        if obj == 'maximizar':
            is_best = (col == col.max()).tolist()
        elif obj == 'minimizar':
            is_best = (col == col.min()).tolist()
        
        for idx, alt_name in enumerate(col.index):
            clean_name = alt_name.replace('\u0336', '')
            if clean_name in alternativas_removidas:
                is_best[idx] = False

        styles = ['background-color: rgba(144, 238, 144, 0.3)' if v else '' for v in is_best]
        return pd.Series(styles, index=col.index)

    styler = styler.apply(highlight_best, axis=0)

    def style_rows(row):
        clean_name = row.name.replace('\u0336', '')
        if clean_name in alternativas_removidas:
            styles = ['text-decoration: line-through; color: #888; background-color: rgba(0, 0, 0, 0.05)'] * len(row)
        else:
            styles = [''] * len(row)
        return pd.Series(styles, index=row.index)

    styler = styler.apply(style_rows, axis=1)

    def highlight_cells(x):
        styles = pd.DataFrame('', index=x.index, columns=x.columns)
        if celulas_alteradas:
            for alt, col in celulas_alteradas:
                for idx_val in styles.index:
                    clean_idx = idx_val.replace('\u0336', '')
                    if clean_idx == alt and col in styles.columns:
                        styles.at[idx_val, col] = 'background-color: rgba(255, 165, 0, 0.25)'
        return styles

    styler = styler.apply(highlight_cells, axis=None)

    return styler.format(precision=2)

def formatar_lista_portugues(lista):
    if not lista:
        return ""
    if len(lista) == 1:
        return f"'{lista[0]}'"
    if len(lista) == 2:
        return f"'{lista[0]}' e '{lista[1]}'"
    return ", ".join([f"'{x}'" for x in lista[:-1]]) + f" e '{lista[-1]}'"

# =====================================================================
# WEB INTERFACE (STREAMLIT)
# =====================================================================

st.set_page_config(page_title="Ferramenta de Decisão por Sistema de Compensação", layout="wide")

st.markdown("""
    <style>
    /* Hide Streamlit custom +/- step buttons */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }
    /* Hide standard HTML number input spinners */
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button {
        -webkit-appearance: none !important;
        margin: 0 !important;
    }
    input[type=number] {
        -moz-appearance: textfield !important;
    }
    
    /* Spreadsheet grid layout styling */
    div[data-testid="stHorizontalBlock"] {
        gap: 0px !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        margin-right: -1px !important;
        margin-bottom: -1px !important;
        padding: 8px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        min-height: 60px !important;
    }
    /* Header row background shading */
    div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="stColumn"] {
        background-color: rgba(128, 128, 128, 0.15) !important;
    }
    
    /* Remove vertical gap between adjacent rows in the spreadsheet grid */
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stHorizontalBlock"]) + div:has(> div[data-testid="stHorizontalBlock"]) {
        margin-top: -1rem !important;
    }
    
    /* Make buttons and widgets inside cells align nicely */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] button {
        width: 100% !important;
        height: 100% !important;
    }
    
    /* Centered bold markdown text alignment inside grid cells */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] p {
        margin: 0 !important;
        font-weight: inherit !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚖️ Sistema de Compensação - Suporte à Decisão")

def salvar_estado_historico():
    if 'historico' not in st.session_state:
        st.session_state.historico = []
    
    snapshot = {
        'passo': st.session_state.get('passo'),
        'setup_step': st.session_state.get('setup_step'),
        'sub_setup_step': st.session_state.get('sub_setup_step'),
        'criterio_atual_idx': st.session_state.get('criterio_atual_idx'),
        'tabela_construcao': st.session_state.tabela_construcao.copy() if st.session_state.get('tabela_construcao') is not None else None,
        'objetivo': st.session_state.objetivo.copy() if st.session_state.get('objetivo') is not None else {},
        'tabela': st.session_state.tabela.copy() if st.session_state.get('tabela') is not None else None,
        'alternativas': st.session_state.get('alternativas'),
        'criterios': st.session_state.get('criterios'),
        'qual_melhor_alt': st.session_state.get('qual_melhor_alt'),
        'qual_melhor_score': st.session_state.get('qual_melhor_score'),
        'qual_pior_alt': st.session_state.get('qual_pior_alt'),
        'qual_pior_score': st.session_state.get('qual_pior_score'),
        'qual_restantes': st.session_state.get('qual_restantes'),
        'qual_alt_idx': st.session_state.get('qual_alt_idx'),
        'qual_scores_temp': st.session_state.qual_scores_temp.copy() if st.session_state.get('qual_scores_temp') is not None else {},
        'simple_comp_c_comp': st.session_state.get('simple_comp_c_comp'),
        'last_selected_qd_key': st.session_state.get('last_selected_qd_key')
    }
    st.session_state.historico.append(snapshot)

def voltar_estado():
    if 'historico' in st.session_state and st.session_state.historico:
        last_state = st.session_state.historico.pop()
        
        st.session_state.passo = last_state['passo']
        st.session_state.setup_step = last_state['setup_step']
        st.session_state.sub_setup_step = last_state['sub_setup_step']
        st.session_state.criterio_atual_idx = last_state['criterio_atual_idx']
        st.session_state.tabela_construcao = last_state['tabela_construcao']
        st.session_state.objetivo = last_state['objetivo']
        st.session_state.tabela = last_state['tabela']
        st.session_state.alternativas = last_state['alternativas']
        st.session_state.criterios = last_state['criterios']
        st.session_state.qual_melhor_alt = last_state['qual_melhor_alt']
        st.session_state.qual_melhor_score = last_state['qual_melhor_score']
        st.session_state.qual_pior_alt = last_state['qual_pior_alt']
        st.session_state.qual_pior_score = last_state['qual_pior_score']
        st.session_state.qual_restantes = last_state['qual_restantes']
        st.session_state.qual_alt_idx = last_state['qual_alt_idx']
        st.session_state.qual_scores_temp = last_state['qual_scores_temp']
        st.session_state.simple_comp_c_comp = last_state.get('simple_comp_c_comp')
        st.session_state.last_selected_qd_key = last_state.get('last_selected_qd_key')
        st.rerun()

# 1. INITIALIZATION OF STATE
if 'tabela' not in st.session_state:
    st.session_state.tabela = None
    st.session_state.objetivo = {}
    st.session_state.passo = "setup" 
    st.session_state.setup_step = "define_alts_crits"
    st.session_state.historico = []

# Global back button (rendered if there is history)
if 'historico' in st.session_state and st.session_state.historico:
    if st.button("⬅️ Voltar ao Passo Anterior", key="btn_global_voltar"):
        voltar_estado()
    st.divider()

# 2. DATA INPUT SECTION (WIZARD PASSO A PASSO)
if st.session_state.passo == "setup":
    if st.session_state.setup_step == "define_alts_crits":
        st.header("Passo 1: Preenchimento da Matriz de Consequências")
        
        origem = st.radio(
            "Como você deseja carregar a matriz de consequências?",
            ["Entrada Manual", "Upload CSV"],
            key="origem_dados"
        )
        
        if origem == "Entrada Manual":
            st.write("Quais são as alternativas e os critérios de decisão para iniciar o processo?")
            alts_input = st.text_input("Quais são as alternativas? (separadas por vírgula)", "VW Polo, Chevy Onix, Hyundai HB20")
            crits_input = st.text_input("Quais são os critérios? (separados por vírgula)", "Preço, Porta_Malas, Km/L")
            
            if st.button("Avançar para a Configuração dos Atributos"):
                alts = [a.strip() for a in alts_input.split(",") if a.strip()]
                crits = [c.strip() for c in crits_input.split(",") if c.strip()]
                
                if len(alts) < 2:
                    st.error("Erro: Informe pelo menos 2 alternativas.")
                elif len(crits) < 1:
                    st.error("Erro: Informe pelo menos 1 critério.")
                else:
                    salvar_estado_historico()
                    st.session_state.alternativas = alts
                    st.session_state.criterios = crits
                    st.session_state.tabela_construcao = pd.DataFrame(0.0, index=alts, columns=crits)
                    st.session_state.objetivo = {}
                    st.session_state.criterio_atual_idx = 0
                    st.session_state.setup_step = "config_criterio"
                    st.session_state.sub_setup_step = "natureza"
                    st.rerun()
        else:
            st.subheader("Importar Matriz por CSV")
            st.markdown("""
            O arquivo deve ser um CSV comum (separado por vírgulas). 
            A **primeira coluna** deve conter os nomes das alternativas. 
            A **primeira linha** de dados deve se chamar **Objetivo** e conter `maximizar` ou `minimizar`.
            """)
            
            with st.expander("Ver exemplo de formato CSV", expanded=False):
                st.code("""Alternativa,Preco,Porta_Malas,Km/L,Zero_a_Cem,Seguranca
Objetivo,minimizar,maximizar,maximizar,minimizar,maximizar
VW Polo,88000,300,13.5,13.4,5
Chevy Onix,86000,275,13.8,13.3,5
Hyundai HB20,84000,300,13.1,14.5,3""", language="csv")

            file = st.file_uploader("Qual arquivo CSV você deseja selecionar?", type="csv")
            if file:
                try:
                    df = pd.read_csv(file, index_col=0)
                    if st.button("Carregar e Processar os Dados"):
                        if "Objetivo" in df.index:
                            salvar_estado_historico()
                            obj_row = df.loc['Objetivo'].str.lower().str.strip().to_dict()
                            st.session_state.objetivo = obj_row
                            st.session_state.tabela = df.drop(index='Objetivo').astype(float)
                            st.session_state.passo = "compensacao"
                            st.rerun()
                        else:
                            st.error("Erro: Não foi encontrada uma linha com o nome 'Objetivo' na primeira coluna.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")

    elif st.session_state.setup_step == "config_criterio":
        crit = st.session_state.criterios[st.session_state.criterio_atual_idx]
        total_crits = len(st.session_state.criterios)
        
        st.header(f"Configuração do Atributo: **{crit}** (Atributo {st.session_state.criterio_atual_idx + 1} de {total_crits})")
        
        if st.session_state.sub_setup_step == "natureza":
            st.subheader("1. Natureza do Objetivo")
            natureza = st.radio(
                f"Qual é o objetivo para '{crit}'?",
                ["maximizar", "minimizar"],
                key=f"nat_{crit}"
            )
            
            if natureza == "maximizar":
                st.info(f"Então quanto maior '{crit}', melhor?")
            else:
                st.info(f"Então quanto menor '{crit}', melhor?")
                
            if st.button("Confirmar e Prosseguir", key=f"btn_nat_conf_{crit}"):
                salvar_estado_historico()
                st.session_state.objetivo[crit] = natureza
                st.session_state.sub_setup_step = "tipo"
                st.rerun()
                
        elif st.session_state.sub_setup_step == "tipo":
            st.subheader("2. Tipo de Atributo")
            tipo = st.radio(
                f"O atributo '{crit}' é quantitativo ou qualitativo?",
                ["quantitativo", "qualitativo"],
                key=f"tipo_{crit}"
            )
            
            st.write("""
            * **Quantitativo:** Possui dados concretos e numéricos (ex: Preço em R$, Consumo em Km/L, etc.).
            * **Qualitativo:** Baseado em escala de percepção subjetiva (ex: Conforto, Design, etc.).
            """)
            
            if st.button("Confirmar e Prosseguir", key=f"btn_tipo_conf_{crit}"):
                salvar_estado_historico()
                if tipo == "quantitativo":
                    st.session_state.sub_setup_step = "quantitativo_input"
                else:
                    st.session_state.sub_setup_step = "qualitativo_melhor"
                    st.session_state.qual_melhor_alt = None
                    st.session_state.qual_melhor_score = 10.0
                    st.session_state.qual_pior_alt = None
                    st.session_state.qual_pior_score = 0.0
                    st.session_state.qual_scores_temp = {}
                st.rerun()
                
        elif st.session_state.sub_setup_step == "quantitativo_input":
            st.subheader("3. Entrada de Dados Numéricos")
            
            valores = {}
            for alt in st.session_state.alternativas:
                valores[alt] = st.number_input(
                    f"Qual o valor de '{crit}' para a alternativa '{alt}'?",
                    value=0.0,
                    format="%.2f",
                    key=f"quant_{crit}_{alt}"
                )
                
            if st.button("Salvar e Prosseguir", key=f"btn_salvar_quant_{crit}"):
                salvar_estado_historico()
                for alt, val in valores.items():
                    st.session_state.tabela_construcao.at[alt, crit] = val
                    
                st.session_state.criterio_atual_idx += 1
                if st.session_state.criterio_atual_idx < len(st.session_state.criterios):
                    st.session_state.sub_setup_step = "natureza"
                else:
                    st.session_state.tabela = st.session_state.tabela_construcao
                    st.session_state.passo = "compensacao"
                st.rerun()
                
        elif st.session_state.sub_setup_step == "qualitativo_melhor":
            st.subheader("3. Avaliação Qualitativa: Melhor Alternativa")
            
            melhor_alt = st.selectbox(
                f"Qual é o melhor no atributo '{crit}'?",
                st.session_state.alternativas,
                key=f"qual_best_{crit}"
            )
            
            score_max = st.slider(
                    f"Qual o score máximo para '{melhor_alt}' (de 0 a 10)?",
                min_value=0.0,
                max_value=10.0,
                value=10.0,
                step=0.1,
                key=f"qual_best_score_{crit}"
            )
            
            if st.button("Confirmar Melhor Alternativa", key=f"btn_conf_melhor_{crit}"):
                salvar_estado_historico()
                st.session_state.qual_melhor_alt = melhor_alt
                st.session_state.qual_melhor_score = score_max
                st.session_state.qual_scores_temp[melhor_alt] = score_max
                st.session_state.sub_setup_step = "qualitativo_pior"
                st.rerun()
                
        elif st.session_state.sub_setup_step == "qualitativo_pior":
            st.subheader("4. Avaliação Qualitativa: Pior Alternativa")
            
            restantes_pior = [a for a in st.session_state.alternativas if a != st.session_state.qual_melhor_alt]
            
            pior_alt = st.selectbox(
                f"Qual é o pior no atributo '{crit}'?",
                restantes_pior,
                key=f"qual_worst_{crit}"
            )
            
            score_min = st.slider(
                    f"Qual o score mínimo para '{pior_alt}' (de 0 a 10)?",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.1,
                key=f"qual_worst_score_{crit}"
            )
            
            if st.button("Confirmar Pior Alternativa", key=f"btn_conf_pior_{crit}"):
                salvar_estado_historico()
                st.session_state.qual_pior_alt = pior_alt
                st.session_state.qual_pior_score = score_min
                st.session_state.qual_scores_temp[pior_alt] = score_min
                
                restantes = [a for a in st.session_state.alternativas if a not in [st.session_state.qual_melhor_alt, pior_alt]]
                if restantes:
                    st.session_state.qual_restantes = restantes
                    st.session_state.qual_alt_idx = 0
                    st.session_state.sub_setup_step = "qualitativo_restantes"
                else:
                    for alt, val in st.session_state.qual_scores_temp.items():
                        st.session_state.tabela_construcao.at[alt, crit] = val
                    
                    st.session_state.criterio_atual_idx += 1
                    if st.session_state.criterio_atual_idx < len(st.session_state.criterios):
                        st.session_state.sub_setup_step = "natureza"
                    else:
                        st.session_state.tabela = st.session_state.tabela_construcao
                        st.session_state.passo = "compensacao"
                st.rerun()
                
        elif st.session_state.sub_setup_step == "qualitativo_restantes":
            alt_atual = st.session_state.qual_restantes[st.session_state.qual_alt_idx]
            st.subheader(f"5. Avaliação Qualitativa: Alternativa '{alt_atual}'")
            
            proximidade = st.radio(
                f"A alternativa '{alt_atual}' está mais perto do pior ('{st.session_state.qual_pior_alt}') ou do melhor ('{st.session_state.qual_melhor_alt}')?",
                ["pior", "melhor"],
                key=f"prox_{crit}_{alt_atual}"
            )
            
            score_max = float(st.session_state.qual_melhor_score)
            score_min = float(st.session_state.qual_pior_score)
            media = (score_max + score_min) / 2.0
            
            if proximidade == "melhor":
                st.info(f"A média entre o melhor ({score_max:.2f}) e o pior ({score_min:.2f}) é {media:.2f}. "
                        f"Como você escolheu 'melhor', defina um score entre a média ({media:.2f}) e o melhor ({score_max:.2f}).")
                score_val = st.slider(
                    f"Qual o score deseja atribuir para '{alt_atual}'?",
                    min_value=float(media),
                    max_value=float(score_max),
                    value=float((media + score_max) / 2.0),
                    step=0.1,
                    key=f"qual_val_{crit}_{alt_atual}"
                )
            else:
                st.info(f"A média entre o melhor ({score_max:.2f}) e o pior ({score_min:.2f}) é {media:.2f}. "
                        f"Como você escolheu 'pior', defina um score entre o pior ({score_min:.2f}) e a média ({media:.2f}).")
                score_val = st.slider(
                    f"Qual o score deseja atribuir para '{alt_atual}'?",
                    min_value=float(score_min),
                    max_value=float(media),
                    value=float((score_min + media) / 2.0),
                    step=0.1,
                    key=f"qual_val_{crit}_{alt_atual}"
                )
                
            if st.button(f"Confirmar Score para {alt_atual}", key=f"btn_conf_score_{crit}_{alt_atual}"):
                salvar_estado_historico()
                st.session_state.qual_alt_idx += 1
                
                if st.session_state.qual_alt_idx >= len(st.session_state.qual_restantes):
                    for alt, val in st.session_state.qual_scores_temp.items():
                        st.session_state.tabela_construcao.at[alt, crit] = val
                        
                    st.session_state.criterio_atual_idx += 1
                    if st.session_state.criterio_atual_idx < len(st.session_state.criterios):
                        st.session_state.sub_setup_step = "natureza"
                    else:
                        st.session_state.tabela = st.session_state.tabela_construcao
                        st.session_state.passo = "compensacao"
                st.rerun()

# 3. INTERFACE DE COMPENSAÇÃO
elif st.session_state.passo == "compensacao":
    tabela_completa = st.session_state.tabela
    objetivos = st.session_state.objetivo

    # Inicializa sub-passo do fluxo de compensação se não existir
    if 'compensacao_step' not in st.session_state:
        st.session_state.compensacao_step = "checar_dominancia"

    tabela_limpa, logs_dom = remover_alternativas_dominadas(tabela_completa, objetivos)
    alternativas_removidas = tabela_completa.index.difference(tabela_limpa.index).tolist()

    # Condição de vitória imediata (apenas 1 alternativa restante)
    if len(tabela_limpa) == 1 and not alternativas_removidas:
        st.balloons()
        st.success(f"### 🏆 Alternativa Vencedora: {tabela_limpa.index[0]}")
        st.session_state.tabela = tabela_limpa
        st.session_state.passo = "final"
        st.rerun()

    # Roteador de passos simplificados
    if alternativas_removidas and st.session_state.compensacao_step != "transicao_pos_compensacao" and st.session_state.compensacao_step != "visualizar_dominancia":
        st.session_state.compensacao_step = "visualizar_dominancia"
    elif not alternativas_removidas and st.session_state.compensacao_step == "visualizar_dominancia":
        st.session_state.compensacao_step = "escolher_acao"
    elif st.session_state.compensacao_step == "checar_dominancia":
        st.session_state.compensacao_step = "escolher_acao"

    if st.session_state.compensacao_step == "visualizar_dominancia":
        st.header("Passo 2: Eliminação de alternativas dominadas")
        st.info("**Dominância =>** Se existir uma alternativa com desempenho inferior em todos os critérios em relação à outra, dizemos que esta alternativa é dominada pela outra; portanto, deve ser eliminada.")
        for log in logs_dom:
            st.warning(f"-> {log}")
            
        st.subheader("Matriz de Consequências")
        st.table(estilizar_tabela(tabela_completa, objetivos, alternativas_removidas))
        
        if st.button("Confirmar Eliminação e Prosseguir"):
            salvar_estado_historico()
            st.session_state.tabela = tabela_limpa
            st.session_state.compensacao_step = "escolher_acao"
            st.rerun()

    elif st.session_state.compensacao_step == "transicao_pos_compensacao":
        st.header("Resultado da Compensação")
        
        if 'mensagem_sucesso' in st.session_state:
            st.success(st.session_state.mensagem_sucesso)
        
        if 'ultimo_atributo_removido' in st.session_state and st.session_state.ultimo_atributo_removido:
            st.warning(f"⚠️ O atributo '{st.session_state.ultimo_atributo_removido}' foi igualado para todas as alternativas e foi removido da matriz.")
            del st.session_state.ultimo_atributo_removido
            
        st.subheader("Matriz de Consequências Atualizada")
        celulas_alt = st.session_state.get('celulas_alteradas', [])
        st.table(estilizar_tabela(st.session_state.tabela, objetivos, celulas_alteradas=celulas_alt))
        
        if st.button("Prosseguir para Próxima Rodada"):
            salvar_estado_historico()
            if 'celulas_alteradas' in st.session_state:
                del st.session_state.celulas_alteradas
            if 'mensagem_sucesso' in st.session_state:
                del st.session_state.mensagem_sucesso
            st.session_state.compensacao_step = "checar_dominancia"
            st.rerun()
    else:
        # Passo 3: Escolher Ação e Executar
        st.header("Passo 3: Compensações")
        
        quase_dominacoes = detectar_quase_dominacoes(tabela_completa, objetivos)
        
        if quase_dominacoes:
            opcao_acao = st.radio(
                "O que deseja fazer nesta rodada?",
                ["Resolver uma Compensação Simples (Quase-Dominação)", "Fazer uma Compensação Subjetiva (Manual)"],
                key="opcao_acao_compensacao"
            )
        else:
            opcao_acao = "Fazer uma Compensação Subjetiva (Manual)"
            
        if opcao_acao == "Resolver uma Compensação Simples (Quase-Dominação)":
            st.subheader("3.1. Compensação Simples (Quase-Dominação)")
            st.info("Quase dominação significa que uma alternativa só não domina a outra por causa de exatamente um atributo.")
            
            options = []
            for idx, qd in enumerate(quase_dominacoes):
                label = f"'{qd['alt_quase_dominada']}' quase dominada por '{qd['alt_dominadora']}' (bloqueio em '{qd['atributo_bloqueio']}')"
                options.append((label, qd))
                
            selected_option = st.selectbox(
                "Qual relação de quase-dominação deseja resolver?",
                options,
                format_func=lambda x: x[0]
            )
            
            if selected_option:
                selected_qd = selected_option[1]
                label_qd = selected_option[0]
                alt_b = selected_qd['alt_quase_dominada']
                alt_a = selected_qd['alt_dominadora']
                c_block = selected_qd['atributo_bloqueio']
                c_comps = selected_qd['atributos_compensar']
                val_b_block = selected_qd['valor_quase_dominada_bloqueio']
                val_a_block = selected_qd['valor_dominadora_bloqueio']
                
                # Reset simple comp selection if we switch relation
                if 'last_selected_qd_key' not in st.session_state or st.session_state.last_selected_qd_key != label_qd:
                    st.session_state.last_selected_qd_key = label_qd
                    st.session_state.simple_comp_c_comp = None
                
                c_comp = st.session_state.get('simple_comp_c_comp')
                
                if c_comp is None:
                    st.info(f"👉 **Instrução:** Em qual atributo de '{alt_b}' deseja realizar a compensação? Clique no cabeçalho correspondente na matriz abaixo.")
                else:
                    st.info(f"✍️ **Instrução:** Qual o novo valor de '{c_comp}' para '{alt_b}'? Por favor, preencha-o na célula com a seta (→) e confirme na pergunta abaixo.")
                
                N = len(tabela_completa.columns) + 1
                
                # Header Row
                cols = st.columns(N)
                with cols[0]:
                    st.markdown("**Alternativa**")
                for idx, col_name in enumerate(tabela_completa.columns):
                    with cols[idx + 1]:
                        if col_name == c_block:
                            st.markdown(f"**{col_name} (Bloqueio)**")
                        elif col_name == c_comp:
                            if st.button(f"{col_name} (Compensar)", key=f"btn_header_simple_comp_{col_name}"):
                                st.session_state.simple_comp_c_comp = col_name
                                st.rerun()
                        elif col_name in c_comps:
                            if st.button(col_name, key=f"btn_header_simple_comp_{col_name}"):
                                st.session_state.simple_comp_c_comp = col_name
                                st.rerun()
                        else:
                            st.markdown(f"**{col_name}**")
                            
                # Data Rows
                novo_val = None
                for alt in tabela_completa.index:
                    cols = st.columns(N)
                    with cols[0]:
                        st.markdown(f"**{alt}**")
                    for j, col_name in enumerate(tabela_completa.columns):
                        val_atual = tabela_completa.at[alt, col_name]
                        with cols[j + 1]:
                            if c_comp is not None:
                                if alt == alt_b and col_name == c_block:
                                    st.write(f"{val_atual:.2f} → {val_a_block:.2f}")
                                elif alt == alt_b and col_name == c_comp:
                                    c_antigo, c_novo = st.columns([2, 3])
                                    with c_antigo:
                                        st.write(f"{val_atual:.2f} →")
                                    with c_novo:
                                        novo_val = st.number_input(
                                            "Novo valor",
                                            value=float(val_atual),
                                            key=f"ss_val_grid_{alt}_{col_name}",
                                            format="%.2f",
                                            label_visibility="collapsed"
                                        )
                                else:
                                    st.write(f"{val_atual:.2f}")
                            else:
                                if alt == alt_b and col_name == c_block:
                                    st.write(f"{val_atual:.2f} (Melhorar)")
                                else:
                                    st.write(f"{val_atual:.2f}")
                                    
                if c_comp is not None and novo_val is not None:
                    st.divider()
                    val_atual_comp = tabela_completa.at[alt_b, c_comp]
                    st.write(f"**Pergunta de Confirmação:** O atributo **'{c_block}'** de **'{alt_b}'** será alterado de **{val_b_block:.2f}** para **{val_a_block:.2f}**. Isso vale a alteração de **'{c_comp}'** de **{val_atual_comp:.2f}** para **{novo_val:.2f}**?")
                    
                    if st.button("Confirmar Compensação Simples", key="btn_confirmar_compensacao_simples"):
                        salvar_estado_historico()
                        st.session_state.tabela = st.session_state.tabela.loc[tabela_completa.index]
                        st.session_state.tabela.at[alt_b, c_comp] = novo_val
                        st.session_state.tabela.at[alt_b, c_block] = val_a_block
                        
                        has_dropped_c_block = False
                        if st.session_state.tabela[c_block].nunique() == 1:
                            has_dropped_c_block = True
                            
                        st.session_state.celulas_alteradas = [(alt_b, c_comp)]
                        if not has_dropped_c_block:
                            st.session_state.celulas_alteradas.append((alt_b, c_block))
                            
                        st.session_state.mensagem_sucesso = f"O atributo {c_block} foi igualado e compensado em uma mudança em {c_comp} na alternativa {alt_b}."
                        
                        if has_dropped_c_block:
                            st.session_state.tabela = st.session_state.tabela.drop(columns=[c_block])
                            del st.session_state.objetivo[c_block]
                            st.session_state.ultimo_atributo_removido = c_block
                        else:
                            st.session_state.ultimo_atributo_removido = None
                            
                        if 'simple_comp_c_comp' in st.session_state:
                            del st.session_state.simple_comp_c_comp
                        if 'last_selected_qd_key' in st.session_state:
                            del st.session_state.last_selected_qd_key
                            
                        st.session_state.compensacao_step = "transicao_pos_compensacao"
                        st.rerun()
        else:
            st.subheader("3.2. Compensações Subjetivas")
            
            if 'interacao' not in st.session_state:
                st.session_state.interacao = {
                    'passo_interativo': 'selecionar_eliminar',
                    'attr_eliminar': None,
                    'valor_alvo': None,
                    'attr_compensar': None
                }
                
            interac = st.session_state.interacao
            step = interac['passo_interativo']
            
            # Instructions
            if step == 'selecionar_eliminar':
                st.info("👉 **Instrução:** Qual atributo você deseja fixar e eliminar? Clique no cabeçalho correspondente na matriz abaixo.")
            elif step == 'selecionar_valor':
                st.info(f"👉 **Instrução:** Qual valor da coluna '{interac['attr_eliminar']}' você deseja fixar? Clique na célula correspondente na matriz abaixo.")
            elif step == 'selecionar_compensar':
                st.info(f"👉 **Instrução:** Em qual atributo será feita a compensação? Clique no cabeçalho correspondente na matriz abaixo.")
            elif step == 'preencher_valores':
                st.info(f"✍️ **Instrução:** Quais são os novos valores de compensação para a coluna '{interac['attr_compensar']}' nas células com a seta (→)? Por favor, insira-os na matriz e confirme na pergunta abaixo.")
            
            N = len(tabela_completa.columns) + 1
            
            # Header Row
            cols = st.columns(N)
            with cols[0]:
                st.markdown("**Alternativa**")
                
            for idx, col_name in enumerate(tabela_completa.columns):
                with cols[idx + 1]:
                    if step == 'selecionar_eliminar':
                        if st.button(col_name, key=f"btn_header_elim_{col_name}"):
                            st.session_state.interacao['attr_eliminar'] = col_name
                            st.session_state.interacao['passo_interativo'] = 'selecionar_valor'
                            st.rerun()
                    elif step == 'selecionar_compensar':
                        if col_name == interac['attr_eliminar']:
                            st.markdown(f"**{col_name} (Fixado)**")
                        else:
                            if st.button(col_name, key=f"btn_header_comp_{col_name}"):
                                st.session_state.interacao['attr_compensar'] = col_name
                                st.session_state.interacao['passo_interativo'] = 'preencher_valores'
                                st.rerun()
                    else:
                        if col_name == interac['attr_eliminar']:
                            st.markdown(f"**{col_name} (Fixado)**")
                        elif col_name == interac['attr_compensar']:
                            st.markdown(f"**{col_name} (Compensar)**")
                        else:
                            st.markdown(f"**{col_name}**")
                            
            # Data Rows
            novos_valores = {}
            for alt in tabela_completa.index:
                cols = st.columns(N)
                with cols[0]:
                    st.markdown(f"**{alt}**")
                    
                for j, col_name in enumerate(tabela_completa.columns):
                    val_atual = tabela_completa.at[alt, col_name]
                    with cols[j + 1]:
                        if step == 'selecionar_valor':
                            if col_name == interac['attr_eliminar']:
                                if st.button(f"{val_atual:.2f}", key=f"btn_cell_{alt}_{col_name}"):
                                    st.session_state.interacao['valor_alvo'] = val_atual
                                    st.session_state.interacao['passo_interativo'] = 'selecionar_compensar'
                                    st.rerun()
                            else:
                                st.write(f"{val_atual:.2f}")
                        elif step == 'preencher_valores':
                            attr_elim = interac['attr_eliminar']
                            attr_comp = interac['attr_compensar']
                            val_alvo = interac['valor_alvo']
                            
                            if col_name == attr_elim:
                                if np.isclose(val_atual, val_alvo):
                                    st.write(f"{val_atual:.2f}")
                                else:
                                    st.write(f"{val_atual:.2f} → {val_alvo:.2f}")
                            elif col_name == attr_comp:
                                val_atual_elim = tabela_completa.at[alt, attr_elim]
                                if np.isclose(val_atual_elim, val_alvo):
                                    st.write(f"{val_atual:.2f}")
                                    novos_valores[alt] = val_atual
                                else:
                                    c_antigo, c_novo = st.columns([2, 3])
                                    with c_antigo:
                                        st.write(f"{val_atual:.2f} →")
                                    with c_novo:
                                        novos_valores[alt] = st.number_input(
                                            "Novo valor",
                                            value=float(val_atual),
                                            key=f"input_grid_{alt}_{col_name}",
                                            format="%.2f",
                                            label_visibility="collapsed"
                                        )
                            else:
                                st.write(f"{val_atual:.2f}")
                        else:
                            st.write(f"{val_atual:.2f}")
                            
            if step == 'preencher_valores':
                st.divider()
                st.write(f"**Pergunta de Confirmação:** Para neutralizar e eliminar o atributo **'{interac['attr_eliminar']}'** (fixando todas as alternativas em **{interac['valor_alvo']:.2f}**), você aceita realizar as compensações no atributo **'{interac['attr_compensar']}'** conforme os novos valores informados?")
                
                if st.button("Confirmar Compensação e Atualizar", key="btn_confirmar_compensacao_subjetiva"):
                    salvar_estado_historico()
                    
                    # Calculate modified alternatives (where original value is different from valor_alvo)
                    attr_elim = interac['attr_eliminar']
                    attr_comp = interac['attr_compensar']
                    val_alvo = interac['valor_alvo']
                    alts_modificadas = [alt for alt in tabela_completa.index if not np.isclose(tabela_completa.at[alt, attr_elim], val_alvo)]
                    
                    # Store cell coordinates for styling
                    st.session_state.celulas_alteradas = [(alt, attr_comp) for alt in alts_modificadas]
                    
                    # Format names in Portuguese list format
                    alts_str = formatar_lista_portugues(alts_modificadas)
                    st.session_state.mensagem_sucesso = f"O atributo {attr_elim} foi igualado e compensado em uma mudança em {attr_comp} nas alternativas {alts_str}."
                    
                    st.session_state.ultimo_atributo_removido = interac['attr_eliminar']
                    st.session_state.tabela = st.session_state.tabela.loc[tabela_completa.index]
                    for a, nv in novos_valores.items():
                        st.session_state.tabela.at[a, interac['attr_compensar']] = nv
                        
                    st.session_state.tabela = st.session_state.tabela.drop(columns=[interac['attr_eliminar']])
                    del st.session_state.objetivo[interac['attr_eliminar']]
                    
                    st.session_state.interacao = {
                        'passo_interativo': 'selecionar_eliminar',
                        'attr_eliminar': None,
                        'valor_alvo': None,
                        'attr_compensar': None
                    }
                    st.session_state.compensacao_step = "transicao_pos_compensacao"
                    st.rerun()

# 4. FINAL STATE
else:
    st.header("Resultado Final")
    st.table(st.session_state.tabela.style.format(precision=2))
    if st.button("Reiniciar Sistema"):
        st.session_state.clear()
        st.rerun()