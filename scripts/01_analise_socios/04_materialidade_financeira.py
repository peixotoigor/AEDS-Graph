"""
ETAPA 4 (PASSO 1): Materialidade Financeira e Filtro Anti-Falso Positivo
========================================================================

Entrada:
  - outputs/01_analise_socios/grafo_cheio_nos.csv
  - outputs/01_analise_socios/subgrafos_fraudes_nos.csv
  - outputs/01_analise_socios/subgrafos_fraudes_arestas.csv
  - outputs/01_analise_socios/alertas_vinculos_concorrentes.csv
  - database/2025/raw/SICOM.2025.3122306.licitacao/2025.3122306.licitacao.homologLicitacao.csv
  - database/2025/raw/SICOM.2025.3122306.empenho/2025.3122306.empenho.empenho.csv
  - database/2025/raw/SICOM.2025.3122306.empenho/2025.3122306.empenho.credorEmpenho.csv
  - database/2025/raw/SICOM.2025.3122306.despesa/2025.3122306.despesa.pagamento.csv

Processamento:
  1. Agrega valores homologados (vlr_unitario * num_quant_item), empenhos
     contratuais líquidos (excluindo '99 - DESPESA NÃO DECORRENTE DE LICITAÇÃO')
     e pagamentos líquidos vinculados por CNPJ/CPF higienizado.
  2. Cruza a materialidade financeira com os nós e arestas de subgrafos_fraudes.
  3. Aplica filtro anti-falso positivo diferenciando pares com evidência dura
     (sócio em comum, mesma raiz CNPJ, mesmo endereço/telefone/e-mail) de pares
     puramente onomásticos (apenas sobrenome em comum, rebaixados a
     MEDIO_ONOMASTICO com Validacao_Manual=True).
  4. Calcula Risco_Materializado = Score * log1p(Materialidade_Par) e ordena os
     componentes conexos por prioridade investigativa.

Saídas:
  - database/2025/processed/01_analise_socios/materialidade_empresas.csv
  - outputs/01_analise_socios/subgrafos_fraudes_enriquecido_nos.csv
  - outputs/01_analise_socios/subgrafos_fraudes_enriquecido_arestas.csv
  - outputs/01_analise_socios/subgrafos_fraudes_enriquecido.gexf
  - outputs/01_analise_socios/ranking_componentes_risco.csv
"""

import ast
import json
import math
import re
from pathlib import Path

import networkx as nx
import pandas as pd

# ==========================================
# 0. CONFIGURAÇÕES E CAMINHOS
# ==========================================
BASE_DIR = Path(__file__).resolve().parents[2]
DIR_RAW = BASE_DIR / 'database' / '2025' / 'raw'
DIR_PROC = BASE_DIR / 'database' / '2025' / 'processed' / '01_analise_socios'
DIR_OUT = BASE_DIR / 'outputs' / '01_analise_socios'
DIR_PROC.mkdir(parents=True, exist_ok=True)
DIR_OUT.mkdir(parents=True, exist_ok=True)

ARQ_GRAFO_CHEIO_NOS = DIR_OUT / 'grafo_cheio_nos.csv'
ARQ_GRAFO_CHEIO_ARESTAS = DIR_OUT / 'grafo_cheio_arestas.csv'
ARQ_SUB_NOS = DIR_OUT / 'subgrafos_fraudes_nos.csv'
ARQ_SUB_ARESTAS = DIR_OUT / 'subgrafos_fraudes_arestas.csv'
ARQ_ALERTAS = DIR_OUT / 'alertas_vinculos_concorrentes.csv'
ARQ_SOCIOS_REAIS = DIR_OUT / 'socios_reais.csv'
ARQ_CACHE_QSA = DIR_OUT / 'cache_qsa_brasilapi.json'
ARQ_MAP_VIS = BASE_DIR / 'scripts' / '04_visualizacoes' / 'gerar_grafos_gephi.py'

ARQ_HOMOLOG = DIR_RAW / 'SICOM.2025.3122306.licitacao' / '2025.3122306.licitacao.homologLicitacao.csv'
ARQ_EMPENHO = DIR_RAW / 'SICOM.2025.3122306.empenho' / '2025.3122306.empenho.empenho.csv'
ARQ_CREDOR_EMP = DIR_RAW / 'SICOM.2025.3122306.empenho' / '2025.3122306.empenho.credorEmpenho.csv'
ARQ_PAGAMENTO = DIR_RAW / 'SICOM.2025.3122306.despesa' / '2025.3122306.despesa.pagamento.csv'

ARQ_MAT_PROC = DIR_PROC / 'materialidade_empresas.csv'
ARQ_OUT_NOS = DIR_OUT / 'subgrafos_fraudes_enriquecido_nos.csv'
ARQ_OUT_ARESTAS = DIR_OUT / 'subgrafos_fraudes_enriquecido_arestas.csv'
ARQ_OUT_GEXF = DIR_OUT / 'subgrafos_fraudes_enriquecido.gexf'
ARQ_OUT_RANKING = DIR_OUT / 'ranking_componentes_risco.csv'
ARQ_OUT_AUDITORIA = DIR_OUT / 'resumo_auditoria_eixo1.json'
ARQ_OUT_PSEUDONIMOS = DIR_OUT / 'mapeamento_pseudonimos_restrito.csv'

IND_NAO_LICITACAO = '99 - DESPESA NÃO DECORRENTE DE LICITAÇÃO'
LIMIAR_MATERIALIDADE_SIGNIFICATIVA = 100_000.0


