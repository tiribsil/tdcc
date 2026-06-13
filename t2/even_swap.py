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

    def informar_dominacao(self, alternativa_vencedora: str, alternativa_dominada: str):
        """Notifica o descarte de uma alternativa dominada"""
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

def verificar_dominacao(linha_a, linha_b, dicionario_natureza, tolerance=1e-9):
    """
    Verifica se a linha_a domina a linha_b.
    Retorna True se 'a' for igual ou melhor em TUDO e estritamente melhor em pelo menos UM.
    """
    pelo_menos_um_melhor = False
    
    for atributo, natureza in dicionario_natureza.items():
        valor_a = linha_a[atributo]
        valor_b = linha_b[atributo]
        
        # Ignora diferenças irrelevantes de ponto flutuante
        if abs(valor_a - valor_b) < tolerance:
            continue
            
        if natureza == 'maior':
            if valor_a < valor_b: 
                return False
            if valor_a > valor_b: 
                pelo_menos_um_melhor = True
        elif natureza == 'menor':
            if valor_a > valor_b: 
                return False
            if valor_a < valor_b: 
                pelo_menos_um_melhor = True
            
    return pelo_menos_um_melhor

def remover_alternativas_dominadas(tabela, dicionario_natureza, interface):
    """
    Remove todas as alternativas que são estritamente dominadas por outra.
    """
    alternativas_para_remover = []
    nomes_alternativas = tabela.index.tolist()
    
    for i, nome_a in enumerate(nomes_alternativas):
        if nome_a in alternativas_para_remover: 
            continue
            
        for j, nome_b in enumerate(nomes_alternativas):
            if i == j or nome_b in alternativas_para_remover: 
                continue
                
            linha_a = tabela.loc[nome_a]
            linha_b = tabela.loc[nome_b]
            
            if verificar_dominacao(linha_a, linha_b, dicionario_natureza):
                alternativas_para_remover.append(nome_b)
                interface.informar_dominacao(nome_a, nome_b)
                
    tabela_limpa = tabela.drop(index=alternativas_para_remover)
    return tabela_limpa

def executar_algoritmo_even_swap(tabela, dicionario_natureza, interface):
    """
    Orquestra as etapas de Even Swap guiadas pelo decisor.
    """
    interface.exibir_tabela(tabela, "TABELA INICIAL")
    
    while len(tabela) > 1:
        # Etapa 1: Eliminar dominações
        tabela_antes = len(tabela)
        tabela = remover_alternativas_dominadas(tabela, dicionario_natureza, interface)
        if len(tabela) < tabela_antes:
            interface.exibir_tabela(tabela, "TABELA APÓS ELIMINAÇÃO POR DOMINAÇÃO")
        
        if len(tabela) <= 1:
            break
            
        if len(tabela.columns) <= 1:
            interface.exibir_tabela(tabela, "FIM DO PROCESSO (Apenas 1 critério restante, sem dominância óbvia)")
            break
            
        # Etapa 2: Escolha manual dos atributos para o Swap (Passo 3.1 do PDF)
        atributos_disponiveis = list(tabela.columns)
        atributo_eliminar = interface.pedir_atributo_eliminar(atributos_disponiveis)
        
        valores_existentes = tabela[atributo_eliminar].tolist()
        natureza_eliminar = dicionario_natureza[atributo_eliminar]
        melhor_valor = tabela[atributo_eliminar].max() if natureza_eliminar == 'maior' else tabela[atributo_eliminar].min()
        
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
        del dicionario_natureza[atributo_eliminar]
        
        interface.exibir_tabela(tabela, f"TABELA APÓS SWAP (Eliminado: {atributo_eliminar} | Compensado: {atributo_compensar})")

    interface.exibir_resultado_final(tabela)


# =====================================================================
# INTERFACE EM MODO TERMINAL
# =====================================================================

