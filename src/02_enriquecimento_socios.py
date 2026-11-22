"""
ETAPA 2: Enriquecimento do Quadro Societário via API e Geração do Grafo "Cheio"
===============================================================================

Entrada (gerada por src/01_limpeza_dados.py):
  - results/tabela_nos_gephi.csv
  - results/tabela_arestas_gephi.csv

Processamento:
  1. Lê as empresas da tabela de nós gerada por src/01_limpeza_dados.py.
  2. Consulta o Quadro de Sócios e Administradores (QSA) da Receita Federal via
     BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/{cnpj}) para vincular os
     CPFs/CNPJs e nomes reais dos sócios a cada empresa.
  3. Analisa os pares de empresas que possuem aresta 'Concorreu_Contra' na
     tabela de arestas de src/01_limpeza_dados.py, verificando sócios, dados cadastrais
     e sobrenomes em comum.
  4. Substitui os nós 'Sócio_ID_' anônimos pelos Sócios Reais e adiciona as
     arestas 'Vinculo_Suspeito', gerando o Grafo Cheio completo.

Saída:
  - results/grafo_cheio_nos.csv
  - results/grafo_cheio_arestas.csv
  - results/socios_reais.csv
  - results/alertas_vinculos_concorrentes.csv
"""

import json
import os
import re
import socket
import time
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict

import pandas as pd

socket.setdefaulttimeout(30)

# ==========================================
# 0. CONFIGURAÇÕES E CAMINHOS
# ==========================================
PASTA_DESTINO = 'results'
os.makedirs(PASTA_DESTINO, exist_ok=True)

# Entradas vindas diretamente de src/01_limpeza_dados.py
ARQ_NOS_ENTRADA = os.path.join(PASTA_DESTINO, 'tabela_nos_gephi.csv')
ARQ_ARESTAS_ENTRADA = os.path.join(PASTA_DESTINO, 'tabela_arestas_gephi.csv')

# Cache da API e Saídas do Grafo Cheio
ARQ_CACHE = os.path.join(PASTA_DESTINO, 'cache_qsa_brasilapi.json')
ARQ_GRAFO_CHEIO_NOS = os.path.join(PASTA_DESTINO, 'grafo_cheio_nos.csv')
ARQ_GRAFO_CHEIO_ARESTAS = os.path.join(PASTA_DESTINO, 'grafo_cheio_arestas.csv')

URL_API = 'https://brasilapi.com.br/api/cnpj/v1/{}'
INTERVALO_ENTRE_CONSULTAS = 1.0
MAX_TENTATIVAS = 5

PARTICULAS = {'DE', 'DA', 'DO', 'DAS', 'DOS', 'E', 'D', 'DI', 'DEL', 'VAN', 'VON'}
SUFIXOS = {'FILHO', 'FILHA', 'JUNIOR', 'JR', 'NETO', 'NETA', 'SOBRINHO', 'SOBRINHA',
           'SEGUNDO', 'TERCEIRO'}

SOBRENOMES_COMUNS = {
    'SILVA', 'SANTOS', 'OLIVEIRA', 'SOUZA', 'SOUSA', 'RODRIGUES', 'FERREIRA', 'ALVES',
    'PEREIRA', 'LIMA', 'GOMES', 'COSTA', 'RIBEIRO', 'MARTINS', 'CARVALHO', 'ALMEIDA',
    'LOPES', 'SOARES', 'FERNANDES', 'VIEIRA', 'BARBOSA', 'ROCHA', 'DIAS', 'NASCIMENTO',
    'ANDRADE', 'MOREIRA', 'NUNES', 'MARQUES', 'MACHADO', 'MENDES', 'FREITAS', 'CARDOSO',
    'RAMOS', 'GONCALVES', 'SANTANA', 'TEIXEIRA', 'ARAUJO', 'CASTRO', 'MELO', 'PINTO',
    'CAMPOS', 'CUNHA', 'REIS', 'JESUS', 'MOURA', 'CORREIA', 'CORREA', 'BATISTA',
    'FARIA', 'RESENDE', 'REZENDE', 'MIRANDA', 'TAVARES',
}

