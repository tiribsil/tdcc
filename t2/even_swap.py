import pandas as pd
import numpy as np

# =====================================================================
# INTERFACES ABSTRATAS (ENCAPSULAMENTO PARA FUTURO WEBAPP)
# =====================================================================

class InterfaceBase:
    """
    Classe base abstrata definindo todas as interações necessárias para o algoritmo.
    Para migrar para Web App ou GUI, basta herdar desta classe e implementar as
    entradas/saídas de forma assíncrona ou orientada a eventos.
    """
    def escolher_origem_dados(self) -> str:
        """Retorna 'csv' ou 'interativo'"""
        raise NotImplementedError

    def pedir_nome_arquivo_csv(self) -> str:
        """Retorna o caminho do arquivo CSV"""
        raise NotImplementedError

    def obter_dados_tabela_interativa(self) -> tuple:
        """Retorna (DataFrame, dicionario_natureza)"""
        raise NotImplementedError

    def exibir_tabela(self, tabela: pd.DataFrame, titulo: str):
        """Apresenta a tabela de consequências atualizada"""
        raise NotImplementedError

    def informar_dominacoes(self, logs: list):
        """Notifica o descarte de alternativas dominadas"""
        raise NotImplementedError

    def pedir_swap_simples(self, quase_dominacoes: list, tabela: pd.DataFrame) -> dict:
        """Retorna as informações do swap simples escolhido, ou None para pular"""
        raise NotImplementedError

    def pedir_atributo_eliminar(self, atributos_disponiveis: list) -> str:
        """Retorna qual atributo o decisor quer fixar e eliminar"""
        raise NotImplementedError

    def pedir_valor_alvo_fixar(self, atributo: str, valores_existentes: list, melhor_valor: float) -> float:
        """Retorna o valor para o qual o atributo_eliminar será igualado"""
        raise NotImplementedError

    def pedir_atributo_compensar(self, atributo_eliminar: str, atributos_disponiveis: list) -> str:
        """Retorna qual atributo sofrerá a compensação"""
        raise NotImplementedError

    def pedir_novo_valor_compensacao(self, alternativa: str, atributo_eliminar: str, 
                                    valor_atual: float, valor_alvo: float, 
                                    atributo_compensar: str, valor_atual_compensar: float) -> float:
        """Retorna o novo valor subjetivo compensado para aquela alternativa específica"""
        raise NotImplementedError

    def exibir_resultado_final(self, tabela: pd.DataFrame):
        """Apresenta a alternativa vencedora ou o estado final da tabela"""
        raise NotImplementedError


# =====================================================================
# LÓGICA DO ALGORITMO (INDEPENDENTE DE INTERFACE)
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
                logs.append(f"{nome_b} foi removida pois é pior ou igual a {nome_a} em todos os aspectos.")
                
    tabela_limpa = tabela.drop(index=alternativas_para_remover)
    return tabela_limpa, logs

def detectar_quase_dominacoes(tabela, dicionario_objetivo):
    quase_dominacoes = []
    nomes_alternativas = tabela.index.tolist()
    tolerance = 1e-9
    
    for i, nome_a in enumerate(nomes_alternativas):
        for j, nome_b in enumerate(nomes_alternativas):
            if i == j:
                continue
            
            linha_a = tabela.loc[nome_a]
            linha_b = tabela.loc[nome_b]
            
            atributos_b_melhor = []
            atributos_a_melhor = []
            
            for atributo, objetivo in dicionario_objetivo.items():
                val_a = linha_a[atributo]
                val_b = linha_b[atributo]
                
                if abs(val_a - val_b) < tolerance:
                    continue
                
                if objetivo == 'maximizar':
                    if val_b > val_a:
                        atributos_b_melhor.append(atributo)
                    elif val_a > val_b:
                        atributos_a_melhor.append(atributo)
                elif objetivo == 'minimizar':
                    if val_b < val_a:
                        atributos_b_melhor.append(atributo)
                    elif val_a < val_b:
                        atributos_a_melhor.append(atributo)
            
            if len(atributos_b_melhor) == 1 and len(atributos_a_melhor) >= 1:
                quase_dominacoes.append({
                    'alt_dominadora': nome_a,
                    'alt_quase_dominada': nome_b,
                    'atributo_bloqueio': atributos_b_melhor[0],
                    'valor_dominadora_bloqueio': float(linha_a[atributos_b_melhor[0]]),
                    'valor_quase_dominada_bloqueio': float(linha_b[atributos_b_melhor[0]]),
                    'atributos_compensar': atributos_a_melhor
                })
                
    return quase_dominacoes

