import pandas as pd
import numpy as np

# =====================================================================
# LÓGICA MATEMÁTICA E DO ALGORITMO (INDEPENDENTE DE INTERFACE)
# =====================================================================

def verificar_dominacao(linha_a, linha_b, dicionario_natureza):
    """
    Verifica se a linha_a domina a linha_b.
    Retorna True se 'a' for igual ou melhor em TUDO e estritamente melhor em pelo menos UM.
    """
    pelo_menos_um_melhor = False
    
    for atributo, natureza in dicionario_natureza.items():
        valor_a = linha_a[atributo]
        valor_b = linha_b[atributo]
        
        if natureza == 'maior':
            if valor_a < valor_b: return False
            if valor_a > valor_b: pelo_menos_um_melhor = True
        elif natureza == 'menor':
            if valor_a > valor_b: return False
            if valor_a < valor_b: pelo_menos_um_melhor = True
            
    return pelo_menos_um_melhor

def remover_alternativas_dominadas(tabela, dicionario_natureza, interface):
    alternativas_para_remover = []
    nomes_alternativas = tabela.index.tolist()
    
    for i, nome_a in enumerate(nomes_alternativas):
        if nome_a in alternativas_para_remover: continue
            
        for j, nome_b in enumerate(nomes_alternativas):
            if i == j or nome_b in alternativas_para_remover: continue
                
            linha_a = tabela.loc[nome_a]
            linha_b = tabela.loc[nome_b]
            
            if verificar_dominacao(linha_a, linha_b, dicionario_natureza):
                alternativas_para_remover.append(nome_b)
                interface.informar_dominacao(nome_a, nome_b)
                
    tabela_limpa = tabela.drop(index=alternativas_para_remover)
    return tabela_limpa

def escolher_atributo_eliminar(tabela):
    """
    Heurística: Escolhe o atributo com o menor Coeficiente de Variação (Desvio Padrão / Média).
    Adiciona um epsilon na média para evitar divisão por zero.
    """
    desvio_padrao = tabela.std()
    media = tabela.mean() + 1e-9 
    coeficiente_variacao = abs(desvio_padrao / media)
    atributo_escolhido = coeficiente_variacao.idxmin()
    return atributo_escolhido

def aplicar_troca_equivalente(tabela, dicionario_natureza, atributo_eliminar, atributo_compensar, taxa_equivalencia, unidade_base):
    natureza_eliminar = dicionario_natureza[atributo_eliminar]
    natureza_compensar = dicionario_natureza[atributo_compensar]
    
    # Define qual é o "melhor" valor para forçar o empate
    if natureza_eliminar == 'maior':
        melhor_valor_alvo = tabela[atributo_eliminar].max()
    else:
        melhor_valor_alvo = tabela[atributo_eliminar].min()
        
    for alternativa in tabela.index:
        valor_atual = tabela.at[alternativa, atributo_eliminar]
        
        # Calcula quanto a alternativa foi "melhorada" virtualmente
        if natureza_eliminar == 'maior':
            melhoria = melhor_valor_alvo - valor_atual
        else:
            melhoria = valor_atual - melhor_valor_alvo
            
        # Punição correspondente no atributo B
        punicao = (melhoria / unidade_base) * taxa_equivalencia
        
        # Aplica a punição piorando o valor de B
        valor_atual_compensar = tabela.at[alternativa, atributo_compensar]
        if natureza_compensar == 'maior':
            novo_valor = valor_atual_compensar - punicao # Diminui porque maior é melhor
        else:
            novo_valor = valor_atual_compensar + punicao # Aumenta porque menor é melhor
            
        tabela.at[alternativa, atributo_compensar] = novo_valor
        
    # Iguala a coluna do atributo eliminado para o alvo
    tabela[atributo_eliminar] = melhor_valor_alvo
    return tabela