PESO_SOCIO_EM_COMUM = 10.0
PESO_MESMA_RAIZ_CNPJ = 10.0
PESO_MESMO_ENDERECO = 10.0
PESO_MESMO_TELEFONE = 8.0
PESO_MESMO_EMAIL = 5.0
PESO_SOBRENOME_RARO = 1.0
PESO_SOBRENOME_COMUM = 0.25


# ==========================================
# 1. FUNÇÕES AUXILIARES
# ==========================================
def normalizar_nome(nome):
    if not nome:
        return ''
    nome = unicodedata.normalize('NFKD', str(nome)).encode('ascii', 'ignore').decode('ascii')
    nome = re.sub(r'[^A-Za-z ]', ' ', nome).upper()
    return re.sub(r'\s+', ' ', nome).strip()


def extrair_sobrenomes(nome):
    tokens = [t for t in normalizar_nome(nome).split()
              if t not in PARTICULAS and t not in SUFIXOS and len(t) > 1]
    return set(tokens[1:])


def nome_titular_mei(razao_social):
    return re.sub(r'^[\d\.\s/-]+', '', str(razao_social)).strip()


def limpar_telefone(tel):
    if not tel:
        return ''
    digitos = re.sub(r'\D', '', str(tel))
    if len(digitos) >= 8 and not digitos.startswith('0000'):
        return digitos
    return ''


def normalizar_endereco(info):
    if not isinstance(info, dict):
        return ''
    logr = normalizar_nome(info.get('logradouro') or '')
    num = str(info.get('numero') or '').strip().upper()
    mun = normalizar_nome(info.get('municipio') or '')
    uf = str(info.get('uf') or '').strip().upper()
    if logr and num and logr != 'RUA' and num not in ['S/N', 'SN', '0', '']:
        return f"{logr}, {num} - {mun}/{uf}"
    return ''


def normalizar_email(email):
    if not email:
        return ''
    em = str(email).strip().lower()
    palavras_contabeis = ['contabil', 'contador', 'contabilidade', 'assessoria', 'escritorio']
    if '@' in em and not any(p in em for p in palavras_contabeis):
        return em
    return ''