def executar_algoritmo_even_swap(tabela, dicionario_objetivo, interface):
    """
    Orquestra as etapas de Even Swap guiadas pelo decisor.
    """
    interface.exibir_tabela(tabela, "Passo 1: Matriz de Consequências Inicial")
    
    while len(tabela) > 1:
        # Loop interno: remover dominados ou fazer swap simples
        while True:
            tabela_antes = len(tabela)
            tabela_limpa, logs = remover_alternativas_dominadas(tabela, dicionario_objetivo)
            if len(tabela_limpa) < tabela_antes:
                # Mostrar tabela com as alternativas dominadas riscadas
                tabela_riscada = tabela.copy()
                removidas = tabela.index.difference(tabela_limpa.index)
                tabela_riscada.index = [
                    "".join([char + '\u0336' for char in name]) if name in removidas else name
                    for name in tabela_riscada.index
                ]
                interface.informar_dominacoes(logs)
                interface.exibir_tabela(tabela_riscada, "Passo 2: Eliminação de alternativas dominadas (Riscadas serão removidas)")
                tabela = tabela_limpa
                continue
            
            if len(tabela) <= 1:
                break
                
            # Buscar quase dominações
            quase_dominacoes = detectar_quase_dominacoes(tabela, dicionario_objetivo)
            if quase_dominacoes:
                # Perguntar ao decisor se deseja realizar um swap simples
                swap_info = interface.pedir_swap_simples(quase_dominacoes, tabela)
                if swap_info:
                    alt_b = swap_info['alt_quase_dominada']
                    c_block = swap_info['atributo_bloqueio']
                    val_alvo = swap_info['valor_alvo_bloqueio']
                    c_comp = swap_info['atributo_compensar']
                    novo_val = swap_info['novo_valor_compensar']
                    
                    # Aplicar a compensação no atributo de compensação para a alternativa B
                    tabela.at[alt_b, c_comp] = novo_val
                    # Igualar o atributo de bloqueio de B ao valor da alternativa dominadora A
                    tabela.at[alt_b, c_block] = val_alvo
                    
                    interface.exibir_tabela(tabela, f"Passo 3: Compensações - 3.1. Even Swap Simples realizado (Compensado: {alt_b} | '{c_block}' e '{c_comp}')")
                    continue
            
            break
            
        if len(tabela) <= 1:
            break
            
        if len(tabela.columns) <= 1:
            interface.exibir_tabela(tabela, "FIM DO PROCESSO (Apenas 1 critério restante, sem dominância óbvia)")
            break
            
        # Etapa 2: Escolha manual dos atributos para o Swap (Passo 3.1 do PDF)
        atributos_disponiveis = list(tabela.columns)
        atributo_eliminar = interface.pedir_atributo_eliminar(atributos_disponiveis)
        
        valores_existentes = tabela[atributo_eliminar].tolist()
        objetivo_eliminar = dicionario_objetivo[atributo_eliminar]
        melhor_valor = tabela[atributo_eliminar].max() if objetivo_eliminar == 'maximizar' else tabela[atributo_eliminar].min()
        
        # Define para qual valor igualar
        valor_alvo = interface.pedir_valor_alvo_fixar(atributo_eliminar, valores_existentes, melhor_valor)
        
        atributos_compensar_disponiveis = [col for col in atributos_disponiveis if col != atributo_eliminar]
        atributo_compensar = interface.pedir_atributo_compensar(atributo_eliminar, atributos_compensar_disponiveis)
        
        # Etapa 3: Aplicar compensações subjetivas individuais por alternativa (Passo 3.2 do PDF)
        for alternativa in tabela.index:
            valor_atual = tabela.at[alternativa, atributo_eliminar]
            
            # Se já está no valor alvo (dentro da tolerância), nenhuma compensação é necessária
            if np.isclose(valor_atual, valor_alvo):
                continue
                
            valor_atual_compensar = tabela.at[alternativa, atributo_compensar]
            novo_valor_compensar = interface.pedir_novo_valor_compensacao(
                alternativa=alternativa,
                atributo_eliminar=atributo_eliminar,
                valor_atual=valor_atual,
                valor_alvo=valor_alvo,
                atributo_compensar=atributo_compensar,
                valor_atual_compensar=valor_atual_compensar
            )
            tabela.at[alternativa, atributo_compensar] = novo_valor_compensar
            
        # Iguala a coluna eliminada
        tabela[atributo_eliminar] = valor_alvo
        
        # Etapa 4: Eliminar coluna neutralizada (Passo 3.4 do PDF)
        tabela = tabela.drop(columns=[atributo_eliminar])
        del dicionario_objetivo[atributo_eliminar]
        
        interface.exibir_tabela(tabela, f"Passo 3: Compensações - 3.4. Eliminação do objetivo irrelevante (retirado '{atributo_eliminar}')")

    interface.exibir_resultado_final(tabela)


