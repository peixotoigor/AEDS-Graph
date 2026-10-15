# Estilo e Convenções de Código

## 1. Padrões Gerais de Linguagem (Python)

O código de produção em `src/` deve seguir os padrões modernos do ecossistema Python (PEP 8, compatível com Python 3.10+):

- **Tipagem Estática Obrigatória (`typing`):**
  - Todas as assinaturas de funções e métodos públicos devem conter anotações completas de tipos nos parâmetros e no retorno.
  - Exemplo:
    ```python
    import polars as pl
    import networkx as nx
    from typing import Dict, Any, List, Optional

    def build_bipartite_network(
        nodes_df: pl.DataFrame,
        edges_df: pl.DataFrame
    ) -> nx.MultiDiGraph:
        """Constrói um grafo heterogêneo direcionado a partir de nós e arestas.
        
        Args:
            nodes_df: DataFrame Polars com colunas ['id', 'label', 'type', 'attributes'].
            edges_df: DataFrame Polars com colunas ['source', 'target', 'relation', 'weight'].
            
        Returns:
            Instância do grafo heterogêneo MultiDiGraph do NetworkX.
            
        Complexity:
            Tempo: O(V + E) onde V é o número de nós e E é o número de arestas.
            Espaço: O(V + E) para armazenamento das listas de adjacência.
        """
        ...
    ```

- **Docstrings Didáticas e Complexidade Assintótica:**
  - Como se trata de um projeto acadêmico de Algoritmos e Estruturas de Dados (AEDS), toda função analítica ou de transformação de grafos **deve explicitar sua complexidade assintótica de tempo e espaço** na docstring.
  - Comentários no corpo da função devem explicar a intuição do algoritmo ou a justificativa pericial do cruzamento de dados.

---

## 2. Tratamento Seguro de Dados Fiscais e Governamentais

1. **Documentos de Identificação (CNPJ e CPF):**
   - Remova pontuações, barras e traços (`.`, `-`, `/`), preservando apenas os dígitos (`[0-9]`).
   - Garanta o preenchimento de zeros à esquerda quando o CSV tiver truncado números (`zfill(14)` para CNPJ e `zfill(11)` para CPF).
   - Suporte e respeite registros que apresentem mascaramento parcial legal (ex: `***.123.456-**`).
2. **Valores Monetários e Numéricos:**
   - Converta strings de valores com formatação brasileira (separador de milhar `.` e decimal `,`) para `float` padrão IEEE 754 de forma determinística:
     ```python
     def parse_brazilian_currency(val: str) -> float:
         if not val or val.strip() == "":
             return 0.0
         return float(val.replace(".", "").replace(",", "."))
     ```
3. **Datas e Séries Temporais:**
   - Padronize datas no formato ISO-8601 (`YYYY-MM-DD`) para viabilizar ordenação cronológica e cálculo de janelas temporais de certames.

---

## 3. Diretrizes de Modularidade e Funções Puras

- **Funções Puras no ETL:**
  - Funções de processamento devem receber DataFrames e configurações explicitamente, retornando novos DataFrames sem efeitos colaterais globais.
- **Evitar Variáveis Globais de Estado:**
  - Não armazene o grafo em variáveis globais de módulo. Passe o grafo instanciado como argumento para as rotinas de detecção e exportação.
- **Tratamento de Nulos:**
  - O SICOM apresenta diversas colunas nulas em virtude de dispensas de licitação ou processos cancelados. Sempre defina um comportamento padrão seguro (`null_strategy`) em vez de permitir exceções silenciosas.
