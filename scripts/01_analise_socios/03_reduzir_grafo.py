"""
ETAPA 3: Redução Algorítmica do Grafo Cheio para o Subgrafo de Fraudes
======================================================================

Entrada (gerada pelo 02_enriquecimento_socios.py):
  - outputs/01_analise_socios/grafo_cheio_nos.csv
  - outputs/01_analise_socios/grafo_cheio_arestas.csv
  - outputs/01_analise_socios/alertas_vinculos_concorrentes.csv (opcional, para enriquecimento)

Algoritmos de Teoria dos Grafos Aplicados:
  1. Subgrafo Induzido por Arestas (Edge-Induced Subgraph) — O(V + E):
     Corta as arestas gravitacionais do órgão público ('Participou_Licitacao')
     e de concorrência comum, retendo as arestas críticas de conluio
     ('Vinculo_Suspeito' com peso >= 2.0) e a estrutura societária ('É_Dono_De')
     das empresas envolvidas.
  2. Decomposição 1-Core (Poda de Grau via Fila BFS) — O(V + E):
     Remove todos os vértices isolados (grau zero) que não possuem conexões suspeitas.
  3. Decomposição em Componentes Conexas (Union-Find com Path Compression
     e Union by Rank) — O(E · α(V)):
     Particiona o subgrafo nas ilhas/redes conexas de suspeita (|C_i| >= 2).
  4. Listagem de Triângulos Societários (Motivo K_3) — O(E · d_max):
     Identifica formalmente os ciclos fechados (Sócio -> Empresa A <-> Empresa B <- Sócio).

Saída:
  - outputs/01_analise_socios/subgrafos_fraudes_nos.csv
  - outputs/01_analise_socios/subgrafos_fraudes_arestas.csv
  - outputs/01_analise_socios/subgrafos_fraudes.gexf
"""

import os
import re
from collections import defaultdict, deque

import networkx as nx
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_DESTINO = os.path.join(BASE_DIR, 'outputs', '01_analise_socios')
os.makedirs(PASTA_DESTINO, exist_ok=True)
ARQ_GRAFO_CHEIO_NOS = os.path.join(PASTA_DESTINO, 'grafo_cheio_nos.csv')
ARQ_GRAFO_CHEIO_ARESTAS = os.path.join(PASTA_DESTINO, 'grafo_cheio_arestas.csv')
ARQ_ALERTAS = os.path.join(PASTA_DESTINO, 'alertas_vinculos_concorrentes.csv')

ARQ_SUBGRAFO_NOS = os.path.join(PASTA_DESTINO, 'subgrafos_fraudes_nos.csv')
ARQ_SUBGRAFO_ARESTAS = os.path.join(PASTA_DESTINO, 'subgrafos_fraudes_arestas.csv')
ARQ_SUBGRAFO_GEXF = os.path.join(PASTA_DESTINO, 'subgrafos_fraudes.gexf')

LIMIAR_SCORE_ALTO_RISCO = 2.0


def sanitizar_texto(valor, padrao=''):
    """Garante string limpa sem None/NaN nem caracteres de controle inválidos em XML/GEXF."""
    if valor is None or pd.isna(valor):
        return padrao
    texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', str(valor))
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto if texto else padrao