class InterfaceTerminal(InterfaceBase):
    def escolher_origem_dados(self) -> str:
        print("\n=== MÉTODO EVEN SWAP ===")
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
        print("\n--- MONTAGEM INTERATIVA DA TABELA ---")
        
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
            
        dicionario_natureza = {}
        tipo_criterio = {}
        
        # 3. Natureza e Tipo de cada critério
        for crit in critérios:
            print(f"\nConfigurando critério: '{crit}'")
            while True:
                natureza = input(f"  Qual a natureza de '{crit}'? (maior = quanto maior melhor | menor = quanto menor melhor): ").strip().lower()
                if natureza in ['maior', 'menor']:
                    dicionario_natureza[crit] = natureza
                    break
                print("  Entrada inválida. Digite 'maior' ou 'menor'.")
            
            while True:
                tipo = input(f"  O critério '{crit}' é quantitativo ou qualitativo? (quant | qual): ").strip().lower()
                if tipo in ['quant', 'qual', 'quantitativo', 'qualitativo']:
                    tipo_criterio[crit] = 'quant' if tipo.startswith('quan') else 'qual'
                    break
                print("  Entrada inválida. Digite 'quant' ou 'qual'.")

        # 4. Preenchimento de consequências
        tabela = pd.DataFrame(index=alternativas, columns=critérios, dtype=float)
        
        for crit in critérios:
            print(f"\nPreenchendo valores para o critério: '{crit}' ({dicionario_natureza[crit]} é melhor)")
            
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
                                
        return tabela, dicionario_natureza

    def exibir_tabela(self, tabela: pd.DataFrame, titulo: str):
        print(f"\n[{titulo}]")
        print("-" * 65)
        print(tabela.round(4).to_string())
        print("-" * 65)

    def informar_dominacao(self, alternativa_vencedora: str, alternativa_dominada: str):
        print(f"> A alternativa '{alternativa_dominada}' foi eliminada pois é totalmente dominada por '{alternativa_vencedora}'.")

    def pedir_atributo_eliminar(self, atributos_disponiveis: list) -> str:
        print(f"\nAtributos disponíveis na tabela: {', '.join(atributos_disponiveis)}")
        while True:
            escolha = input("Digite o nome do atributo que deseja fixar e eliminar: ").strip()
            if escolha in atributos_disponiveis:
                return escolha
            print("Atributo inválido. Escolha um nome da lista.")

    def pedir_valor_alvo_fixar(self, atributo: str, valores_existentes: list, melhor_valor: float) -> float:
        valores_str = ", ".join([f"{v:.4g}" for v in sorted(set(valores_existentes))])
        print(f"  Valores existentes para '{atributo}': [{valores_str}]")
        print(f"  O melhor valor atual (sugerido para alvo) é: {melhor_valor:.4g}")
        while True:
            alvo_input = input(f"  Digite o valor alvo para o qual quer igualar '{atributo}' (pressione Enter para usar o sugerido {melhor_valor:.4g}): ").strip()
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
        print(f"\n  [Compensação para '{alternativa}']")
        print(f"    '{atributo_eliminar}' será alterado de {valor_atual:.4g} para o alvo {valor_alvo:.4g}.")
        print(f"    O valor atual de '{atributo_compensar}' é {valor_atual_compensar:.4g}.")
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
            
            # Extrai a natureza dos atributos (linha com índice 'Natureza')
            linha_natureza = df_bruto.loc['Natureza']
            dicionario_natureza = linha_natureza.to_dict()
            
            # Isola apenas as amostras (remove a linha 'Natureza' da tabela) e converte para numérico
            tabela_amostras = df_bruto.drop(index='Natureza').astype(float)
        else:
            tabela_amostras, dicionario_natureza = interface_usuario.obter_dados_tabela_interativa()
            
        # Executa a lógica isolada
        executar_algoritmo_even_swap(tabela_amostras, dicionario_natureza, interface_usuario)
        
    except FileNotFoundError:
        print("Erro: Arquivo não encontrado no diretório especificado.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()