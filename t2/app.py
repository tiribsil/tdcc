import streamlit as st
import pandas as pd
import numpy as np

# =====================================================================
# LOGIC CORE
# =====================================================================

def verificar_dominacao(linha_a, linha_b, dicionario_objetivo, tolerance=1e-9):
    pelo_menos_um_melhor = False
    for atributo, objetivo in dicionario_objetivo.items():
        valor_a = linha_a[atributo]
        valor_b = linha_b[atributo]
        if abs(valor_a - valor_b) < tolerance:
            continue
        
        if objetivo == 'maximizar':
            if valor_a < valor_b: return False
            if valor_a > valor_b: pelo_menos_um_melhor = True
        elif objetivo == 'minimizar':
            if valor_a > valor_b: return False
            if valor_a < valor_b: pelo_menos_um_melhor = True
            
    return pelo_menos_um_melhor

def remover_alternativas_dominadas(tabela, dicionario_objetivo):
    alternativas_para_remover = []
    nomes_alternativas = tabela.index.tolist()
    logs = []
    
    for i, nome_a in enumerate(nomes_alternativas):
        if nome_a in alternativas_para_remover: continue
        for j, nome_b in enumerate(nomes_alternativas):
            if i == j or nome_b in alternativas_para_remover: continue
            if verificar_dominacao(tabela.loc[nome_a], tabela.loc[nome_b], dicionario_objetivo):
                alternativas_para_remover.append(nome_b)
                logs.append(f"'{nome_b}' removida (dominada por '{nome_a}')")
                
    tabela_limpa = tabela.drop(index=alternativas_para_remover)
    return tabela_limpa, logs

def estilizar_tabela(df, objetivos):
    def highlight_best(col):
        obj = objetivos.get(col.name)
        is_best = [False] * len(col)
        if obj == 'maximizar':
            is_best = col == col.max()
        elif obj == 'minimizar':
            is_best = col == col.min()
        return ['background-color: rgba(144, 238, 144, 0.3)' if v else '' for v in is_best]

    return df.style.apply(highlight_best, axis=0).format(precision=2)

# =====================================================================
# WEB INTERFACE (STREAMLIT)
# =====================================================================

st.set_page_config(page_title="Even Swap Decision Tool", layout="wide")

st.title("⚖️ Even Swap Decision Support")

# 1. INITIALIZATION OF STATE
if 'tabela' not in st.session_state:
    st.session_state.tabela = None
    st.session_state.objetivo = {}
    st.session_state.passo = "setup" 

# 2. DATA INPUT SECTION
if st.session_state.passo == "setup":
    st.header("1. Configuração Inicial")
    
    st.info("""
    **Como funciona o Objetivo?**
    - **maximizar:** Você quer o MAIOR valor (ex: Segurança, Km/L).
    - **minimizar:** Você quer o MENOR valor (ex: Preço, 0 a 100).
    """)
    
    origem = st.radio("Escolha como carregar os dados:", ["Upload CSV", "Entrada Manual"])

    if origem == "Upload CSV":
        st.subheader("Configuração do Arquivo CSV")
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

        file = st.file_uploader("Selecione o arquivo CSV", type="csv")
        if file:
            try:
                df = pd.read_csv(file, index_col=0)
                if st.button("Carregar e Processar Dados"):
                    if "Objetivo" in df.index:
                        obj_row = df.loc['Objetivo'].str.lower().str.strip().to_dict()
                        st.session_state.objetivo = obj_row
                        st.session_state.tabela = df.drop(index='Objetivo').astype(float)
                        st.session_state.passo = "swap"
                        st.rerun()
                    else:
                        st.error("Erro: Não foi encontrada uma linha com o nome 'Objetivo' na primeira coluna.")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo: {e}")

    else:
        with st.expander("Definir Matriz Manualmente", expanded=True):
            alts_input = st.text_input("Alternativas (separadas por vírgula)", "VW Polo, Chevy Onix, Hyundai HB20")
            crits_input = st.text_input("Critérios (separados por vírgula)", "Preço, Porta_Malas, Km/L")
            
            alternativas = [a.strip() for a in alts_input.split(",")]
            criterios = [c.strip() for c in crits_input.split(",")]
            
            st.write("### Defina o Objetivo para cada Critério")
            cols = st.columns(len(criterios))
            objs = {}
            for i, crit in enumerate(criterios):
                objs[crit] = cols[i].selectbox(
                    f"{crit}", ["maximizar", "minimizar"], key=f"obj_{crit}"
                )
            
            df_init = pd.DataFrame(0.0, index=alternativas, columns=criterios)
            edited_df = st.data_editor(df_init, width='stretch')
            
            if st.button("Iniciar Processo Even Swap"):
                st.session_state.tabela = edited_df
                st.session_state.objetivo = objs
                st.session_state.passo = "swap"
                st.rerun()

