import pandas as pd
import numpy as np
import re
import os

# ==========================================
# 1. FUNÇÕES DE LIMPEZA E FORMATAÇÃO
# ==========================================

def limpar_documento(doc):
    """
    Remove notação científica (ex: 2.71E+13), pontos, traços e espaços de CNPJs/CPFs.
    Se o arquivo CSV original já foi salvo com o 'E+13' pelo Excel, tentamos converter.
    """
    if pd.isna(doc):
        return "DESCONHECIDO"
    
    doc_str = str(doc).strip().replace('.', '').replace('-', '').replace('/', '')
    
    # Verifica se a string contém notação científica literal
    if 'E+' in doc_str.upper():
        try:
            # Converte de notação científica para inteiro longo, depois volta para string
            doc_str = str(int(float(doc_str.replace(',', '.'))))
        except ValueError:
            pass

    # Recupera zeros à esquerda perdidos na exportação numérica (CNPJ = 14 dígitos, CPF = 11 dígitos)
    if doc_str.isdigit():
        if 9 <= len(doc_str) < 11:
            doc_str = doc_str.zfill(11)
        elif 12 <= len(doc_str) < 14:
            doc_str = doc_str.zfill(14)
            
    return doc_str

# ==========================================
# 2. CARREGAMENTO DAS BASES DE DADOS
# ==========================================
# Forçamos a leitura como string (dtype=str) para proteger IDs numéricos e CNPJs
df_licitacao = pd.read_csv('data/raw/2025.3122306.licitacao.licitacao.csv', sep=';', dtype=str)
df_hab = pd.read_csv('data/raw/2025.3122306.licitacao.habLicitacao.csv', sep=';', dtype=str)
df_socios = pd.read_csv('data/raw/2025.3122306.licitacao.quadroSocLicitacao.csv', sep=';', dtype=str)
df_julgamento = pd.read_csv('data/raw/2025.3122306.licitacao.julgLicitacao.csv', sep=';', dtype=str)

# Aplicando a higienização nos documentos (agora usando os nomes REAIS das colunas)
df_hab['num_documento'] = df_hab['num_documento'].apply(limpar_documento)
df_socios['num_documento'] = df_socios['num_documento'].apply(limpar_documento) 
df_julgamento['num_doc_licitante'] = df_julgamento['num_doc_licitante'].apply(limpar_documento) # Nome real da coluna

# ==========================================
# 3. CONSTRUÇÃO DA TABELA DE NÓS (VÉRTICES)
# ==========================================
nos_orgaos = df_licitacao[['cod_orgao']].drop_duplicates().rename(columns={'cod_orgao': 'ID'})
nos_orgaos['Label'] = 'Orgao_' + nos_orgaos['ID'].astype(str)
nos_orgaos['Classe'] = 'Órgão'

# Empresas vêm da Habilitação e do Julgamento (garante que nenhum licitante fique sem nó)
empresas_hab = df_hab[['num_documento', 'nom_pessoa']].rename(columns={'num_documento': 'ID', 'nom_pessoa': 'Label'})
empresas_julg = df_julgamento[['num_doc_licitante', 'nom_licitante']].rename(columns={'num_doc_licitante': 'ID', 'nom_licitante': 'Label'})
nos_empresas = pd.concat([empresas_hab, empresas_julg], ignore_index=True).dropna(subset=['ID']).drop_duplicates(subset=['ID']).copy()
nos_empresas['Classe'] = 'Empresa'

# Como a base pública oculta o CPF do sócio, usaremos o ID sequencial como representante do Sócio
nos_socios = df_socios[['seq_quadro_soc']].drop_duplicates().rename(columns={'seq_quadro_soc': 'ID'})
nos_socios['Label'] = 'Sócio_ID_' + nos_socios['ID'].astype(str)
nos_socios['Classe'] = 'Sócio'

# Concatena todos os vértices em um único DataFrame de nós
tabela_nos = pd.concat([nos_orgaos, nos_empresas, nos_socios], ignore_index=True)
tabela_nos = tabela_nos.drop_duplicates(subset=['ID']).dropna(subset=['ID'])