# =====================================================================
# INTERFACE EM MODO TERMINAL
# =====================================================================

class InterfaceTerminal(InterfaceBase):
    def escolher_origem_dados(self) -> str:
        print("\n=== Tomada de Decisão Multicritério: Sistema de Compensação (Even Swap) ===")
        print("Como deseja carregar a matriz de consequências?")
        print("1 - Carregar arquivo CSV")
        print("2 - Montar a tabela iterativamente no terminal")
        while True:
            opcao = input("Escolha uma opção (1 ou 2): ").strip()
            if opcao == '1':
                return 'csv'
            elif opcao == '2':
                return 'interativo'
            print("Opção inválida. Digite 1 ou 2.")

    def pedir_nome_arquivo_csv(self) -> str:
        nome = input("\nDigite o caminho/nome do arquivo CSV (padrão: entrada.csv): ").strip()
        if not nome:
            return "entrada.csv"
        return nome

    def obter_dados_tabela_interativa(self) -> tuple:
        print("\n--- Passo 1: Preenchimento da Matriz de Consequências ---")
        
        # 1. Entrada de alternativas
        while True:
            alts_str = input("Digite o nome das alternativas separadas por vírgula:\nExemplo: Strata, Quantum, Vanguard, Pragma, Nexxo\n> ").strip()
            alternativas = [a.strip() for a in alts_str.split(",") if a.strip()]
            if len(alternativas) >= 2:
                break
            print("Erro: São necessárias pelo menos 2 alternativas.")
            
        # 2. Entrada de critérios
        while True:
            crits_str = input("\nDigite o nome dos critérios/objetivos separados por vírgula:\nExemplo: Preço, Experiência, Confiança\n> ").strip()
            critérios = [c.strip() for c in crits_str.split(",") if c.strip()]
            if len(critérios) >= 2:
                break
            print("Erro: São necessários pelo menos 2 critérios.")
            
        dicionario_objetivo = {}
        tipo_criterio = {}
        
        # 3. Natureza e Tipo de cada critério
        for crit in critérios:
            print(f"\nConfigurando critério: '{crit}'")
            while True:
                objetivo = input(f"  Qual o objetivo de '{crit}'? (maximizar = quanto maior melhor | minimizar = quanto menor melhor): ").strip().lower()
                if objetivo in ['maximizar', 'minimizar']:
                    dicionario_objetivo[crit] = objetivo
                    break
                print("  Entrada inválida. Digite 'maximizar' ou 'minimizar'.")
            
            while True:
                tipo = input(f"  O critério '{crit}' é quantitativo ou qualitativo? (quant | qual): ").strip().lower()
                if tipo in ['quant', 'qual', 'quantitativo', 'qualitativo']:
                    tipo_criterio[crit] = 'quant' if tipo.startswith('quan') else 'qual'
                    break
                print("  Entrada inválida. Digite 'quant' ou 'qual'.")

        # 4. Preenchimento de consequências
        tabela = pd.DataFrame(index=alternativas, columns=critérios, dtype=float)
        
        for crit in critérios:
            print(f"\nPreenchendo valores para o critério: '{crit}' ({dicionario_objetivo[crit]} é melhor)")
            
            if tipo_criterio[crit] == 'quant':
                # Entrada direta
                for alt in alternativas:
                    while True:
                        try:
                            val = float(input(f"  Valor de '{crit}' para a alternativa '{alt}': "))
                            tabela.at[alt, crit] = val
                            break
                        except ValueError:
                            print("  Por favor, digite um número válido.")
            else:
                # Passo a Passo Qualitativo (Passos 1.1 a 1.7 do PDF)
                print(f"  [Avaliação Qualitativa para '{crit}']")
                
                # Passo 1.2: Melhor alternativa
                print("  Alternativas disponíveis:", ", ".join(alternativas))
                while True:
                    melhor_alt = input(f"  Qual alternativa possui a MELHOR avaliação no critério '{crit}'? ").strip()
                    if melhor_alt in alternativas:
                        break
                    print("  Alternativa inválida. Escolha uma da lista.")
                
                while True:
                    try:
                        score_max = float(input(f"  Atribua um score máximo para '{melhor_alt}' (de 0 a 10): "))
                        if 0 <= score_max <= 10:
                            tabela.at[melhor_alt, crit] = score_max
                            break
                        print("  O score deve estar entre 0 e 10.")
                    except ValueError:
                        print("  Por favor, digite um número válido.")
                        
                # Passo 1.3: Pior alternativa
                restantes = [a for a in alternativas if a != melhor_alt]
                print("  Alternativas restantes:", ", ".join(restantes))
                while True:
                    pior_alt = input(f"  Qual alternativa possui a PIOR avaliação no critério '{crit}'? ").strip()
                    if pior_alt in restantes:
                        break
                    print("  Alternativa inválida. Escolha uma das restantes.")
                
                while True:
                    try:
                        score_min = float(input(f"  Atribua um score mínimo para '{pior_alt}' (de 0 a 10): "))
                        if 0 <= score_min <= 10:
                            tabela.at[pior_alt, crit] = score_min
                            break
                        print("  O score deve estar entre 0 e 10.")
                    except ValueError:
                        print("  Por favor, digite um número válido.")

                # Passos 1.4 a 1.6: Demais alternativas
                restantes = [a for a in restantes if a != pior_alt]
                
                if restantes:
                    # Terceira alternativa (Passo 1.4)
                    alt_3 = restantes[0]
                    print(f"\n  Avaliando terceira alternativa '{alt_3}':")
                    while True:
                        proxima = input(f"    Ela está mais próxima da melhor ('{melhor_alt}': {score_max}) ou da pior ('{pior_alt}': {score_min})? (melhor/pior): ").strip().lower()
                        if proxima in ['melhor', 'pior']:
                            break
                        print("    Por favor, responda 'melhor' ou 'pior'.")
                    
                    while True:
                        try:
                            score = float(input(f"    Atribua um score para '{alt_3}' (de 0 a 10): "))
                            if 0 <= score <= 10:
                                tabela.at[alt_3, crit] = score
                                break
                            print("    O score deve estar entre 0 e 10.")
                        except ValueError:
                            print("    Por favor, digite um número válido.")
                    
                    # Demais alternativas (Passo 1.5 - quarta em diante)
                    for alt_i in restantes[1:]:
                        print(f"\n  Avaliando alternativa '{alt_i}':")
                        avaliados = tabela[crit].dropna().sort_values()
                        faixas = " | ".join([f"{alt_name}: {score_val:.2f}" for alt_name, score_val in avaliados.items()])
                        print(f"    Scores atribuídos até agora: {faixas}")
                        print(f"    Defina em qual intervalo '{alt_i}' se enquadra e se está mais próxima da âncora superior ou inferior.")
                        
                        while True:
                            try:
                                score = float(input(f"    Atribua um score para '{alt_i}' (de 0 a 10): "))
                                if 0 <= score <= 10:
                                    tabela.at[alt_i, crit] = score
                                    break
                                print("    O score deve estar entre 0 e 10.")
                            except ValueError:
                                print("    Por favor, digite um número válido.")
                                
        return tabela, dicionario_objetivo

    def exibir_tabela(self, tabela: pd.DataFrame, titulo: str):
        print(f"\n[{titulo}]")
        print("-" * 65)
        print(tabela.round(4).to_string())
        print("-" * 65)

    def informar_dominacoes(self, logs: list):
        for log in logs:
            print(f"> {log}")

    def pedir_swap_simples(self, quase_dominacoes: list, tabela: pd.DataFrame) -> dict:
        print("\n--- PASSO 3: COMPENSAÇÕES - 3.1. EVEN SWAP SIMPLES (QUASE-DOMINAÇÃO) ---")
        print("Verificação: Se a alternativa A é melhor em um objetivo que a alternativa B, e um outro objetivo B é pior que A, e empata em todos os outros objetivos.")
        
        for idx, qd in enumerate(quase_dominacoes):
            alt_a = qd['alt_dominadora']
            alt_b = qd['alt_quase_dominada']
            c_block = qd['atributo_bloqueio']
            c_comps = qd['atributos_compensar']
            
            print(f"{idx + 1} - '{alt_b}' é quase dominada por '{alt_a}'")
            print(f"    Atributo bloqueio (onde '{alt_b}' é melhor): '{c_block}'")
            print(f"    Atributos onde '{alt_a}' é melhor (opções de compensação): {', '.join(c_comps)}")
            
        while True:
            opcao_str = input("\nEscolha uma quase-dominação para resolver (ou Enter para pular): ").strip()
            if not opcao_str:
                return None
            try:
                opcao = int(opcao_str)
                if 1 <= opcao <= len(quase_dominacoes):
                    qd = quase_dominacoes[opcao - 1]
                    break
                print(f"Opção inválida. Digite um número de 1 a {len(quase_dominacoes)}.")
            except ValueError:
                print("Por favor, digite um número válido.")
                
        alt_a = qd['alt_dominadora']
        alt_b = qd['alt_quase_dominada']
        c_block = qd['atributo_bloqueio']
        c_comps = qd['atributos_compensar']
        val_a_block = qd['valor_dominadora_bloqueio']
        val_b_block = qd['valor_quase_dominada_bloqueio']
        
        # Escolha do atributo de compensação
        if len(c_comps) == 1:
            c_comp = c_comps[0]
        else:
            print(f"\nEscolha qual atributo de '{alt_b}' melhorar para compensar a perda no '{c_block}':")
            for idx, c in enumerate(c_comps):
                print(f"{idx + 1} - {c}")
            while True:
                choice_str = input(f"Opção (1 a {len(c_comps)}): ").strip()
                try:
                    choice = int(choice_str)
                    if 1 <= choice <= len(c_comps):
                        c_comp = c_comps[choice - 1]
                        break
                    print(f"Opção inválida. Digite um número de 1 a {len(c_comps)}.")
                except ValueError:
                    print("Por favor, digite um número válido.")
                    
        val_atual_compensar = tabela.at[alt_b, c_comp]
        
        print(f"\n[Compensação para '{alt_b}']")
        print(f"  '{c_block}' será alterado de {val_b_block:.2f} para o valor de '{alt_a}' ({val_a_block:.2f}).")
        print(f"  O valor atual de '{c_comp}' em '{alt_b}' é {val_atual_compensar:.2f}.")
        
        while True:
            try:
                novo_valor = float(input(f"  Qual deve ser o NOVO valor de '{c_comp}' para '{alt_b}'? "))
                break
            except ValueError:
                print("  Por favor, digite um número válido.")
                
        return {
            'alt_quase_dominada': alt_b,
            'atributo_bloqueio': c_block,
            'valor_alvo_bloqueio': val_a_block,
            'atributo_compensar': c_comp,
            'novo_valor_compensar': novo_valor
        }

    def pedir_atributo_eliminar(self, atributos_disponiveis: list) -> str:
        print("\n--- PASSO 3: COMPENSAÇÕES - 3.1. SELEÇÃO DE CRITÉRIOS PARA EVEN SWAP ---")
        print(f"Atributos disponíveis na tabela: {', '.join(atributos_disponiveis)}")
        while True:
            escolha = input("Digite o nome do atributo que deseja fixar e eliminar: ").strip()
            if escolha in atributos_disponiveis:
                return escolha
            print("Atributo inválido. Escolha um nome da lista.")

    def pedir_valor_alvo_fixar(self, atributo: str, valores_existentes: list, melhor_valor: float) -> float:
        valores_str = ", ".join([f"{v:.0f}" for v in sorted(set(valores_existentes))])
        print(f"  Valores existentes para '{atributo}': [{valores_str}]")
        print(f"  O melhor valor atual (sugerido para alvo) é: {melhor_valor:.0f}")
        while True:
            alvo_input = input(f"  Digite o valor alvo para o qual quer igualar '{atributo}' (pressione Enter para usar o sugerido {melhor_valor:.0f}): ").strip()
            if not alvo_input:
                return melhor_valor
            try:
                return float(alvo_input)
            except ValueError:
                print("  Por favor, digite um número válido.")

    def pedir_atributo_compensar(self, atributo_eliminar: str, atributos_disponiveis: list) -> str:
        print(f"Atributos disponíveis para compensação: {', '.join(atributos_disponiveis)}")
        while True:
            escolha = input(f"Digite o nome do atributo que sofrerá a compensação por '{atributo_eliminar}': ").strip()
            if escolha in atributos_disponiveis:
                return escolha
            print("Atributo inválido. Escolha um nome da lista.")

    def pedir_novo_valor_compensacao(self, alternativa: str, atributo_eliminar: str, 
                                    valor_atual: float, valor_alvo: float, 
                                    atributo_compensar: str, valor_atual_compensar: float) -> float:
        print(f"\n  [Passo 3.2: Compensação Subjetiva para '{alternativa}']")
        print(f"    Mudar '{atributo_eliminar}' de {valor_atual:.2f} para o valor fixado {valor_alvo:.2f}.")
        print(f"    O valor atual de '{atributo_compensar}' é {valor_atual_compensar:.2f}.")
        while True:
            try:
                novo_valor = float(input(f"    Qual deve ser o NOVO valor de '{atributo_compensar}' para '{alternativa}'? "))
                return novo_valor
            except ValueError:
                print("    Por favor, digite um número válido.")

    def exibir_resultado_final(self, tabela: pd.DataFrame):
        print("\n" + "=" * 65)
        if len(tabela) == 1:
            print(f"DECISÃO FINAL: A alternativa vencedora é '{tabela.index[0]}'!")
        else:
            print("Processo concluído. Alternativas finalistas restantes:")
            print(tabela.to_string())
        print("=" * 65 + "\n")


# =====================================================================
# FUNÇÃO PRINCIPAL (MAIN)
# =====================================================================

def main():
    try:
        interface_usuario = InterfaceTerminal()
        origem = interface_usuario.escolher_origem_dados()
        
        if origem == 'csv':
            nome_arquivo = interface_usuario.pedir_nome_arquivo_csv()
            df_bruto = pd.read_csv(nome_arquivo, index_col=0)
            
            # Extrai o objetivo dos atributos (linha com índice 'Objetivo')
            linha_objetivo = df_bruto.loc['Objetivo'].str.lower().str.strip()
            dicionario_objetivo = linha_objetivo.to_dict()
            
            # Isola apenas as amostras (remove a linha 'Objetivo' da tabela) e converte para numérico
            tabela_amostras = df_bruto.drop(index='Objetivo').astype(float)
        else:
            tabela_amostras, dicionario_objetivo = interface_usuario.obter_dados_tabela_interativa()
            
        # Executa a lógica isolada
        executar_algoritmo_even_swap(tabela_amostras, dicionario_objetivo, interface_usuario)
        
    except FileNotFoundError:
        print("Erro: Arquivo não encontrado no diretório especificado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()