# ==========================================
# 1. FUNÇÕES AUXILIARES
# ==========================================
def sanitizar_texto(valor, padrao=''):
    """Remove valores nulos e caracteres de controle inválidos em XML/GEXF."""
    if valor is None or pd.isna(valor):
        return padrao
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', str(valor))
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto if texto else padrao


def limpar_documento(doc):
    """Higieniza CNPJ/CPF preservando zeros à esquerda e CPFs mascarados."""
    if pd.isna(doc):
        return 'DESCONHECIDO'
    s = str(doc).strip()
    if '*' in s:
        return s
    doc_str = s.replace('.', '').replace('-', '').replace('/', '')
    if 'E+' in doc_str.upper():
        try:
            doc_str = str(int(float(doc_str.replace(',', '.'))))
        except ValueError:
            pass
    if doc_str.isdigit():
        if 9 <= len(doc_str) < 11:
            doc_str = doc_str.zfill(11)
        elif 12 <= len(doc_str) < 14:
            doc_str = doc_str.zfill(14)
    return doc_str or 'DESCONHECIDO'


def formatar_brl(valor):
    """Formata número em moeda brasileira legível (ex.: R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


# ==========================================
# 2. AGREGAÇÃO DA MATERIALIDADE FINANCEIRA — O(N)
# ==========================================
def calcular_materialidade_empresas(df_empresas_grafo):
    """Agrega homologações, empenhos contratuais líquidos e pagamentos líquidos por empresa."""
    df_hom = pd.read_csv(ARQ_HOMOLOG, sep=';', dtype=str)
    df_hom['Id_Empresa'] = df_hom['num_doc_vencedor'].apply(limpar_documento)
    df_hom['vlr_unitario'] = pd.to_numeric(df_hom['vlr_unitario'], errors='coerce').fillna(0.0)
    df_hom['num_quant_item'] = pd.to_numeric(df_hom['num_quant_item'], errors='coerce').fillna(0.0)
    df_hom['Vlr_Homologado_Item'] = df_hom['vlr_unitario'] * df_hom['num_quant_item']

    agg_hom = (
        df_hom.groupby('Id_Empresa', as_index=False)
        .agg(
            Qtd_Itens_Homologados=('seq_hom_licitacao', 'count'),
            Vlr_Homologado=('Vlr_Homologado_Item', 'sum'),
        )
    )

    df_emp = pd.read_csv(ARQ_EMPENHO, sep=';', dtype=str)
    df_cred = pd.read_csv(ARQ_CREDOR_EMP, sep=';', dtype=str)
    df_cred['Id_Empresa'] = df_cred['num_doc_credor'].apply(limpar_documento)

    df_emp = df_emp[df_emp['ind_dec_licitacao'] != IND_NAO_LICITACAO].copy()
    for col in ('vlr_empenhado', 'vlr_reforco', 'vlr_anulempenho'):
        df_emp[col] = pd.to_numeric(df_emp[col], errors='coerce').fillna(0.0)
    df_emp['Vlr_Empenhado_Liq'] = (
        df_emp['vlr_empenhado'] + df_emp['vlr_reforco'] - df_emp['vlr_anulempenho']
    )

    df_emp = df_emp.merge(df_cred[['seq_empenho', 'Id_Empresa']], on='seq_empenho', how='left')

    df_pag = pd.read_csv(ARQ_PAGAMENTO, sep=';', dtype=str)
    for col in ('vlr_pag_fonte', 'vlr_anu_fonte'):
        df_pag[col] = pd.to_numeric(df_pag[col], errors='coerce').fillna(0.0)
    df_pag['Vlr_Pago_Liq'] = df_pag['vlr_pag_fonte'] - df_pag['vlr_anu_fonte']
    pag_por_emp = (
        df_pag[df_pag['seq_empenho'] != '-1']
        .groupby('seq_empenho', as_index=False)['Vlr_Pago_Liq']
        .sum()
    )

    df_emp = df_emp.merge(pag_por_emp, on='seq_empenho', how='left')
    df_emp['Vlr_Pago_Liq'] = df_emp['Vlr_Pago_Liq'].fillna(0.0)

    agg_emp = (
        df_emp.groupby('Id_Empresa', as_index=False)
        .agg(
            Qtd_Empenhos=('seq_empenho', 'count'),
            Vlr_Empenhado_Liq=('Vlr_Empenhado_Liq', 'sum'),
            Vlr_Pago_Liq=('Vlr_Pago_Liq', 'sum'),
        )
    )

    base = df_empresas_grafo[['Id', 'Label']].rename(columns={'Id': 'Id_Empresa'}).drop_duplicates('Id_Empresa')
    mat = base.merge(agg_hom, on='Id_Empresa', how='left').merge(agg_emp, on='Id_Empresa', how='left')
    for col_int in ('Qtd_Itens_Homologados', 'Qtd_Empenhos'):
        mat[col_int] = mat[col_int].fillna(0).astype(int)
    for col_flt in ('Vlr_Homologado', 'Vlr_Empenhado_Liq', 'Vlr_Pago_Liq'):
        mat[col_flt] = mat[col_flt].fillna(0.0).round(2)

    mat['Materialidade_Base'] = mat.apply(
        lambda r: r['Vlr_Empenhado_Liq'] if r['Vlr_Empenhado_Liq'] > 0 else r['Vlr_Homologado'],
        axis=1,
    ).round(2)
    return mat.sort_values(['Vlr_Empenhado_Liq', 'Vlr_Homologado'], ascending=False)


# ==========================================
# 2B. AUDITORIA E PSEUDONIMIZAÇÃO LGPD
# ==========================================
def carregar_dicionarios_pseudonimos():
    """Lê via AST (somente leitura) os dicionários oficiais de pseudonímia de gerar_grafos_gephi.py."""
    alvo = {'PSEUDO_EIXO1_EMP', 'PSEUDO_EIXO1_SOC', 'PSEUDO_EIXO2', 'PSEUDO_EIXO3_CREDS', 'UNIDADE_CURTA'}
    dicionarios = {k: {} for k in alvo}
    if not ARQ_MAP_VIS.exists():
        return dicionarios
    arvore = ast.parse(ARQ_MAP_VIS.read_text(encoding='utf-8'))
    for node in arvore.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nome = node.targets[0].id
            if nome in alvo:
                dicionarios[nome] = ast.literal_eval(node.value)
    return dicionarios


def _pseudo_por_comp_id_atributo(comp_id):
    """Mapeia os atributos físicos compartilhados para os pseudônimos End. A/B e Tel. A/B."""
    mapa = {
        1: ('End. A', 'Tel. A'),
        2: ('', 'Tel. B'),
        5: ('End. B', ''),
    }
    return mapa.get(int(comp_id), ('', ''))


def gerar_mapeamento_pseudonimos(df_out_nos, df_alertas, pseudo_dicts):
    """Consolida mapeamento restrito (protegido pelo .gitignore) entre pseudônimos LGPD e IDs reais."""
    linhas = []
    pseudo_emp = pseudo_dicts.get('PSEUDO_EIXO1_EMP', {})
    pseudo_soc = pseudo_dicts.get('PSEUDO_EIXO1_SOC', {})

    tipo_socio_map = {}
    qual_socio_map = {}
    if ARQ_SOCIOS_REAIS.exists():
        df_soc = pd.read_csv(ARQ_SOCIOS_REAIS, dtype=str).fillna('')
        for _, r in df_soc.iterrows():
            sid = sanitizar_texto(r.get('Id_Socio'))
            if sid:
                tipo_socio_map[sid] = sanitizar_texto(r.get('Tipo_Socio'), 'PF')
                qual_socio_map[sid] = sanitizar_texto(r.get('Qualificacao'))

    nos_map = df_out_nos.set_index('Id').to_dict(orient='index') if not df_out_nos.empty else {}
    comp_por_emp = {nid: int(info.get('Componente_Id', 0) or 0) for nid, info in nos_map.items()}

    for id_real, pseudo in pseudo_emp.items():
        info = nos_map.get(id_real, {})
        linhas.append({
            'Categoria': 'Empresa',
            'Pseudonimo': pseudo,
            'ID_Real': id_real,
            'Nome_Real': sanitizar_texto(info.get('Label')),
            'Tipo_Detalhe': 'MEI/EI' if pseudo.startswith('EI-') else 'Pessoa Jurídica',
            'Componente_Id': int(info.get('Componente_Id', 0) or 0),
            'Vlr_Empenhado_Liq': float(info.get('Vlr_Empenhado_Liq', 0.0) or 0.0),
        })

    for id_real, pseudo in pseudo_soc.items():
        info = nos_map.get(id_real, {})
        tipo_s = tipo_socio_map.get(id_real, 'PJ' if 'LTDA' in id_real else 'PF')
        qual_s = qual_socio_map.get(id_real, '')
        linhas.append({
            'Categoria': 'Socio',
            'Pseudonimo': f"{pseudo} (PJ)" if tipo_s == 'PJ' else pseudo,
            'ID_Real': id_real,
            'Nome_Real': sanitizar_texto(info.get('Label')),
            'Tipo_Detalhe': f"{tipo_s} | {qual_s}".strip(' |'),
            'Componente_Id': int(info.get('Componente_Id', 0) or 0),
            'Vlr_Empenhado_Liq': 0.0,
        })

    # Atributos físicos compartilhados (End. A/B e Tel. A/B)
    for _, r in df_alertas.iterrows():
        a, b = sanitizar_texto(r.get('Empresa_A')), sanitizar_texto(r.get('Empresa_B'))
        comp_id = comp_por_emp.get(a) or comp_por_emp.get(b)
        if not comp_id:
            continue
        p_end, p_tel = _pseudo_por_comp_id_atributo(comp_id)
        end_real = sanitizar_texto(r.get('Mesmo_Endereco'))
        tel_real = sanitizar_texto(r.get('Mesmo_Telefone'))
        if p_end and end_real:
            linhas.append({
                'Categoria': 'Endereco_Compartilhado',
                'Pseudonimo': p_end,
                'ID_Real': f"COMP_{comp_id}_END",
                'Nome_Real': end_real,
                'Tipo_Detalhe': f"{pseudo_emp.get(a, a)} x {pseudo_emp.get(b, b)}",
                'Componente_Id': int(comp_id),
                'Vlr_Empenhado_Liq': 0.0,
            })
        if p_tel and tel_real:
            linhas.append({
                'Categoria': 'Telefone_Compartilhado',
                'Pseudonimo': p_tel,
                'ID_Real': f"COMP_{comp_id}_TEL",
                'Nome_Real': tel_real,
                'Tipo_Detalhe': f"{pseudo_emp.get(a, a)} x {pseudo_emp.get(b, b)}",
                'Componente_Id': int(comp_id),
                'Vlr_Empenhado_Liq': 0.0,
            })

    return pd.DataFrame(linhas)


def consolidar_resumo_auditoria(
    df_cheio_nos,
    df_alertas,
    df_mat,
    df_out_nos,
    df_out_arestas,
    df_ranking,
    pseudo_dicts,
):
    """Consolida métricas livres de PII em outputs/01_analise_socios/resumo_auditoria_eixo1.json."""
    df_cheio_arestas = (
        pd.read_csv(ARQ_GRAFO_CHEIO_ARESTAS, dtype=str).fillna('')
        if ARQ_GRAFO_CHEIO_ARESTAS.exists()
        else pd.DataFrame()
    )

    # 1. Cobertura QSA dos 673 CNPJs válidos
    emp_ids = sorted(df_cheio_nos[df_cheio_nos['Classe'] == 'Empresa']['Id'].unique())
    cnpjs = [d for d in emp_ids if d.isdigit() and len(d) == 14]
    docs_mascarados = [d for d in emp_ids if not d.isdigit()]

    cache = {}
    if ARQ_CACHE_QSA.exists():
        with open(ARQ_CACHE_QSA, 'r', encoding='utf-8') as f:
            cache = json.load(f)

    emp_com_socio = set()
    if ARQ_SOCIOS_REAIS.exists():
        df_soc = pd.read_csv(ARQ_SOCIOS_REAIS, dtype=str).fillna('')
        emp_com_socio = set(df_soc['Empresa'].unique())

    em_cache = sum(1 for c in cnpjs if c in cache)
    com_qsa_receita = sum(1 for c in cnpjs if isinstance(cache.get(c), dict) and bool(cache[c].get('qsa')))
    cobertos_total = len(set(cnpjs) & emp_com_socio) if emp_com_socio else sum(
        1 for c in cnpjs if isinstance(cache.get(c), dict) and 'erro' not in cache[c]
    )
    cobertos_mei_ei = max(0, cobertos_total - com_qsa_receita)
    vazios_ou_erro = len(cnpjs) - cobertos_total

    # 2. Métricas de documento(s) mascarado(s) sem expor PII
    ar_masc = (
        df_cheio_arestas[
            df_cheio_arestas['Source'].isin(docs_mascarados)
            | df_cheio_arestas['Target'].isin(docs_mascarados)
        ]
        if (not df_cheio_arestas.empty and docs_mascarados)
        else pd.DataFrame()
    )
    mat_masc = df_mat[df_mat['Id_Empresa'].isin(docs_mascarados)] if docs_mascarados else pd.DataFrame()

    # 3. Estrato MEDIO podado antes da Etapa 3
    mat_idx = df_mat.set_index('Id_Empresa').to_dict(orient='index')
    df_medio = df_alertas[df_alertas['Nivel'] == 'MEDIO']
    bilateral = unilateral = sem_emp = 0
    soma_emp_pares = 0.0
    for _, r in df_medio.iterrows():
        va = float(mat_idx.get(sanitizar_texto(r['Empresa_A']), {}).get('Vlr_Empenhado_Liq', 0.0) or 0.0)
        vb = float(mat_idx.get(sanitizar_texto(r['Empresa_B']), {}).get('Vlr_Empenhado_Liq', 0.0) or 0.0)
        if va > 0 and vb > 0:
            bilateral += 1
        elif va > 0 or vb > 0:
            unilateral += 1
        else:
            sem_emp += 1
        soma_emp_pares += va + vb

    emps_medio = set(df_medio['Empresa_A'].map(sanitizar_texto)) | set(df_medio['Empresa_B'].map(sanitizar_texto))
    soma_emp_dist = sum(float(mat_idx.get(e, {}).get('Vlr_Empenhado_Liq', 0.0) or 0.0) for e in emps_medio)
    soma_hom_dist = sum(float(mat_idx.get(e, {}).get('Vlr_Homologado', 0.0) or 0.0) for e in emps_medio)
    soma_pag_dist = sum(float(mat_idx.get(e, {}).get('Vlr_Pago_Liq', 0.0) or 0.0) for e in emps_medio)

    # 4. Resumo dos 6 componentes com pseudônimos LGPD
    pseudo_emp = pseudo_dicts.get('PSEUDO_EIXO1_EMP', {})
    resumo_comps = []
    for _, r in df_ranking.iterrows():
        cid = int(r['Componente_Id'])
        c_emps = df_out_nos[(df_out_nos['Componente_Id'] == cid) & (df_out_nos['Classe'] == 'Empresa')]['Id'].tolist()
        pseudos = [pseudo_emp.get(e, f"Emp-Comp{cid}") for e in sorted(c_emps)]
        resumo_comps.append({
            'componente_id': cid,
            'empresas_pseudonimos': pseudos,
            'classificacao_prioridade': sanitizar_texto(r['Classificacao_Prioridade']),
            'em_triangulo_k3': bool(r['Em_Triangulo_K3']),
            'tem_evidencia_dura': bool(r['Tem_Evidencia_Dura']),
            'score_maximo': float(r['Score_Maximo']),
            'qtd_certames_comuns': int(r['Qtd_Certames_Comuns']),
            'qtd_itens_comuns': int(r['Qtd_Itens_Comuns']),
            'segmento_objeto': sanitizar_texto(r['Segmento_Objeto']),
            'vlr_homologado_total': float(r['Vlr_Homologado_Total']),
            'vlr_empenhado_liq_total': float(r['Vlr_Empenhado_Liq_Total']),
            'vlr_pago_liq_total': float(r['Vlr_Pago_Liq_Total']),
            'risco_materializado_max': float(r['Risco_Materializado_Max']),
        })

    return {
        'invariantes_topologia': {
            'grafo_cheio_nos': int(len(df_cheio_nos)),
            'grafo_cheio_arestas': int(len(df_cheio_arestas)),
            'alertas_brutos_total': int(len(df_alertas)),
            'alertas_por_nivel': {str(k): int(v) for k, v in df_alertas['Nivel'].value_counts().to_dict().items()},
            'subgrafo_reduzido_nos': int(len(df_out_nos)),
            'subgrafo_reduzido_arestas': int(len(df_out_arestas)),
            'qtd_componentes': int(len(df_ranking)),
            'componentes_ids': sorted(int(x) for x in df_ranking['Componente_Id'].tolist()),
        },
        'cobertura_qsa': {
            'cnpjs_validos': int(len(cnpjs)),
            'em_cache': int(em_cache),
            'com_qsa_receita': int(com_qsa_receita),
            'cobertos_mei_ei': int(cobertos_mei_ei),
            'total_cobertos_ge_1_socio': int(cobertos_total),
            'vazios_ou_erro': int(vazios_ou_erro),
            'cobertura_pct': round((100.0 * cobertos_total / len(cnpjs)) if cnpjs else 0.0, 2),
        },
        'documentos_mascarados': {
            'qtd_docs_mascarados': int(len(docs_mascarados)),
            'arestas_grafo_cheio': int(len(ar_masc)),
            'arestas_concorreu_contra': int((ar_masc['Tipo_Relacao'] == 'Concorreu_Contra').sum()) if not ar_masc.empty else 0,
            'arestas_participou_licitacao': int((ar_masc['Tipo_Relacao'] == 'Participou_Licitacao').sum()) if not ar_masc.empty else 0,
            'qtd_itens_homologados': int(pd.to_numeric(mat_masc['Qtd_Itens_Homologados'], errors='coerce').sum()) if not mat_masc.empty else 0,
            'vlr_homologado': round(float(pd.to_numeric(mat_masc['Vlr_Homologado'], errors='coerce').sum()), 2) if not mat_masc.empty else 0.0,
            'qtd_empenhos': int(pd.to_numeric(mat_masc['Qtd_Empenhos'], errors='coerce').sum()) if not mat_masc.empty else 0,
            'vlr_empenhado_liq': round(float(pd.to_numeric(mat_masc['Vlr_Empenhado_Liq'], errors='coerce').sum()), 2) if not mat_masc.empty else 0.0,
            'vlr_pago_liq': round(float(pd.to_numeric(mat_masc['Vlr_Pago_Liq'], errors='coerce').sum()), 2) if not mat_masc.empty else 0.0,
        },
        'estrato_medio_podado': {
            'qtd_pares': int(len(df_medio)),
            'qtd_bilateral_empenhado': int(bilateral),
            'qtd_unilateral_empenhado': int(unilateral),
            'qtd_sem_empenho': int(sem_emp),
            'qtd_empresas_distintas': int(len(emps_medio)),
            'vlr_empenhado_soma_pares': round(soma_emp_pares, 2),
            'vlr_empenhado_empresas_distintas': round(soma_emp_dist, 2),
            'vlr_homologado_empresas_distintas': round(soma_hom_dist, 2),
            'vlr_pago_empresas_distintas': round(soma_pag_dist, 2),
        },
        'componentes_risco': resumo_comps,
    }


# ==========================================
# 3. ENRIQUECIMENTO DO SUBGRAFO E RANKING
# ==========================================
def main():
    for arq in (ARQ_GRAFO_CHEIO_NOS, ARQ_SUB_NOS, ARQ_SUB_ARESTAS, ARQ_ALERTAS):
        if not arq.exists():
            raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {arq}")

    df_cheio_nos = pd.read_csv(ARQ_GRAFO_CHEIO_NOS, dtype=str).fillna('')
    df_sub_nos = pd.read_csv(ARQ_SUB_NOS, dtype=str).fillna('')
    df_sub_arestas = pd.read_csv(ARQ_SUB_ARESTAS, dtype=str).fillna('')
    df_alertas = pd.read_csv(ARQ_ALERTAS, dtype=str).fillna('')

    df_empresas_grafo = df_cheio_nos[df_cheio_nos['Classe'] == 'Empresa'].copy()
    df_mat = calcular_materialidade_empresas(df_empresas_grafo)
    df_mat.to_csv(ARQ_MAT_PROC, index=False, encoding='utf-8')
    mat_map = df_mat.set_index('Id_Empresa').to_dict(orient='index')

    # Mapeamento de evidências duras por par ordenado de empresas — O(E_alertas)
    alertas_map = {}
    for _, r in df_alertas.iterrows():
        a, b = sorted([limpar_documento(r['Empresa_A']), limpar_documento(r['Empresa_B'])])
        tem_socios = bool(sanitizar_texto(r.get('Socios_Em_Comum')))
        tem_raiz = str(r.get('Mesma_Raiz_CNPJ', '')).strip().lower() == 'true'
        tem_end = bool(sanitizar_texto(r.get('Mesmo_Endereco')))
        tem_tel = bool(sanitizar_texto(r.get('Mesmo_Telefone')))
        tem_em = bool(sanitizar_texto(r.get('Mesmo_Email')))
        tem_dura = tem_socios or tem_raiz or tem_end or tem_tel or tem_em
        alertas_map[(a, b)] = {
            'tem_evidencia_dura': tem_dura,
            'motivos': sanitizar_texto(r.get('Motivos_Vinculo')),
            'score': float(pd.to_numeric(r.get('Score'), errors='coerce') or 0.0),
            'peso_conc': int(pd.to_numeric(r.get('Peso_Concorrencia'), errors='coerce') or 0),
            'qtd_certames': int(pd.to_numeric(r.get('Qtd_Certames_Comuns'), errors='coerce') or 0),
            'qtd_itens': int(pd.to_numeric(r.get('Qtd_Itens_Comuns'), errors='coerce') or 0),
            'segmento': sanitizar_texto(r.get('Segmento_Objeto')),
        }

    # Identifica evidência dura por componente e empresa — O(V + E)
    comp_tem_dura = {}
    emp_tem_dura = set()
    linhas_arestas = []

    for _, r in df_sub_arestas.iterrows():
        src = sanitizar_texto(r['Source'])
        tgt = sanitizar_texto(r['Target'])
        tipo = sanitizar_texto(r['Tipo_Relacao'])
        peso = float(pd.to_numeric(r['Weight'], errors='coerce') or 1.0)
        comp_id = int(pd.to_numeric(r['Componente_Id'], errors='coerce') or 0)
        em_k3 = str(r.get('Em_Triangulo_K3', '')).strip().lower() == 'true'
        lbl = sanitizar_texto(r.get('Label'), tipo)
        desc_orig = sanitizar_texto(r.get('Descricao'))
        motivos = sanitizar_texto(r.get('Motivos_Vinculo'))
        nivel_orig = sanitizar_texto(r.get('Nivel_Risco'))
        qtd_certames = 0
        qtd_itens = 0
        segmento_obj = ''

        if tipo == 'Vinculo_Suspeito':
            par = tuple(sorted([src, tgt]))
            al = alertas_map.get(par, {})
            qtd_certames = int(pd.to_numeric(r.get('Qtd_Certames_Comuns'), errors='coerce') or al.get('qtd_certames', 0) or 0)
            qtd_itens = int(pd.to_numeric(r.get('Qtd_Itens_Comuns'), errors='coerce') or al.get('qtd_itens', 0) or 0)
            segmento_obj = sanitizar_texto(r.get('Segmento_Objeto')) or al.get('segmento', '')
            tem_dura = bool(al.get('tem_evidencia_dura', False))
            if not motivos:
                motivos = al.get('motivos', '')

            mat_a = mat_map.get(src, {})
            mat_b = mat_map.get(tgt, {})
            emp_a_vlr = float(mat_a.get('Vlr_Empenhado_Liq', 0.0))
            emp_b_vlr = float(mat_b.get('Vlr_Empenhado_Liq', 0.0))
            hom_a_vlr = float(mat_a.get('Vlr_Homologado', 0.0))
            hom_b_vlr = float(mat_b.get('Vlr_Homologado', 0.0))

            base_a = emp_a_vlr if emp_a_vlr > 0 else hom_a_vlr
            base_b = emp_b_vlr if emp_b_vlr > 0 else hom_b_vlr
            materialidade_par = round(base_a + base_b, 2)
            ambas_materialidade = (base_a > 0) and (base_b > 0)
            risco_mat = round(peso * math.log1p(max(materialidade_par, 0.0)), 4)

            validacao_manual = not tem_dura
            if tem_dura:
                nivel_ref = 'ALTO'
                comp_tem_dura[comp_id] = True
                emp_tem_dura.update([src, tgt])
            else:
                nivel_ref = 'MEDIO_ONOMASTICO'
                comp_tem_dura.setdefault(comp_id, False)

            tag_mat = f"Materialidade Par: {formatar_brl(materialidade_par)} | Risco Materializado: {risco_mat:.2f}"
            if validacao_manual:
                tag_val = (
                    "Validação Manual (apenas sobrenome; ambas com contratos)"
                    if (ambas_materialidade and materialidade_par >= LIMIAR_MATERIALIDADE_SIGNIFICATIVA)
                    else "Validação Manual (apenas sobrenome; baixa/unilateral materialidade)"
                )
            else:
                tag_val = "Evidência Dura Confirmada"

            desc = f"{desc_orig} | {tag_mat} | {tag_val}" if desc_orig else f"{lbl} | {tag_mat} | {tag_val}"
        else:
            tem_dura = True
            validacao_manual = False
            materialidade_par = 0.0
            risco_mat = 0.0
            nivel_ref = ''
            desc = desc_orig

        linhas_arestas.append({
            'Source': src,
            'Target': tgt,
            'Tipo_Relacao': tipo,
            'Weight': peso,
            'Label': lbl,
            'Componente_Id': comp_id,
            'Em_Triangulo_K3': em_k3,
            'Nivel_Risco_Original': nivel_orig,
            'Nivel_Risco_Refinado': nivel_ref,
            'Tem_Evidencia_Dura': tem_dura,
            'Validacao_Manual': validacao_manual,
            'Materialidade_Par': materialidade_par,
            'Risco_Materializado': risco_mat,
            'Qtd_Certames_Comuns': qtd_certames,
            'Qtd_Itens_Comuns': qtd_itens,
            'Segmento_Objeto': segmento_obj,
            'Motivos_Vinculo': motivos,
            'Descricao': sanitizar_texto(desc),
        })

    df_out_arestas = pd.DataFrame(linhas_arestas)

    # Enriquecimento dos nós — O(V)
    linhas_nos = []
    for _, r in df_sub_nos.iterrows():
        id_no = sanitizar_texto(r['Id'])
        lbl = sanitizar_texto(r['Label'], id_no)
        cls = sanitizar_texto(r['Classe'])
        comp_id = int(pd.to_numeric(r['Componente_Id'], errors='coerce') or 0)
        em_k3 = str(r.get('Em_Triangulo_K3', '')).strip().lower() == 'true'
        desc_orig = sanitizar_texto(r.get('Descricao'))

        if cls == 'Empresa':
            m = mat_map.get(id_no, {})
            vlr_hom = float(m.get('Vlr_Homologado', 0.0))
            vlr_emp = float(m.get('Vlr_Empenhado_Liq', 0.0))
            vlr_pag = float(m.get('Vlr_Pago_Liq', 0.0))
            tem_dura_no = id_no in emp_tem_dura
            desc = (
                f"{desc_orig} | Homologado: {formatar_brl(vlr_hom)} | "
                f"Empenhado Líq.: {formatar_brl(vlr_emp)} | Pago Líq.: {formatar_brl(vlr_pag)}"
            )
        else:
            vlr_hom = 0.0
            vlr_emp = 0.0
            vlr_pag = 0.0
            tem_dura_no = bool(comp_tem_dura.get(comp_id, False))
            desc = desc_orig

        linhas_nos.append({
            'Id': id_no,
            'Label': lbl,
            'Classe': cls,
            'Componente_Id': comp_id,
            'Em_Triangulo_K3': em_k3,
            'Tem_Evidencia_Dura': tem_dura_no,
            'Vlr_Homologado': round(vlr_hom, 2),
            'Vlr_Empenhado_Liq': round(vlr_emp, 2),
            'Vlr_Pago_Liq': round(vlr_pag, 2),
            'Descricao': sanitizar_texto(desc),
        })

    df_out_nos = pd.DataFrame(linhas_nos)

    # Ranking de componentes por prioridade investigativa — O(V + E)
    ranking = []
    for comp_id, grp_n in df_out_nos.groupby('Componente_Id'):
        grp_a = df_out_arestas[
            (df_out_arestas['Componente_Id'] == comp_id)
            & (df_out_arestas['Tipo_Relacao'] == 'Vinculo_Suspeito')
        ]
        empresas_grp = grp_n[grp_n['Classe'] == 'Empresa']
        socios_grp = grp_n[grp_n['Classe'] != 'Empresa']
        tem_dura_comp = bool(grp_a['Tem_Evidencia_Dura'].any()) if not grp_a.empty else False
        em_k3_comp = bool(grp_n['Em_Triangulo_K3'].any())
        vlr_hom_tot = round(float(empresas_grp['Vlr_Homologado'].sum()), 2)
        vlr_emp_tot = round(float(empresas_grp['Vlr_Empenhado_Liq'].sum()), 2)
        vlr_pag_tot = round(float(empresas_grp['Vlr_Pago_Liq'].sum()), 2)
        score_max = float(grp_a['Weight'].max()) if not grp_a.empty else 0.0
        risco_mat_max = float(grp_a['Risco_Materializado'].max()) if not grp_a.empty else 0.0
        qtd_cert_comp = int(grp_a['Qtd_Certames_Comuns'].sum()) if not grp_a.empty else 0
        qtd_itens_comp = int(grp_a['Qtd_Itens_Comuns'].sum()) if not grp_a.empty else 0
        seg_comp = ' ; '.join(
            dict.fromkeys(s for s in grp_a['Segmento_Objeto'].tolist() if s)
        ) if not grp_a.empty else ''

        if tem_dura_comp and vlr_emp_tot > 0:
            prioridade = 'CRITICA_EVIDENCIA_DURA_COM_CONTRATO'
        elif tem_dura_comp:
            prioridade = 'ALTA_EVIDENCIA_DURA_SEM_EMPENHO_2025'
        elif vlr_emp_tot >= LIMIAR_MATERIALIDADE_SIGNIFICATIVA:
            prioridade = 'MEDIA_ONOMASTICA_ALTA_MATERIALIDADE'
        else:
            prioridade = 'BAIXA_ONOMASTICA_REVISAO_MANUAL'

        ranking.append({
            'Componente_Id': int(comp_id),
            'Qtd_Nos': int(len(grp_n)),
            'Qtd_Empresas': int(len(empresas_grp)),
            'Qtd_Socios': int(len(socios_grp)),
            'Empresas': ' | '.join(empresas_grp['Label'].tolist()),
            'Em_Triangulo_K3': em_k3_comp,
            'Tem_Evidencia_Dura': tem_dura_comp,
            'Validacao_Manual': not tem_dura_comp,
            'Score_Maximo': round(score_max, 2),
            'Qtd_Certames_Comuns': qtd_cert_comp,
            'Qtd_Itens_Comuns': qtd_itens_comp,
            'Segmento_Objeto': seg_comp,
            'Vlr_Homologado_Total': vlr_hom_tot,
            'Vlr_Empenhado_Liq_Total': vlr_emp_tot,
            'Vlr_Pago_Liq_Total': vlr_pag_tot,
            'Risco_Materializado_Max': round(risco_mat_max, 4),
            'Classificacao_Prioridade': prioridade,
        })

    df_ranking = pd.DataFrame(ranking).sort_values(
        ['Tem_Evidencia_Dura', 'Risco_Materializado_Max', 'Score_Maximo'],
        ascending=[False, False, False],
    )

    df_out_nos.to_csv(ARQ_OUT_NOS, index=False, encoding='utf-8')
    df_out_arestas.to_csv(ARQ_OUT_ARESTAS, index=False, encoding='utf-8')
    df_ranking.to_csv(ARQ_OUT_RANKING, index=False, encoding='utf-8')

    # Exportação GEXF com tamanho proporcional a log1p(Vlr_Empenhado_Liq)
    G_nx = nx.MultiGraph()
    for _, r in df_out_nos.iterrows():
        cls = sanitizar_texto(r['Classe'])
        em_k3 = bool(r['Em_Triangulo_K3'])
        tem_dura_no = bool(r['Tem_Evidencia_Dura'])
        vlr_emp = float(r['Vlr_Empenhado_Liq'])

        if cls == 'Empresa':
            if tem_dura_no:
                cor = {'r': 214, 'g': 39, 'b': 40, 'a': 1.0} if em_k3 else {'r': 31, 'g': 119, 'b': 180, 'a': 1.0}
            else:
                cor = {'r': 230, 'g': 159, 'b': 0, 'a': 1.0}
            tam = round(14.0 + 2.5 * math.log1p(max(vlr_emp, 0.0)), 2)
        else:
            cor = {'r': 255, 'g': 127, 'b': 14, 'a': 1.0} if em_k3 else {'r': 255, 'g': 187, 'b': 120, 'a': 1.0}
            tam = 16.0 if em_k3 else 12.0

        G_nx.add_node(
            sanitizar_texto(r['Id']),
            label=sanitizar_texto(r['Label']),
            classe=cls,
            componente_id=int(r['Componente_Id']),
            em_triangulo_k3=em_k3,
            tem_evidencia_dura=tem_dura_no,
            vlr_homologado=float(r['Vlr_Homologado']),
            vlr_empenhado_liq=vlr_emp,
            vlr_pago_liq=float(r['Vlr_Pago_Liq']),
            descricao=sanitizar_texto(r['Descricao']),
            viz={'color': cor, 'size': float(tam)},
        )

    for _, r in df_out_arestas.iterrows():
        tipo = sanitizar_texto(r['Tipo_Relacao'])
        tem_dura = bool(r['Tem_Evidencia_Dura'])
        if tipo == 'Vinculo_Suspeito':
            cor_e = {'r': 214, 'g': 39, 'b': 40, 'a': 1.0} if tem_dura else {'r': 230, 'g': 159, 'b': 0, 'a': 1.0}
        else:
            cor_e = {'r': 255, 'g': 127, 'b': 14, 'a': 0.9} if bool(r['Em_Triangulo_K3']) else {'r': 140, 'g': 140, 'b': 140, 'a': 0.8}

        G_nx.add_edge(
            sanitizar_texto(r['Source']),
            sanitizar_texto(r['Target']),
            key=tipo,
            label=sanitizar_texto(r['Label']),
            tipo_relacao=tipo,
            weight=float(r['Weight']),
            componente_id=int(r['Componente_Id']),
            em_triangulo_k3=bool(r['Em_Triangulo_K3']),
            nivel_risco=sanitizar_texto(r['Nivel_Risco_Refinado']),
            tem_evidencia_dura=tem_dura,
            validacao_manual=bool(r['Validacao_Manual']),
            materialidade_par=float(r['Materialidade_Par']),
            risco_materializado=float(r['Risco_Materializado']),
            qtd_certames_comuns=int(r['Qtd_Certames_Comuns']),
            qtd_itens_comuns=int(r['Qtd_Itens_Comuns']),
            segmento_objeto=sanitizar_texto(r['Segmento_Objeto']),
            motivos_vinculo=sanitizar_texto(r['Motivos_Vinculo']),
            descricao=sanitizar_texto(r['Descricao']),
            viz={'color': cor_e},
        )

    nx.write_gexf(G_nx, ARQ_OUT_GEXF, encoding='utf-8')

    pseudo_dicts = carregar_dicionarios_pseudonimos()
    resumo_auditoria = consolidar_resumo_auditoria(
        df_cheio_nos=df_cheio_nos,
        df_alertas=df_alertas,
        df_mat=df_mat,
        df_out_nos=df_out_nos,
        df_out_arestas=df_out_arestas,
        df_ranking=df_ranking,
        pseudo_dicts=pseudo_dicts,
    )
    with open(ARQ_OUT_AUDITORIA, 'w', encoding='utf-8') as f:
        json.dump(resumo_auditoria, f, ensure_ascii=False, indent=2)

    df_pseudo_map = gerar_mapeamento_pseudonimos(
        df_out_nos=df_out_nos,
        df_alertas=df_alertas,
        pseudo_dicts=pseudo_dicts,
    )
    df_pseudo_map.to_csv(ARQ_OUT_PSEUDONIMOS, index=False, encoding='utf-8')

    print("Passo 1 concluído! Materialidade financeira e filtro anti-falso positivo aplicados:")
    print(f"  -> {ARQ_MAT_PROC} ({len(df_mat)} empresas do grafo)")
    print(f"  -> {ARQ_OUT_NOS} ({len(df_out_nos)} nós)")
    print(f"  -> {ARQ_OUT_ARESTAS} ({len(df_out_arestas)} arestas)")
    print(f"  -> {ARQ_OUT_RANKING} ({len(df_ranking)} componentes)")
    print(f"  -> {ARQ_OUT_GEXF} ({G_nx.number_of_nodes()} nós | {G_nx.number_of_edges()} arestas)")
    print(f"  -> {ARQ_OUT_AUDITORIA}")
    print(f"  -> {ARQ_OUT_PSEUDONIMOS} ({len(df_pseudo_map)} registros [RESTRITO / .gitignore])")


if __name__ == '__main__':
    main()