# ==========================================
# 4. CONSTRUÇÃO DA TABELA DE ARESTAS
# ==========================================
arestas = []

# A. Grafo Bipartido: Empresa -> Participou -> Órgão
df_part = df_hab[['num_documento', 'cod_orgao']].dropna()
for _, row in df_part.iterrows():
    arestas.append({
        'Source': row['num_documento'],
        'Target': row['cod_orgao'],
        'Tipo_Relacao': 'Participou_Licitacao',
        'Weight': 1
    })

# B. Projeção Monopartida: Empresa -> Concorreu_Contra -> Empresa 
# 1) Empresas habilitadas/participantes na mesma licitação (seq_licitacao)
df_part_lic = pd.concat([
    df_hab[['seq_licitacao', 'num_documento']].rename(columns={'num_documento': 'doc'}),
    df_julgamento[['seq_licitacao', 'num_doc_licitante']].rename(columns={'num_doc_licitante': 'doc'})
], ignore_index=True).dropna(subset=['seq_licitacao', 'doc']).drop_duplicates()

for _, empresas_lic in df_part_lic.groupby('seq_licitacao')['doc']:
    lista_emp = sorted(empresas_lic.unique())
    for i in range(len(lista_emp)):
        for j in range(i + 1, len(lista_emp)):
            arestas.append({
                'Source': lista_emp[i],
                'Target': lista_emp[j],
                'Tipo_Relacao': 'Concorreu_Contra',
                'Weight': 1
            })

# 2) Agrupamos também as empresas que disputaram o mesmo item no julgamento (soma peso por item disputado)
df_julgamento_valido = df_julgamento.dropna(subset=['num_doc_licitante', 'seq_item_licitacao'])
itens_disputados = df_julgamento_valido.groupby('seq_item_licitacao')['num_doc_licitante'].apply(list)

for item, empresas in itens_disputados.items():
    if len(empresas) > 1:
        # Cria aresta para todos os pares de empresas que disputaram este item
        for i in range(len(empresas)):
            for j in range(i + 1, len(empresas)):
                if empresas[i] == empresas[j]:
                    continue
                # Ordenar para evitar duplicidade direcional (A->B ser diferente de B->A)
                emp1, emp2 = sorted([empresas[i], empresas[j]])
                arestas.append({
                    'Source': emp1,
                    'Target': emp2,
                    'Tipo_Relacao': 'Concorreu_Contra',
                    'Weight': 1 
                })

# C. Grafo Societário (Multicamada): Sócio -> É_Dono_De -> Empresa
# Ligamos o ID sequencial da tabela de sócios ao CNPJ da Empresa
df_soc = df_socios[['seq_quadro_soc', 'num_documento']].dropna()
for _, row in df_soc.iterrows():
    arestas.append({
        'Source': row['seq_quadro_soc'],
        'Target': row['num_documento'],
        'Tipo_Relacao': 'É_Dono_De',
        'Weight': 1
    })

tabela_arestas_bruta = pd.DataFrame(arestas)

# Agrupa arestas repetidas para somar o Peso (Weight)
tabela_arestas = tabela_arestas_bruta.groupby(['Source', 'Target', 'Tipo_Relacao'], as_index=False).agg({'Weight': 'sum'})

# ==========================================
# 5. EXPORTAÇÃO PARA O GEPHI
# ==========================================
# O Gephi exige especificamente que as colunas se chamem "Id", "Label" para nós, 
# e "Source", "Target", "Weight" para arestas.
tabela_nos = tabela_nos.rename(columns={'ID': 'Id'})

# Define pasta de destino e garante que ela exista
pasta_destino = 'results'
os.makedirs(pasta_destino, exist_ok=True)

caminho_nos = os.path.join(pasta_destino, 'tabela_nos_gephi.csv')
caminho_arestas = os.path.join(pasta_destino, 'tabela_arestas_gephi.csv')

tabela_nos.to_csv(caminho_nos, index=False, encoding='utf-8')
tabela_arestas.to_csv(caminho_arestas, index=False, encoding='utf-8')

print(f"Processamento concluído! Arquivos gerados com sucesso na pasta '{pasta_destino}': tabela_nos_gephi.csv e tabela_arestas_gephi.csv")