# 3. SWAP INTERFACE
elif st.session_state.passo == "swap":
    st.header("2. Processo de Even Swap")
    
    tabela = st.session_state.tabela
    objetivos = st.session_state.objetivo

    tabela, logs_dom = remover_alternativas_dominadas(tabela, objetivos)
    st.session_state.tabela = tabela
    for log in logs_dom:
        st.warning(log)

    if len(tabela) == 1:
        st.balloons()
        st.success(f"### 🏆 Alternativa Vencedora: {tabela.index[0]}")
        st.session_state.passo = "final"
        st.rerun()

    st.subheader("Matriz de Consequências Atual")
    st.table(estilizar_tabela(tabela, objetivos))

    st.divider()
    st.subheader("Configurar Troca (Swap)")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        attr_eliminar = st.selectbox("Fixar e eliminar atributo:", tabela.columns)
    
    with c2:
        obj_atual = objetivos[attr_eliminar]
        melhor_valor = tabela[attr_eliminar].max() if obj_atual == 'maximizar' else tabela[attr_eliminar].min()
        valor_alvo = st.number_input(f"Valor alvo para '{attr_eliminar}':", value=float(melhor_valor), format="%.2f")
    
    with c3:
        outros_attrs = [c for c in tabela.columns if c != attr_eliminar]
        attr_compensar = st.selectbox("Compensar no atributo:", outros_attrs)

    st.info(f"Ao mudar '{attr_eliminar}' para **{valor_alvo:.2f}**, ajuste o valor de '{attr_compensar}' para manter as alternativas equivalentes:")
    
    novos_valores = {}
    for alt in tabela.index:
        val_atual_elim = tabela.at[alt, attr_eliminar]
        val_atual_comp = tabela.at[alt, attr_compensar]
        
        col_info, col_input = st.columns([1, 1])
        with col_info:
            st.markdown(f"**{alt}**")
            st.caption(f"{attr_eliminar}: {val_atual_elim:.2f} → {valor_alvo:.2f}")
        
        with col_input:
            if np.isclose(val_atual_elim, valor_alvo):
                st.write(f"Já está no alvo ({val_atual_comp:.2f})")
                novos_valores[alt] = val_atual_comp
            else:
                # MUDANÇA AQUI: Adicionada key dinâmica para garantir que o valor sugerido seja sempre o atual
                novos_valores[alt] = st.number_input(
                    f"Novo '{attr_compensar}' para {alt}", 
                    value=float(val_atual_comp),
                    key=f"comp_{alt}_{attr_eliminar}_{attr_compensar}",
                    format="%.2f"
                )

    if st.button("Confirmar Troca e Atualizar"):
        for alt, novo_val in novos_valores.items():
            st.session_state.tabela.at[alt, attr_compensar] = novo_val
        
        st.session_state.tabela = st.session_state.tabela.drop(columns=[attr_eliminar])
        del st.session_state.objetivo[attr_eliminar]
        st.rerun()

# 4. FINAL STATE
else:
    st.header("Resultado Final")
    st.table(st.session_state.tabela.style.format(precision=2))
    if st.button("Reiniciar Sistema"):
        st.session_state.clear()
        st.rerun()