# =========================================================================
# 1. ESTRUTURA DE DADOS: UNION-FIND (CONJUNTOS DISJUNTOS)
# =========================================================================
class UnionFind:
    """Disjoint-Set com Compressão de Caminho e União por Rank — O(α(V)) por operação."""
    def __init__(self, elementos):
        self.pai = {x: x for x in elementos}
        self.rank = {x: 0 for x in elementos}

    def find(self, x):
        if self.pai[x] != x:
            self.pai[x] = self.find(self.pai[x])
        return self.pai[x]

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.pai[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True

    def componentes(self):
        grupos = defaultdict(set)
        for x in self.pai:
            grupos[self.find(x)].add(x)
        return list(grupos.values())


# =========================================================================
# 2. ESTRUTURA DE DADOS: GRAFO HETEROGÊNEO POR LISTA DE ADJACÊNCIA
# =========================================================================
class GrafoMulticamada:
    """Grafo G = (V, E, τ, φ, w) representado por Lista de Adjacência."""
    def __init__(self):
        self.nos = {}                 # id -> {'label': str, 'classe': str}
        self.adj = defaultdict(list)  # u  -> [(v, tipo, peso)]
        self.arestas = []             # [(u, v, tipo, peso)]

    def adicionar_no(self, id_no, label, classe):
        self.nos[id_no] = {'label': label, 'classe': classe}

    def adicionar_aresta(self, u, v, tipo, peso=1.0):
        self.arestas.append((u, v, tipo, float(peso)))
        self.adj[u].append((v, tipo, float(peso)))
        self.adj[v].append((u, tipo, float(peso)))

    def subgrafo_induzido_por_arestas(self, predicado):
        """Algoritmo 1: Subgrafo Induzido por Predicado de Aresta — O(V + E)."""
        sub = GrafoMulticamada()
        for id_no, info in self.nos.items():
            sub.adicionar_no(id_no, info['label'], info['classe'])
        for u, v, tipo, peso in self.arestas:
            if predicado(u, v, tipo, peso):
                sub.adicionar_aresta(u, v, tipo, peso)
        return sub

    def k_core(self, k=1):
        """Algoritmo 2: Decomposição k-Core (Poda de Grau via Fila BFS) — O(V + E)."""
        graus = {u: len(self.adj[u]) for u in self.nos}
        removidos = set()
        fila = deque([u for u, g in graus.items() if g < k])

        while fila:
            u = fila.popleft()
            if u in removidos:
                continue
            removidos.add(u)
            for v, _, _ in self.adj[u]:
                if v not in removidos:
                    graus[v] -= 1
                    if graus[v] < k:
                        fila.append(v)

        nos_ativos = set(self.nos.keys()) - removidos
        sub = GrafoMulticamada()
        for u in nos_ativos:
            sub.adicionar_no(u, self.nos[u]['label'], self.nos[u]['classe'])
        for u, v, tipo, peso in self.arestas:
            if u in nos_ativos and v in nos_ativos:
                sub.adicionar_aresta(u, v, tipo, peso)
        return sub

    def componentes_conexas(self, tamanho_minimo=2):
        """Algoritmo 3: Decomposição em Componentes Conexas (Union-Find) — O(E · α(V))."""
        uf = UnionFind(self.nos.keys())
        for u, v, _, _ in self.arestas:
            if u in self.nos and v in self.nos:
                uf.union(u, v)
        return [c for c in uf.componentes() if len(c) >= tamanho_minimo]

    def listar_triangulos_societarios(self):
        """Algoritmo 4: Listagem de Triângulos Societários (Motivo K_3) — O(E · d_max)."""
        donos_por_empresa = defaultdict(set)
        for u, v, tipo, _ in self.arestas:
            if tipo == 'É_Dono_De':
                if self.nos.get(u, {}).get('classe') in ('Sócio Real', 'Sócio'):
                    donos_por_empresa[v].add(u)
                else:
                    donos_por_empresa[u].add(v)

        triangulos = []
        for u, v, tipo, peso in self.arestas:
            if tipo == 'Vinculo_Suspeito':
                socios_comuns = donos_por_empresa[u] & donos_por_empresa[v]
                for s in sorted(socios_comuns):
                    triangulos.append({
                        'Socio_Id': s,
                        'Empresa_A_Id': u,
                        'Empresa_B_Id': v,
                        'Socio': self.nos[s]['label'],
                        'Empresa_A': self.nos[u]['label'],
                        'Empresa_B': self.nos[v]['label'],
                        'Score_Vinculo': peso,
                    })
        return triangulos


# =========================================================================
# 3. EXECUÇÃO DA REDUÇÃO E EXPORTAÇÃO DE "subgrafos_fraudes" (CSV + GEXF)
# =========================================================================
def _chave_aresta(u, v, tipo):
    a, b = sorted([sanitizar_texto(u), sanitizar_texto(v)])
    return (a, b, sanitizar_texto(tipo))


def _carregar_alertas_fallback():
    """Carrega alertas_vinculos_concorrentes.csv (se existir) para enriquecer Motivos_Vinculo."""
    if not os.path.exists(ARQ_ALERTAS):
        return {}
    df_al = pd.read_csv(ARQ_ALERTAS, dtype=str)
    mapa = {}
    for _, r in df_al.iterrows():
        a, b = sorted([sanitizar_texto(r.get('Empresa_A')), sanitizar_texto(r.get('Empresa_B'))])
        mapa[(a, b)] = {
            'nivel': sanitizar_texto(r.get('Nivel')),
            'motivos': sanitizar_texto(r.get('Motivos_Vinculo')),
            'peso_conc': sanitizar_texto(r.get('Peso_Concorrencia'), '0'),
            'qtd_certames': int(pd.to_numeric(r.get('Qtd_Certames_Comuns'), errors='coerce') or 0),
            'qtd_itens': int(pd.to_numeric(r.get('Qtd_Itens_Comuns'), errors='coerce') or 0),
            'segmento': sanitizar_texto(r.get('Segmento_Objeto')),
        }
    return mapa


def main():
    if not os.path.exists(ARQ_GRAFO_CHEIO_NOS) or not os.path.exists(ARQ_GRAFO_CHEIO_ARESTAS):
        raise FileNotFoundError(
            "Grafo cheio não encontrado! Execute primeiro: python scripts/02_enriquecimento_socios.py"
        )

    df_nos = pd.read_csv(ARQ_GRAFO_CHEIO_NOS, dtype=str).fillna('')
    df_arestas = pd.read_csv(ARQ_GRAFO_CHEIO_ARESTAS, dtype=str).fillna('')
    alertas_map = _carregar_alertas_fallback()

    # Metadados originais dos nós e arestas do grafo cheio
    meta_nos = {}
    G_cheio = GrafoMulticamada()
    for _, r in df_nos.iterrows():
        id_no = sanitizar_texto(r['Id'])
        lbl = sanitizar_texto(r['Label'], padrao=id_no)
        cls = sanitizar_texto(r['Classe'])
        desc = sanitizar_texto(r['Descricao']) if 'Descricao' in df_nos.columns else ''
        G_cheio.adicionar_no(id_no, lbl, cls)
        meta_nos[id_no] = {'label': lbl, 'classe': cls, 'descricao': desc}

    meta_arestas = {}
    for _, r in df_arestas.iterrows():
        src = sanitizar_texto(r['Source'])
        tgt = sanitizar_texto(r['Target'])
        tipo = sanitizar_texto(r['Tipo_Relacao'])
        peso = float(pd.to_numeric(r['Weight'], errors='coerce') or 1.0)
        G_cheio.adicionar_aresta(src, tgt, tipo, peso)
        meta_arestas[(src, tgt, tipo)] = {
            'label': sanitizar_texto(r['Label']) if 'Label' in df_arestas.columns else '',
            'descricao': sanitizar_texto(r['Descricao']) if 'Descricao' in df_arestas.columns else '',
            'nivel_risco': sanitizar_texto(r['Nivel_Risco']) if 'Nivel_Risco' in df_arestas.columns else '',
            'motivos_vinculo': sanitizar_texto(r['Motivos_Vinculo']) if 'Motivos_Vinculo' in df_arestas.columns else '',
            'qtd_certames': int(pd.to_numeric(r.get('Qtd_Certames_Comuns'), errors='coerce') or 0),
            'qtd_itens': int(pd.to_numeric(r.get('Qtd_Itens_Comuns'), errors='coerce') or 0),
            'segmento': sanitizar_texto(r.get('Segmento_Objeto')) if 'Segmento_Objeto' in df_arestas.columns else '',
        }

    print(f"Grafo Cheio carregado : {len(G_cheio.nos)} nós | {len(G_cheio.arestas)} arestas")

    # Identifica no próprio grafo as empresas conectadas por Vinculo_Suspeito de alto risco
    empresas_suspeitas = set()
    for u, v, tipo, peso in G_cheio.arestas:
        if tipo == 'Vinculo_Suspeito' and peso >= LIMIAR_SCORE_ALTO_RISCO:
            empresas_suspeitas.add(u)
            empresas_suspeitas.add(v)

    # Passo 1: Algoritmo de Subgrafo Induzido por Arestas — O(V + E)
    G_induzido = G_cheio.subgrafo_induzido_por_arestas(
        lambda u, v, tipo, peso: (
            (tipo == 'Vinculo_Suspeito' and peso >= LIMIAR_SCORE_ALTO_RISCO)
            or (tipo == 'É_Dono_De' and (u in empresas_suspeitas or v in empresas_suspeitas))
        )
    )

    # Passo 2: Algoritmo de Poda 1-Core (remove todos os nós de grau zero) — O(V + E)
    G_reduzido = G_induzido.k_core(k=1)

    # Passo 3: Algoritmo de Componentes Conexas via Union-Find — O(E · α(V))
    componentes = G_reduzido.componentes_conexas(tamanho_minimo=2)
    componentes = sorted(componentes, key=lambda c: (-len(c), sorted(c)[0]))
    nos_validos = set().union(*componentes) if componentes else set()

    comp_por_no = {}
    for idx, comp in enumerate(componentes, 1):
        for u in comp:
            comp_por_no[u] = idx

    # Passo 4: Algoritmo de Listagem de Triângulos Societários (K_3) — O(E · d_max)
    triangulos = G_reduzido.listar_triangulos_societarios()
    nos_em_k3 = set()
    arestas_em_k3 = set()
    for t in triangulos:
        s_id, a_id, b_id = t['Socio_Id'], t['Empresa_A_Id'], t['Empresa_B_Id']
        nos_em_k3.update([s_id, a_id, b_id])
        arestas_em_k3.add(_chave_aresta(a_id, b_id, 'Vinculo_Suspeito'))
        arestas_em_k3.add(_chave_aresta(s_id, a_id, 'É_Dono_De'))
        arestas_em_k3.add(_chave_aresta(s_id, b_id, 'É_Dono_De'))

    # Enriquecimento e exportação dos nós: subgrafos_fraudes_nos.csv
    linhas_nos = []
    for u in sorted(nos_validos):
        lbl = sanitizar_texto(G_reduzido.nos[u]['label'], padrao=u)
        cls = sanitizar_texto(G_reduzido.nos[u]['classe'])
        comp_id = int(comp_por_no[u])
        em_k3 = bool(u in nos_em_k3)
        desc_base = meta_nos.get(u, {}).get('descricao', '') or f"{cls} | {lbl}"
        sufixo = f"Componente: #{comp_id} | Triângulo K3: {'Sim' if em_k3 else 'Não'}"
        desc = desc_base if 'Componente:' in desc_base else f"{desc_base} | {sufixo}"
        linhas_nos.append({
            'Id': u,
            'Label': lbl,
            'Classe': cls,
            'Componente_Id': comp_id,
            'Em_Triangulo_K3': em_k3,
            'Descricao': sanitizar_texto(desc),
        })

    df_sub_nos = pd.DataFrame(
        linhas_nos,
        columns=['Id', 'Label', 'Classe', 'Componente_Id', 'Em_Triangulo_K3', 'Descricao'],
    )

    # Enriquecimento e exportação das arestas: subgrafos_fraudes_arestas.csv
    linhas_arestas = []
    for u, v, tipo, peso in G_reduzido.arestas:
        if u not in nos_validos or v not in nos_validos:
            continue
        comp_id = int(comp_por_no[u])
        em_k3 = bool(_chave_aresta(u, v, tipo) in arestas_em_k3)
        info = meta_arestas.get((u, v, tipo)) or meta_arestas.get((v, u, tipo)) or {}
        label_u = G_reduzido.nos[u]['label']
        label_v = G_reduzido.nos[v]['label']

        nivel_risco = sanitizar_texto(info.get('nivel_risco'))
        motivos = sanitizar_texto(info.get('motivos_vinculo'))
        lbl = sanitizar_texto(info.get('label'))
        desc_base = sanitizar_texto(info.get('descricao'))
        qtd_certames = 0
        qtd_itens = 0
        segmento_obj = ''

        if tipo == 'Vinculo_Suspeito':
            par = tuple(sorted([u, v]))
            al = alertas_map.get(par, {})
            qtd_certames = int(info.get('qtd_certames') or al.get('qtd_certames', 0) or 0)
            qtd_itens = int(info.get('qtd_itens') or al.get('qtd_itens', 0) or 0)
            segmento_obj = sanitizar_texto(info.get('segmento') or al.get('segmento', ''))
            if not nivel_risco:
                nivel_risco = sanitizar_texto(al.get('nivel'), 'ALTO' if peso >= LIMIAR_SCORE_ALTO_RISCO else 'MEDIO')
            if not motivos:
                motivos = sanitizar_texto(al.get('motivos'), 'Vínculo suspeito detectado no cruzamento QSA/cadastral')
            if not lbl:
                lbl = f"Vínculo {nivel_risco} (Score {peso:.2f})"
            if not desc_base:
                desc_base = (
                    f"Vínculo suspeito [{nivel_risco}] entre {label_u} e {label_v} | "
                    f"Score: {peso:.2f} | Motivos: {motivos}"
                )
        else:
            if not lbl:
                lbl = "É Dono De"
            if not desc_base:
                desc_base = f"{label_u} integra o QSA de {label_v}"

        sufixo = f"Componente: #{comp_id} | Triângulo K3: {'Sim' if em_k3 else 'Não'}"
        desc = desc_base if 'Componente:' in desc_base else f"{desc_base} | {sufixo}"

        linhas_arestas.append({
            'Source': u,
            'Target': v,
            'Tipo_Relacao': tipo,
            'Weight': float(peso),
            'Label': sanitizar_texto(lbl),
            'Componente_Id': comp_id,
            'Em_Triangulo_K3': em_k3,
            'Nivel_Risco': nivel_risco,
            'Motivos_Vinculo': motivos,
            'Qtd_Certames_Comuns': qtd_certames,
            'Qtd_Itens_Comuns': qtd_itens,
            'Segmento_Objeto': segmento_obj,
            'Descricao': sanitizar_texto(desc),
        })

    df_sub_arestas = pd.DataFrame(
        linhas_arestas,
        columns=[
            'Source', 'Target', 'Tipo_Relacao', 'Weight', 'Label',
            'Componente_Id', 'Em_Triangulo_K3', 'Nivel_Risco', 'Motivos_Vinculo',
            'Qtd_Certames_Comuns', 'Qtd_Itens_Comuns', 'Segmento_Objeto', 'Descricao',
        ],
    )

    df_sub_nos.to_csv(ARQ_SUBGRAFO_NOS, index=False, encoding='utf-8')
    df_sub_arestas.to_csv(ARQ_SUBGRAFO_ARESTAS, index=False, encoding='utf-8')

    # Exportação GEXF nativo do Gephi (subgrafos_fraudes.gexf)
    G_sub_nx = nx.MultiGraph()
    for _, r in df_sub_nos.iterrows():
        cls = sanitizar_texto(r['Classe'])
        em_k3 = bool(r['Em_Triangulo_K3'])
        if cls == 'Empresa':
            cor = {'r': 214, 'g': 39, 'b': 40, 'a': 1.0} if em_k3 else {'r': 31, 'g': 119, 'b': 180, 'a': 1.0}
            tam = 24.0 if em_k3 else 18.0
        elif cls in ('Sócio Real', 'Sócio'):
            cor = {'r': 255, 'g': 127, 'b': 14, 'a': 1.0} if em_k3 else {'r': 255, 'g': 187, 'b': 120, 'a': 1.0}
            tam = 18.0 if em_k3 else 13.0
        else:
            cor = {'r': 44, 'g': 160, 'b': 44, 'a': 1.0}
            tam = 20.0

        G_sub_nx.add_node(
            sanitizar_texto(r['Id']),
            label=sanitizar_texto(r['Label']),
            classe=cls,
            componente_id=int(r['Componente_Id']),
            em_triangulo_k3=em_k3,
            descricao=sanitizar_texto(r['Descricao']),
            viz={'color': cor, 'size': tam},
        )

    for _, r in df_sub_arestas.iterrows():
        tipo = sanitizar_texto(r['Tipo_Relacao'])
        em_k3 = bool(r['Em_Triangulo_K3'])
        if tipo == 'Vinculo_Suspeito':
            cor_aresta = {'r': 214, 'g': 39, 'b': 40, 'a': 1.0} if em_k3 else {'r': 230, 'g': 85, 'b': 13, 'a': 1.0}
        else:
            cor_aresta = {'r': 255, 'g': 127, 'b': 14, 'a': 0.95} if em_k3 else {'r': 127, 'g': 127, 'b': 127, 'a': 0.85}

        G_sub_nx.add_edge(
            sanitizar_texto(r['Source']),
            sanitizar_texto(r['Target']),
            key=tipo,
            label=sanitizar_texto(r['Label']),
            tipo_relacao=tipo,
            weight=float(r['Weight']),
            componente_id=int(r['Componente_Id']),
            em_triangulo_k3=em_k3,
            nivel_risco=sanitizar_texto(r['Nivel_Risco']),
            motivos_vinculo=sanitizar_texto(r['Motivos_Vinculo']),
            qtd_certames_comuns=int(r['Qtd_Certames_Comuns']),
            qtd_itens_comuns=int(r['Qtd_Itens_Comuns']),
            segmento_objeto=sanitizar_texto(r['Segmento_Objeto']),
            descricao=sanitizar_texto(r['Descricao']),
            viz={'color': cor_aresta},
        )

    nx.write_gexf(G_sub_nx, ARQ_SUBGRAFO_GEXF, encoding='utf-8')

    print(f"Subgrafo Reduzido     : {len(df_sub_nos)} nós | {len(df_sub_arestas)} arestas")
    print(f"Componentes Conexas   : {len(componentes)} núcleos de conluio isolados")
    print(f"Triângulos K_3        : {len(triangulos)} triângulos societários fechados")
    for i, t in enumerate(triangulos, 1):
        print(f"  [K_3 #{i}] {t['Socio']} -> ({t['Empresa_A']} <-> {t['Empresa_B']}) [Score={t['Score_Vinculo']}]")

    print("\nEtapa 3 concluída! Planilhas e GEXF gerados com sucesso:")
    print(f"  -> {ARQ_SUBGRAFO_NOS}")
    print(f"  -> {ARQ_SUBGRAFO_ARESTAS}")
    print(f"  -> {ARQ_SUBGRAFO_GEXF} ({G_sub_nx.number_of_nodes()} nós | {G_sub_nx.number_of_edges()} arestas)")


if __name__ == '__main__':
    main()
