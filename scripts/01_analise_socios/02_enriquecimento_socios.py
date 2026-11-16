"""
ETAPA 2: Enriquecimento do Quadro Societário via API e Geração do Grafo "Cheio"
===============================================================================

Entrada (gerada pelo 01_limpeza_dados.py):
  - database/2025/processed/tabela_nos_gephi.csv
  - database/2025/processed/tabela_arestas_gephi.csv

Processamento:
  1. Lê as empresas da tabela de nós gerada pelo 01_limpeza_dados.py.
  2. Consulta o Quadro de Sócios e Administradores (QSA) da Receita Federal via
     BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/{cnpj}) para vincular os
     CPFs/CNPJs e nomes reais dos sócios a cada empresa.
  3. Analisa os pares de empresas que possuem aresta 'Concorreu_Contra' na
     tabela de arestas do 01_limpeza_dados.py, verificando sócios, endereços,
     telefones, e-mails, raiz de CNPJ e sobrenomes em comum.
  4. Substitui os nós 'Sócio_ID_' anônimos pelos Sócios Reais e adiciona as
     arestas 'Vinculo_Suspeito', gerando o Grafo Cheio completo em CSV e GEXF
     (nativo do Gephi, com atributos sanitizados e cores viz).

Saída:
  - outputs/01_analise_socios/grafo_cheio_nos.csv
  - outputs/01_analise_socios/grafo_cheio_arestas.csv
  - outputs/01_analise_socios/grafo_cheio.gexf
  - outputs/01_analise_socios/socios_reais.csv
  - outputs/01_analise_socios/alertas_vinculos_concorrentes.csv
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

import networkx as nx
import sys
import pandas as pd

socket.setdefaulttimeout(30)

# ==========================================
# 0. CONFIGURAÇÕES E CAMINHOS
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_ENTRADA = os.path.join(BASE_DIR, 'database', '2025', 'processed')
PASTA_PROC_SOCIOS = os.path.join(PASTA_ENTRADA, '01_analise_socios')
PASTA_DESTINO = os.path.join(BASE_DIR, 'outputs', '01_analise_socios')
os.makedirs(PASTA_PROC_SOCIOS, exist_ok=True)
os.makedirs(PASTA_DESTINO, exist_ok=True)

# Entradas vindas diretamente do 01_limpeza_dados.py
ARQ_NOS_ENTRADA = os.path.join(PASTA_ENTRADA, 'tabela_nos_gephi.csv')
ARQ_ARESTAS_ENTRADA = os.path.join(PASTA_ENTRADA, 'tabela_arestas_gephi.csv')

# Cache da API e Saídas do Grafo Cheio
ARQ_CACHE = os.path.join(PASTA_DESTINO, 'cache_qsa_brasilapi.json')
ARQ_GRAFO_CHEIO_NOS = os.path.join(PASTA_DESTINO, 'grafo_cheio_nos.csv')
ARQ_GRAFO_CHEIO_ARESTAS = os.path.join(PASTA_DESTINO, 'grafo_cheio_arestas.csv')
ARQ_GRAFO_CHEIO_GEXF = os.path.join(PASTA_DESTINO, 'grafo_cheio.gexf')

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


def sanitizar_texto(valor, padrao=''):
    """Garante string limpa sem None/NaN nem caracteres de controle inválidos em XML/GEXF."""
    if valor is None or pd.isna(valor):
        return padrao
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', str(valor))
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto if texto else padrao


def formatar_documento(doc):
    """Formata CNPJ (14 dígitos) ou CPF (11 dígitos) para leitura humana."""
    digitos = re.sub(r'\D', '', sanitizar_texto(doc))
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return sanitizar_texto(doc)


def montar_descricao_empresa(doc, dados):
    """Monta descrição detalhada de nó Empresa/PF a partir do cache da Receita Federal."""
    if doc.isdigit() and len(doc) == 11:
        return f"Pessoa Física Licitante | CPF: {formatar_documento(doc)}"
    cnpj_fmt = formatar_documento(doc)
    if not isinstance(dados, dict) or 'erro' in dados:
        return f"Empresa Licitante | CNPJ: {cnpj_fmt} | Dados cadastrais indisponíveis na cache"

    partes = [f"Empresa | CNPJ: {cnpj_fmt}"]
    fantasia = sanitizar_texto(dados.get('nome_fantasia'))
    if fantasia:
        partes.append(f"Fantasia: {fantasia}")
    mun = sanitizar_texto(dados.get('municipio'))
    uf = sanitizar_texto(dados.get('uf'))
    if mun and uf:
        partes.append(f"Município: {mun}/{uf}")
    porte = sanitizar_texto(dados.get('porte'))
    if porte:
        partes.append(f"Porte: {porte}")
    situacao = sanitizar_texto(dados.get('descricao_situacao_cadastral'))
    if situacao:
        partes.append(f"Situação: {situacao}")
    abertura = sanitizar_texto(dados.get('data_inicio_atividade'))
    if abertura:
        partes.append(f"Abertura: {abertura}")
    cnae = sanitizar_texto(dados.get('cnae_fiscal_descricao'))
    if cnae:
        partes.append(f"CNAE: {cnae}")
    return ' | '.join(partes)


# ==========================================
# 2. CONSULTA À BRASILAPI (COM CACHE LOCAL)
# ==========================================
ARQ_CACHE_FALLBACK = os.path.join(PASTA_ENTRADA, 'cache_qsa_brasilapi.json')

def carregar_cache():
    for caminho in (ARQ_CACHE, ARQ_CACHE_FALLBACK):
        if os.path.exists(caminho):
            with open(caminho, 'r', encoding='utf-8') as f:
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
    offline = ('--offline' in sys.argv) or (os.environ.get('AEDS_OFFLINE') == '1')
    print(f"CNPJs únicos recebidos do 01_limpeza_dados: {len(cnpjs)} | em cache: {len(cnpjs) - len(pendentes)} | pendentes: {len(pendentes)}")
    if offline:
        if pendentes:
            print(f"  [modo offline] Pulando {len(pendentes)} consultas externas à BrasilAPI.")
        return cache

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
        "Planilhas de entrada não encontradas! Execute primeiro: python scripts/01_limpeza_dados.py"
    )

df_nos_base = pd.read_csv(ARQ_NOS_ENTRADA, dtype=str)
df_arestas_base = pd.read_csv(ARQ_ARESTAS_ENTRADA, dtype=str)

# Filtra as empresas presentes na tabela de nós do 01_limpeza_dados
df_empresas = df_nos_base[df_nos_base['Classe'] == 'Empresa'].copy()
nome_empresa = df_empresas.set_index('Id')['Label'].to_dict()

documentos = sorted(df_empresas['Id'].unique())
cnpjs = [d for d in documentos if d.isdigit() and len(d) == 14]
docs_cpfs = [d for d in documentos if d.isdigit() and len(d) == 11]
docs_mascarados = [d for d in documentos if not d.isdigit()]

arestas_masc_df = df_arestas_base[
    df_arestas_base['Source'].isin(docs_mascarados) | df_arestas_base['Target'].isin(docs_mascarados)
] if docs_mascarados else df_arestas_base.iloc[0:0]
print(
    f"Documentos empresa: {len(documentos)} | CNPJs válidos={len(cnpjs)} | "
    f"CPFs válidos={len(docs_cpfs)} | Mascarados/excluídos={len(docs_mascarados)} "
    f"(arestas envolvidas={len(arestas_masc_df)}, Concorreu_Contra="
    f"{int((arestas_masc_df['Tipo_Relacao'] == 'Concorreu_Contra').sum())})"
)

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

cnpjs_set = set(cnpjs)
cnpjs_com_qsa = sum(1 for c in cnpjs if isinstance(cache.get(c), dict) and bool(cache[c].get('qsa')))
cnpjs_cobertos_total = len(set(df_socios['Empresa'].unique()) & cnpjs_set) if not df_socios.empty else 0
cnpjs_mei_ei = max(0, cnpjs_cobertos_total - cnpjs_com_qsa)
cnpjs_vazios = len(cnpjs) - cnpjs_cobertos_total
cobertura_pct = (100.0 * cnpjs_cobertos_total / len(cnpjs)) if cnpjs else 0.0
print(
    f"Cobertura QSA ({len(cnpjs)} CNPJs válidos): {cnpjs_cobertos_total}/{len(cnpjs)} "
    f"({cobertura_pct:.2f}%) [QSA={cnpjs_com_qsa} | MEI/EI={cnpjs_mei_ei} | Vazios/Erro={cnpjs_vazios}]"
)

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
    qtd_certames = int(pd.to_numeric(row.get('Qtd_Certames_Comuns', 0), errors='coerce') or 0)
    qtd_itens = int(pd.to_numeric(row.get('Qtd_Itens_Comuns', 0), errors='coerce') or 0)
    segmento_obj = sanitizar_texto(row.get('Segmento_Objeto', ''))

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
        'Qtd_Certames_Comuns': qtd_certames,
        'Qtd_Itens_Comuns': qtd_itens,
        'Segmento_Objeto': segmento_obj,
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
df_alertas.to_csv(os.path.join(PASTA_PROC_SOCIOS, 'alertas_vinculos_concorrentes.csv'),
                  index=False, encoding='utf-8')

# ==========================================
# 6. MONTAGEM DO GRAFO "CHEIO" (COMPLETO: CSV + GEXF)
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
df_grafo_cheio_nos['Id'] = df_grafo_cheio_nos['Id'].apply(sanitizar_texto)
df_grafo_cheio_nos['Label'] = df_grafo_cheio_nos.apply(
    lambda r: sanitizar_texto(r['Label'], padrao=r['Id']), axis=1
)
df_grafo_cheio_nos['Classe'] = df_grafo_cheio_nos['Classe'].apply(sanitizar_texto)
df_grafo_cheio_nos = df_grafo_cheio_nos.drop_duplicates(subset=['Id'])

# Metadados auxiliares para descrições ricas de Sócios Reais
desc_socios_map = {}
qual_socio_empresa = {}
if not df_socios.empty:
    for id_soc, grp in df_socios.groupby('Id_Socio'):
        tipos = sorted({sanitizar_texto(t) for t in grp['Tipo_Socio'] if sanitizar_texto(t)})
        docs = sorted({sanitizar_texto(d) for d in grp['CPF_CNPJ_Socio'] if sanitizar_texto(d)})
        quals = sorted({sanitizar_texto(q) for q in grp['Qualificacao'] if sanitizar_texto(q)})
        empresas = list(dict.fromkeys(
            sanitizar_texto(rz) for rz in grp['Razao_Social'] if sanitizar_texto(rz)
        ))
        resumo_emp = ', '.join(empresas[:3])
        if len(empresas) > 3:
            resumo_emp += f" (+{len(empresas) - 3})"
        partes = [f"Sócio Real ({'/'.join(tipos) or 'PF'})"]
        if docs:
            partes.append(f"Doc: {', '.join(docs)}")
        if quals:
            partes.append(f"Qualificação: {' / '.join(quals)}")
        if empresas:
            partes.append(f"Empresas ({len(empresas)}): {resumo_emp}")
        desc_socios_map[sanitizar_texto(id_soc)] = ' | '.join(partes)

    for _, r in df_socios.iterrows():
        chave_se = (sanitizar_texto(r['Id_Socio']), sanitizar_texto(r['Empresa']))
        qual = sanitizar_texto(r['Qualificacao'])
        if qual:
            qual_socio_empresa.setdefault(chave_se, [])
            if qual not in qual_socio_empresa[chave_se]:
                qual_socio_empresa[chave_se].append(qual)


def _montar_desc_no(row):
    id_no = row['Id']
    classe = row['Classe']
    if classe == 'Órgão':
        return f"Órgão Público Municipal | Código SICOM: {id_no}"
    if classe == 'Empresa':
        return montar_descricao_empresa(id_no, cache.get(id_no))
    if classe == 'Sócio Real':
        return desc_socios_map.get(id_no, f"Sócio Real | {row['Label']}")
    return f"{classe} | {row['Label']}"


df_grafo_cheio_nos['Descricao'] = df_grafo_cheio_nos.apply(_montar_desc_no, axis=1).apply(sanitizar_texto)
df_grafo_cheio_nos = df_grafo_cheio_nos[['Id', 'Label', 'Classe', 'Descricao']]
df_grafo_cheio_nos.to_csv(ARQ_GRAFO_CHEIO_NOS, index=False, encoding='utf-8')

mapa_label_no = df_grafo_cheio_nos.set_index('Id')['Label'].to_dict()
mapa_classe_no = df_grafo_cheio_nos.set_index('Id')['Classe'].to_dict()

# B. Tabela de Arestas do Grafo Cheio:
#    Participou_Licitacao + Concorreu_Contra + É_Dono_De (Sócios Reais) + Vinculo_Suspeito
arestas_mercado = df_arestas_base[df_arestas_base['Tipo_Relacao'] != 'É_Dono_De'].copy()
if 'Qtd_Certames_Comuns' not in arestas_mercado.columns:
    arestas_mercado['Qtd_Certames_Comuns'] = 0
if 'Qtd_Itens_Comuns' not in arestas_mercado.columns:
    arestas_mercado['Qtd_Itens_Comuns'] = 0
if 'Segmento_Objeto' not in arestas_mercado.columns:
    arestas_mercado['Segmento_Objeto'] = ''
arestas_mercado['Nivel_Risco'] = ''
arestas_mercado['Motivos_Vinculo'] = ''
arestas_mercado['Peso_Concorrencia'] = 0

arestas_dono_real = (
    df_socios[['Id_Socio', 'Empresa']]
    .drop_duplicates()
    .rename(columns={'Id_Socio': 'Source', 'Empresa': 'Target'})
)
arestas_dono_real['Tipo_Relacao'] = 'É_Dono_De'
arestas_dono_real['Weight'] = 1.0
arestas_dono_real['Qtd_Certames_Comuns'] = 0
arestas_dono_real['Qtd_Itens_Comuns'] = 0
arestas_dono_real['Segmento_Objeto'] = ''
arestas_dono_real['Nivel_Risco'] = ''
arestas_dono_real['Motivos_Vinculo'] = ''
arestas_dono_real['Peso_Concorrencia'] = 0

arestas_vinculo = pd.DataFrame(
    columns=[
        'Source', 'Target', 'Tipo_Relacao', 'Weight',
        'Qtd_Certames_Comuns', 'Qtd_Itens_Comuns', 'Segmento_Objeto',
        'Nivel_Risco', 'Motivos_Vinculo', 'Peso_Concorrencia',
    ]
)
if not df_alertas.empty:
    arestas_vinculo = (
        df_alertas[df_alertas['Nivel'] != 'BAIXO'][
            [
                'Empresa_A', 'Empresa_B', 'Score',
                'Qtd_Certames_Comuns', 'Qtd_Itens_Comuns', 'Segmento_Objeto',
                'Nivel', 'Motivos_Vinculo', 'Peso_Concorrencia',
            ]
        ]
        .rename(columns={
            'Empresa_A': 'Source',
            'Empresa_B': 'Target',
            'Score': 'Weight',
            'Nivel': 'Nivel_Risco',
        })
    )
    arestas_vinculo['Tipo_Relacao'] = 'Vinculo_Suspeito'

df_grafo_cheio_arestas = pd.concat(
    [arestas_mercado, arestas_dono_real, arestas_vinculo], ignore_index=True
)
df_grafo_cheio_arestas['Source'] = df_grafo_cheio_arestas['Source'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Target'] = df_grafo_cheio_arestas['Target'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Tipo_Relacao'] = df_grafo_cheio_arestas['Tipo_Relacao'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Weight'] = pd.to_numeric(df_grafo_cheio_arestas['Weight'], errors='coerce').fillna(1.0).astype(float)
df_grafo_cheio_arestas['Qtd_Certames_Comuns'] = pd.to_numeric(
    df_grafo_cheio_arestas['Qtd_Certames_Comuns'], errors='coerce'
).fillna(0).astype(int)
df_grafo_cheio_arestas['Qtd_Itens_Comuns'] = pd.to_numeric(
    df_grafo_cheio_arestas['Qtd_Itens_Comuns'], errors='coerce'
).fillna(0).astype(int)
df_grafo_cheio_arestas['Segmento_Objeto'] = df_grafo_cheio_arestas['Segmento_Objeto'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Nivel_Risco'] = df_grafo_cheio_arestas['Nivel_Risco'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Motivos_Vinculo'] = df_grafo_cheio_arestas['Motivos_Vinculo'].apply(sanitizar_texto)
df_grafo_cheio_arestas['Peso_Concorrencia'] = pd.to_numeric(
    df_grafo_cheio_arestas['Peso_Concorrencia'], errors='coerce'
).fillna(0).astype(int)

df_grafo_cheio_arestas = df_grafo_cheio_arestas.drop_duplicates(
    subset=['Source', 'Target', 'Tipo_Relacao']
).copy()


def _formatar_aresta(row):
    src = row['Source']
    tgt = row['Target']
    tipo = row['Tipo_Relacao']
    peso = float(row['Weight'])
    nome_src = mapa_label_no.get(src, src)
    nome_tgt = mapa_label_no.get(tgt, tgt)
    nivel = row['Nivel_Risco']
    motivos = row['Motivos_Vinculo']
    peso_conc = int(row['Peso_Concorrencia'])

    if tipo == 'Participou_Licitacao':
        qtd = int(round(peso))
        lbl = f"Participou ({qtd}x)"
        desc = f"{nome_src} participou de {qtd} habilitação(ões) no órgão {nome_tgt}"
    elif tipo == 'Concorreu_Contra':
        qtd = int(round(peso))
        lbl = f"Concorreu ({qtd}x)"
        desc = f"{nome_src} e {nome_tgt} concorreram juntos ({qtd} registro(s) de disputa)"
    elif tipo == 'É_Dono_De':
        quals = ' / '.join(qual_socio_empresa.get((src, tgt), []))
        lbl = "É Dono De"
        desc = (
            f"{nome_src} integra o QSA de {nome_tgt} ({quals})"
            if quals else f"{nome_src} integra o QSA de {nome_tgt}"
        )
    elif tipo == 'Vinculo_Suspeito':
        lbl = f"Vínculo {nivel or 'SUSPEITO'} (Score {peso:.2f})"
        desc = (
            f"Vínculo suspeito [{nivel}] entre {nome_src} e {nome_tgt} | "
            f"Score: {peso:.2f} | Concorrências: {peso_conc} | Motivos: {motivos}"
        )
    else:
        lbl = tipo
        desc = f"{nome_src} -> {nome_tgt} ({tipo}, peso {peso:.2f})"
    return pd.Series([sanitizar_texto(lbl), sanitizar_texto(desc)])


df_grafo_cheio_arestas[['Label', 'Descricao']] = df_grafo_cheio_arestas.apply(_formatar_aresta, axis=1)
df_grafo_cheio_arestas = df_grafo_cheio_arestas[
    [
        'Source', 'Target', 'Tipo_Relacao', 'Weight', 'Label', 'Descricao',
        'Nivel_Risco', 'Motivos_Vinculo',
        'Qtd_Certames_Comuns', 'Qtd_Itens_Comuns', 'Segmento_Objeto',
    ]
]
df_grafo_cheio_arestas.to_csv(ARQ_GRAFO_CHEIO_ARESTAS, index=False, encoding='utf-8')

# C. Exportação GEXF nativo do Gephi (MultiGraph preserva arestas paralelas Concorreu_Contra + Vinculo_Suspeito)
CORES_NO = {
    'Órgão': {'r': 44, 'g': 160, 'b': 44, 'a': 1.0},       # Verde
    'Empresa': {'r': 31, 'g': 119, 'b': 180, 'a': 1.0},    # Azul
    'Sócio Real': {'r': 255, 'g': 127, 'b': 14, 'a': 1.0}, # Laranja
}
TAMANHOS_NO = {
    'Órgão': 25.0,
    'Empresa': 15.0,
    'Sócio Real': 11.0,
}
CORES_ARESTA = {
    'Vinculo_Suspeito_ALTO': {'r': 214, 'g': 39, 'b': 40, 'a': 1.0},   # Vermelho
    'Vinculo_Suspeito_MEDIO': {'r': 230, 'g': 126, 'b': 34, 'a': 1.0}, # Âmbar
    'É_Dono_De': {'r': 255, 'g': 159, 'b': 64, 'a': 0.85},             # Laranja claro
    'Participou_Licitacao': {'r': 100, 'g': 181, 'b': 246, 'a': 0.7},  # Azul claro
    'Concorreu_Contra': {'r': 180, 'g': 180, 'b': 180, 'a': 0.5},      # Cinza
}

G_cheio_nx = nx.MultiGraph()
for _, r in df_grafo_cheio_nos.iterrows():
    classe = sanitizar_texto(r['Classe'])
    G_cheio_nx.add_node(
        sanitizar_texto(r['Id']),
        label=sanitizar_texto(r['Label']),
        classe=classe,
        descricao=sanitizar_texto(r['Descricao']),
        viz={
            'color': dict(CORES_NO.get(classe, {'r': 150, 'g': 150, 'b': 150, 'a': 1.0})),
            'size': float(TAMANHOS_NO.get(classe, 12.0)),
        },
    )

for _, r in df_grafo_cheio_arestas.iterrows():
    src = sanitizar_texto(r['Source'])
    tgt = sanitizar_texto(r['Target'])
    if src not in G_cheio_nx or tgt not in G_cheio_nx:
        continue
    tipo = sanitizar_texto(r['Tipo_Relacao'])
    nivel = sanitizar_texto(r['Nivel_Risco'])
    chave_cor = f"{tipo}_{nivel}" if tipo == 'Vinculo_Suspeito' and nivel in ('ALTO', 'MEDIO') else tipo
    G_cheio_nx.add_edge(
        src,
        tgt,
        key=tipo,
        label=sanitizar_texto(r['Label']),
        tipo_relacao=tipo,
        weight=float(r['Weight']),
        descricao=sanitizar_texto(r['Descricao']),
        nivel_risco=nivel,
        motivos_vinculo=sanitizar_texto(r['Motivos_Vinculo']),
        qtd_certames_comuns=int(r['Qtd_Certames_Comuns']),
        qtd_itens_comuns=int(r['Qtd_Itens_Comuns']),
        segmento_objeto=sanitizar_texto(r['Segmento_Objeto']),
        viz={'color': dict(CORES_ARESTA.get(chave_cor, {'r': 160, 'g': 160, 'b': 160, 'a': 0.6}))},
    )

nx.write_gexf(G_cheio_nx, ARQ_GRAFO_CHEIO_GEXF, encoding='utf-8')

print("\nEtapa 2 concluída! Grafo 'Cheio' gerado com sucesso:")
print(f"  -> {ARQ_GRAFO_CHEIO_NOS} ({len(df_grafo_cheio_nos)} nós)")
print(f"  -> {ARQ_GRAFO_CHEIO_ARESTAS} ({len(df_grafo_cheio_arestas)} arestas)")
print(f"  -> {ARQ_GRAFO_CHEIO_GEXF} ({G_cheio_nx.number_of_nodes()} nós | {G_cheio_nx.number_of_edges()} arestas)")
