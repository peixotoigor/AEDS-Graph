"""
ETAPA 3: Redução Algorítmica do Grafo Cheio para o Subgrafo de Fraudes
======================================================================

Entrada (gerada pelo enriquecimento_socios.py):
  - resultados/grafo_cheio_nos.csv
  - resultados/grafo_cheio_arestas.csv

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
  - resultados/subgrafos_fraudes_nos.csv
  - resultados/subgrafos_fraudes_arestas.csv
"""

import os
from collections import defaultdict, deque
import pandas as pd

PASTA_DESTINO = 'resultados'
os.makedirs(PASTA_DESTINO, exist_ok=True)
ARQ_GRAFO_CHEIO_NOS = os.path.join(PASTA_DESTINO, 'grafo_cheio_nos.csv')
ARQ_GRAFO_CHEIO_ARESTAS = os.path.join(PASTA_DESTINO, 'grafo_cheio_arestas.csv')

ARQ_SUBGRAFO_NOS = os.path.join(PASTA_DESTINO, 'subgrafos_fraudes_nos.csv')
ARQ_SUBGRAFO_ARESTAS = os.path.join(PASTA_DESTINO, 'subgrafos_fraudes_arestas.csv')

LIMIAR_SCORE_ALTO_RISCO = 2.0


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
                        'Socio': self.nos[s]['label'],
                        'Empresa_A': self.nos[u]['label'],
                        'Empresa_B': self.nos[v]['label'],
                        'Score_Vinculo': peso,
                    })
        return triangulos


# =========================================================================
# 3. EXECUÇÃO DA REDUÇÃO E EXPORTAÇÃO DE "subgrafos_fraudes"
# =========================================================================
def main():
    if not os.path.exists(ARQ_GRAFO_CHEIO_NOS) or not os.path.exists(ARQ_GRAFO_CHEIO_ARESTAS):
        raise FileNotFoundError(
            "Grafo cheio não encontrado! Execute primeiro: python enriquecimento_socios.py"
        )

    df_nos = pd.read_csv(ARQ_GRAFO_CHEIO_NOS, dtype=str)
    df_arestas = pd.read_csv(ARQ_GRAFO_CHEIO_ARESTAS, dtype=str)

    G_cheio = GrafoMulticamada()
    for _, r in df_nos.iterrows():
        G_cheio.adicionar_no(r['Id'], r['Label'], r['Classe'])
    for _, r in df_arestas.iterrows():
        G_cheio.adicionar_aresta(r['Source'], r['Target'], r['Tipo_Relacao'], float(r['Weight']))

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
    nos_validos = set().union(*componentes) if componentes else set()

    # Passo 4: Algoritmo de Listagem de Triângulos Societários (K_3) — O(E · d_max)
    triangulos = G_reduzido.listar_triangulos_societarios()

    # Exportação das planilhas finais: subgrafos_fraudes_nos.csv e subgrafos_fraudes_arestas.csv
    df_sub_nos = pd.DataFrame([
        {'Id': u, 'Label': G_reduzido.nos[u]['label'], 'Classe': G_reduzido.nos[u]['classe']}
        for u in sorted(nos_validos)
    ])
    df_sub_arestas = pd.DataFrame([
        {'Source': u, 'Target': v, 'Tipo_Relacao': tipo, 'Weight': peso}
        for u, v, tipo, peso in G_reduzido.arestas
        if u in nos_validos and v in nos_validos
    ])

    df_sub_nos.to_csv(ARQ_SUBGRAFO_NOS, index=False, encoding='utf-8')
    df_sub_arestas.to_csv(ARQ_SUBGRAFO_ARESTAS, index=False, encoding='utf-8')

    print(f"Subgrafo Reduzido     : {len(df_sub_nos)} nós | {len(df_sub_arestas)} arestas")
    print(f"Componentes Conexas   : {len(componentes)} núcleos de conluio isolados")
    print(f"Triângulos K_3        : {len(triangulos)} triângulos societários fechados")
    for i, t in enumerate(triangulos, 1):
        print(f"  [K_3 #{i}] {t['Socio']} -> ({t['Empresa_A']} <-> {t['Empresa_B']}) [Score={t['Score_Vinculo']}]")

    print("\nEtapa 3 concluída! Planilhas geradas com sucesso:")
    print(f"  -> {ARQ_SUBGRAFO_NOS}")
    print(f"  -> {ARQ_SUBGRAFO_ARESTAS}")


if __name__ == '__main__':
    main()