def executar_algoritmo_even_swap(tabela, dicionario_natureza, interface):
    """
    Método principal altamente abstrato. Orquestra as etapas do algoritmo.
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
            
        # Etapa 2: Escolher heurística e pedir dados
        atributo_eliminar = escolher_atributo_eliminar(tabela)
        atributos_restantes = [col for col in tabela.columns if col != atributo_eliminar]
        
        if not atributos_restantes:
            break # Fim de linha, não há como compensar

        valores_unicos = sorted(tabela[atributo_eliminar].unique())
        if len(valores_unicos) > 1:
            # Pega a menor diferença entre as opções reais
            unidade_base = float(min(np.diff(valores_unicos)))
        else:
            unidade_base = 1.0
            
        atributo_compensar = interface.pedir_atributo_compensar(atributo_eliminar, atributos_restantes)
        taxa_equivalencia = interface.pedir_taxa_equivalencia(atributo_eliminar, atributo_compensar, unidade_base)
        
        # Etapa 3: Aplicar matemática do Swap
        tabela = aplicar_troca_equivalente(tabela, dicionario_natureza, atributo_eliminar, atributo_compensar, taxa_equivalencia, unidade_base)
        
        # Etapa 4: Eliminar coluna neutralizada
        tabela = tabela.drop(columns=[atributo_eliminar])
        del dicionario_natureza[atributo_eliminar]
        
        interface.exibir_tabela(tabela, f"TABELA APÓS SWAP (Eliminado: {atributo_eliminar} | Compensado: {atributo_compensar})")

    interface.exibir_resultado_final(tabela)


# =====================================================================
# CAMADA DE INTERFACE (MÓDULO DE ENTRADA/SAÍDA ABSTRATO)
# =====================================================================

class InterfaceTerminal:
    """
    Implementação da interface via Terminal. 
    Para o Web App, basta criar uma 'InterfaceWeb' com os mesmos métodos e injetar na função principal.
    """
    def exibir_tabela(self, tabela, titulo):
        print(f"\n[{titulo}]")
        print("-" * 50)
        print(tabela.round(2).to_string())
        print("-" * 50)

    def informar_dominacao(self, alternativa_vencedora, alternativa_dominada):
        print(f"> A alternativa '{alternativa_dominada}' foi eliminada pois é totalmente dominada por '{alternativa_vencedora}'.")

    def pedir_atributo_compensar(self, atributo_eliminar, atributos_disponiveis):
        print(f"\nAnálise: O atributo com menor variação é '{atributo_eliminar}'. Ele será igualado para a melhor alternativa.")
        print(f"Atributos disponíveis para compensação: {', '.join(atributos_disponiveis)}")
        
        while True:
            escolha = input("Digite o nome do atributo que sofrerá a compensação: ").strip()
            if escolha in atributos_disponiveis:
                return escolha
            print("Atributo inválido. Digite exatamente o nome como aparece na lista.")

    def pedir_taxa_equivalencia(self, atributo_eliminar, atributo_compensar, unidade_base):
        while True:
            try:
                print(f"\nPergunta de Equivalência:")
                texto_pergunta = f"{unidade_base:g} unidade(s) de '{atributo_eliminar}' equivale(m) a quantas unidades de '{atributo_compensar}'? (Digite um número): "
                valor = float(input(texto_pergunta))
                return valor
            except ValueError:
                print("Por favor, digite um número válido (use '.' para decimais).")

    def exibir_resultado_final(self, tabela):
        print("\n" + "=" * 50)
        if len(tabela) == 1:
            print(f"DECISÃO FINAL: A alternativa vencedora é '{tabela.index[0]}'!")
        else:
            print("Não há mais critérios para avaliar.")
        print("=" * 50 + "\n")


# =====================================================================
# FUNÇÃO PRINCIPAL (MAIN)
# =====================================================================

def main():
    try:
        # Lê o CSV. Supõe que a primeira coluna tem os nomes das alternativas
        df_bruto = pd.read_csv("entrada.csv", index_col=0)
        
        # Extrai a natureza dos atributos (linha com índice 'Natureza')
        linha_natureza = df_bruto.loc['Natureza']
        dicionario_natureza = linha_natureza.to_dict()
        
        # Isola apenas as amostras (remove a linha 'Natureza' da tabela) e converte para numérico
        tabela_amostras = df_bruto.drop(index='Natureza').astype(float)
        
        # Instancia a interface que queremos usar (Terminal, neste caso)
        interface_usuario = InterfaceTerminal()
        
        # Executa a lógica isolada
        executar_algoritmo_even_swap(tabela_amostras, dicionario_natureza, interface_usuario)
        
    except FileNotFoundError:
        print("Erro: Arquivo 'entrada.csv' não encontrado no diretório atual.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()