# ==========================================
# 2. CONSULTA À BRASILAPI (COM CACHE LOCAL)
# ==========================================
def carregar_cache():
    if os.path.exists(ARQ_CACHE):
        with open(ARQ_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def salvar_cache(cache):
    with open(ARQ_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)


def consultar_cnpj(cnpj):
    req = urllib.request.Request(URL_API.format(cnpj),
                                 headers={'User-Agent': 'DeteccaoFraudesLicitacoes/1.0'})
    espera = 2
    for _ in range(MAX_TENTATIVAS):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return {'erro': e.code}
            if e.code == 429 or e.code >= 500:
                time.sleep(espera)
                espera *= 2
                continue
            return None
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(espera)
            espera *= 2
    return None


def obter_qsa(cnpjs):
    cache = carregar_cache()
    pendentes = [c for c in cnpjs if c not in cache]
    print(f"CNPJs únicos recebidos do data_cleaning: {len(cnpjs)} | em cache: {len(cnpjs) - len(pendentes)} | a consultar na API: {len(pendentes)}")

    for i, cnpj in enumerate(pendentes, 1):
        dados = consultar_cnpj(cnpj)
        if dados is not None:
            cache[cnpj] = dados
        else:
            print(f"  [aviso] falha temporária em {cnpj}; será tentado novamente na próxima execução")
        if i % 20 == 0 or i == len(pendentes):
            salvar_cache(cache)
            print(f"  {i}/{len(pendentes)} consultados")
        time.sleep(INTERVALO_ENTRE_CONSULTAS)
    return cache


# ==========================================
# 3. LEITURA DAS PLANILHAS DO DATA CLEANING
# ==========================================
if not os.path.exists(ARQ_NOS_ENTRADA) or not os.path.exists(ARQ_ARESTAS_ENTRADA):
    raise FileNotFoundError(
        "Planilhas de entrada não encontradas! Execute primeiro: python src/01_limpeza_dados.py"
    )

df_nos_base = pd.read_csv(ARQ_NOS_ENTRADA, dtype=str)
df_arestas_base = pd.read_csv(ARQ_ARESTAS_ENTRADA, dtype=str)

# Filtra as empresas presentes na tabela de nós do data_cleaning
df_empresas = df_nos_base[df_nos_base['Classe'] == 'Empresa'].copy()
nome_empresa = df_empresas.set_index('Id')['Label'].to_dict()

documentos = sorted(df_empresas['Id'].unique())
cnpjs = [d for d in documentos if d.isdigit() and len(d) == 14]

# ==========================================
# 4. VINCULAÇÃO DE CPFs E NOMES DOS SÓCIOS VIA API
# ==========================================
cache = obter_qsa(cnpjs)

linhas_socios = []
for doc in documentos:
    razao = nome_empresa.get(doc, '')

    if doc.isdigit() and len(doc) == 11:
        linhas_socios.append({
            'Empresa': doc, 'Razao_Social': razao, 'Nome_Socio': razao,
            'CPF_CNPJ_Socio': doc, 'Qualificacao': 'Pessoa Física Licitante',
            'Tipo_Socio': 'PF', 'Fonte': 'SICOM',
        })
        continue

    dados = cache.get(doc)
    if not dados or 'erro' in dados:
        continue

    razao = dados.get('razao_social') or razao
    qsa = dados.get('qsa') or []

    if qsa:
        for s in qsa:
            tipo = {1: 'PJ', 2: 'PF', 3: 'Estrangeiro'}.get(s.get('identificador_de_socio'), 'PF')
            linhas_socios.append({
                'Empresa': doc, 'Razao_Social': razao,
                'Nome_Socio': s.get('nome_socio', ''),
                'CPF_CNPJ_Socio': s.get('cnpj_cpf_do_socio', '') or '',
                'Qualificacao': s.get('qualificacao_socio', ''),
                'Tipo_Socio': tipo, 'Fonte': 'BrasilAPI (QSA Receita Federal)',
            })
    else:
        natureza = normalizar_nome(dados.get('natureza_juridica', ''))
        if 'INDIVIDUAL' in natureza or re.match(r'^\d', str(razao)):
            linhas_socios.append({
                'Empresa': doc, 'Razao_Social': razao,
                'Nome_Socio': nome_titular_mei(razao), 'CPF_CNPJ_Socio': '',
                'Qualificacao': 'Titular (Empresário Individual/MEI)',
                'Tipo_Socio': 'PF', 'Fonte': 'BrasilAPI (Razão Social)',
            })

df_socios = pd.DataFrame(linhas_socios)
df_socios['Nome_Normalizado'] = df_socios['Nome_Socio'].apply(normalizar_nome)
df_socios['Sobrenomes'] = df_socios.apply(
    lambda r: ' '.join(sorted(extrair_sobrenomes(r['Nome_Socio']))) if r['Tipo_Socio'] != 'PJ' else '',
    axis=1,
)
# Cria o ID único do sócio combinando o nome e os dígitos do CPF/CNPJ retornados pela API
df_socios['Id_Socio'] = df_socios.apply(
    lambda r: 'SOCIO_' + r['Nome_Normalizado'].replace(' ', '_')
              + ('_' + re.sub(r'\D', '', r['CPF_CNPJ_Socio']) if re.sub(r'\D', '', r['CPF_CNPJ_Socio']) else ''),
    axis=1,
)

df_socios.to_csv(os.path.join(PASTA_DESTINO, 'socios_reais.csv'), index=False, encoding='utf-8')

socios_por_empresa = df_socios.groupby('Empresa')['Nome_Normalizado'].apply(set).to_dict()
sobrenomes_por_empresa = defaultdict(set)
for _, r in df_socios[df_socios['Tipo_Socio'] != 'PJ'].iterrows():
    sobrenomes_por_empresa[r['Empresa']] |= extrair_sobrenomes(r['Nome_Socio'])

# Extração de endereços, telefones e e-mails para cruzamento simultâneo
enderecos_por_empresa = {}
telefones_por_empresa = {}
emails_por_empresa = {}

for doc in documentos:
    dados = cache.get(doc)
    if isinstance(dados, dict):
        end = normalizar_endereco(dados)
        if end:
            enderecos_por_empresa[doc] = end
        tel = limpar_telefone(dados.get('ddd_telefone_1')) or limpar_telefone(dados.get('ddd_telefone_2'))
        if tel:
            telefones_por_empresa[doc] = tel
        em = normalizar_email(dados.get('email'))
        if em:
            emails_por_empresa[doc] = em

# ==========================================
# 5. ANÁLISE DE CONCORRENTES A PARTIR DO DATA CLEANING
# ==========================================
df_concorrencia = df_arestas_base[df_arestas_base['Tipo_Relacao'] == 'Concorreu_Contra'].copy()

alertas = []
for _, row in df_concorrencia.iterrows():
    a, b = sorted([str(row['Source']).strip(), str(row['Target']).strip()])
    peso_disputa = float(row['Weight'])

    socios_comuns = (socios_por_empresa.get(a, set()) & socios_por_empresa.get(b, set())) - {''}
    sobrenomes_comuns = sobrenomes_por_empresa.get(a, set()) & sobrenomes_por_empresa.get(b, set())
    mesma_raiz = len(a) == 14 and len(b) == 14 and a[:8] == b[:8]

    # Vínculos Físicos e de Contato
    end_a = enderecos_por_empresa.get(a, '')
    end_b = enderecos_por_empresa.get(b, '')
    mesmo_endereco = bool(end_a and end_b and end_a == end_b)

    tel_a = telefones_por_empresa.get(a, '')
    tel_b = telefones_por_empresa.get(b, '')
    mesmo_telefone = bool(tel_a and tel_b and tel_a == tel_b)

    em_a = emails_por_empresa.get(a, '')
    em_b = emails_por_empresa.get(b, '')
    mesmo_email = bool(em_a and em_b and em_a == em_b)

    score = (
        PESO_SOCIO_EM_COMUM * len(socios_comuns)
        + PESO_MESMA_RAIZ_CNPJ * mesma_raiz
        + PESO_MESMO_ENDERECO * mesmo_endereco
        + PESO_MESMO_TELEFONE * mesmo_telefone
        + PESO_MESMO_EMAIL * mesmo_email
        + sum(PESO_SOBRENOME_COMUM if s in SOBRENOMES_COMUNS else PESO_SOBRENOME_RARO
              for s in sobrenomes_comuns)
    )
    if score == 0:
        continue

    if socios_comuns or mesma_raiz or mesmo_endereco or mesmo_telefone or score >= 2.0:
        nivel = 'ALTO'
    elif score >= 1.0:
        nivel = 'MEDIO'
    else:
        nivel = 'BAIXO'

    motivos = []
    if socios_comuns:
        motivos.append(f"Sócios comuns: {' | '.join(sorted(socios_comuns))}")
    if sobrenomes_comuns:
        motivos.append(f"Sobrenomes comuns: {' '.join(sorted(sobrenomes_comuns))}")
    if mesma_raiz:
        motivos.append("Mesma raiz de CNPJ (Matriz/Filial)")
    if mesmo_endereco:
        motivos.append(f"Mesmo endereço: {end_a}")
    if mesmo_telefone:
        motivos.append(f"Mesmo telefone: {tel_a}")
    if mesmo_email:
        motivos.append(f"Mesmo e-mail: {em_a}")

    alertas.append({
        'Empresa_A': a, 'Nome_A': nome_empresa.get(a, ''),
        'Empresa_B': b, 'Nome_B': nome_empresa.get(b, ''),
        'Peso_Concorrencia': int(peso_disputa),
        'Socios_Em_Comum': ' | '.join(sorted(socios_comuns)),
        'Sobrenomes_Em_Comum': ' '.join(sorted(sobrenomes_comuns)),
        'Mesmo_Endereco': end_a if mesmo_endereco else '',
        'Mesmo_Telefone': tel_a if mesmo_telefone else '',
        'Mesmo_Email': em_a if mesmo_email else '',
        'Mesma_Raiz_CNPJ': mesma_raiz,
        'Motivos_Vinculo': ' ; '.join(motivos),
        'Score': round(score, 2),
        'Nivel': nivel,
    })

df_alertas = pd.DataFrame(alertas)
if not df_alertas.empty:
    df_alertas = df_alertas.sort_values(['Score', 'Peso_Concorrencia'], ascending=False)
df_alertas.to_csv(os.path.join(PASTA_DESTINO, 'alertas_vinculos_concorrentes.csv'),
                  index=False, encoding='utf-8')

# ==========================================
# 6. MONTAGEM DO GRAFO "CHEIO" (COMPLETO)
# ==========================================
# A. Tabela de Nós do Grafo Cheio: Órgãos + Empresas + Sócios Reais (substituindo Sócio_ID_ anônimo)
nos_orgaos_empresas = df_nos_base[df_nos_base['Classe'] != 'Sócio'].copy()
nos_socios_reais = (
    df_socios[['Id_Socio', 'Nome_Socio']]
    .drop_duplicates('Id_Socio')
    .rename(columns={'Id_Socio': 'Id', 'Nome_Socio': 'Label'})
)
nos_socios_reais['Classe'] = 'Sócio Real'

df_grafo_cheio_nos = pd.concat([nos_orgaos_empresas, nos_socios_reais], ignore_index=True)
df_grafo_cheio_nos = df_grafo_cheio_nos.drop_duplicates(subset=['Id'])
df_grafo_cheio_nos.to_csv(ARQ_GRAFO_CHEIO_NOS, index=False, encoding='utf-8')

# B. Tabela de Arestas do Grafo Cheio:
#    Participou_Licitacao + Concorreu_Contra + É_Dono_De (Sócios Reais) + Vinculo_Suspeito
arestas_mercado = df_arestas_base[df_arestas_base['Tipo_Relacao'] != 'É_Dono_De'].copy()

arestas_dono_real = (
    df_socios[['Id_Socio', 'Empresa']]
    .drop_duplicates()
    .rename(columns={'Id_Socio': 'Source', 'Empresa': 'Target'})
)
arestas_dono_real['Tipo_Relacao'] = 'É_Dono_De'
arestas_dono_real['Weight'] = 1.0

arestas_vinculo = pd.DataFrame(columns=['Source', 'Target', 'Tipo_Relacao', 'Weight'])
if not df_alertas.empty:
    arestas_vinculo = (
        df_alertas[df_alertas['Nivel'] != 'BAIXO'][['Empresa_A', 'Empresa_B', 'Score']]
        .rename(columns={'Empresa_A': 'Source', 'Empresa_B': 'Target', 'Score': 'Weight'})
    )
    arestas_vinculo['Tipo_Relacao'] = 'Vinculo_Suspeito'

df_grafo_cheio_arestas = pd.concat(
    [arestas_mercado, arestas_dono_real, arestas_vinculo], ignore_index=True
)[['Source', 'Target', 'Tipo_Relacao', 'Weight']]
df_grafo_cheio_arestas = df_grafo_cheio_arestas.drop_duplicates(
    subset=['Source', 'Target', 'Tipo_Relacao']
)
df_grafo_cheio_arestas.to_csv(ARQ_GRAFO_CHEIO_ARESTAS, index=False, encoding='utf-8')

print("\nEtapa 2 concluída! Grafo 'Cheio' gerado com sucesso:")
print(f"  -> {ARQ_GRAFO_CHEIO_NOS} ({len(df_grafo_cheio_nos)} nós)")
print(f"  -> {ARQ_GRAFO_CHEIO_ARESTAS} ({len(df_grafo_cheio_arestas)} arestas)")
