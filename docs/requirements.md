# Requisitos do Projeto AEDS-Graph

## 1. Visão Geral e Contexto Acadêmico
O projeto **AEDS-Graph** investiga a aplicação prática de Teoria dos Grafos para análise de dados abertos de contratações públicas e execução orçamentária do município de Divinópolis (MG), código SICOM/IBGE `3122306`, referente ao exercício fiscal de 2025 consolidado.

### Pergunta Central Norteadora
> *"Como a análise de grafos pode ser utilizada para identificar padrões anômalos e indicadores de risco nas relações entre municípios, empresas fornecedoras e recursos públicos?"*

---

## 2. Objetivos

### Objetivo Geral
Desenvolver uma estrutura computacional baseada em grafos para modelar e analisar as relações comerciais entre a administração municipal e empresas privadas fornecedoras, identificando padrões de concentração, recorrência e conectividade que constituam indicadores periciais de risco.

### Objetivos Específicos
1. **Estruturar Pipeline de ETL:** Ingerir e tratar 55 tabelas CSV do SICOM/TCE-MG (módulos `orgao`, `licitacao`, `contrato`, `empenho`, `despesa`) usando a biblioteca **Polars**, gerando listas de nós e arestas padronizadas em Parquet.
2. **Modelar Grafo Heterogêneo:** Construir uma representação em rede multicamadas com a biblioteca **NetworkX**, integrando órgãos públicos, certames licitatórios, empresas e quadros societários.
3. **Desenvolver Heurísticas de Risco:** Criar detectores modulares para os três eixos periciais de anomalias:
   - **Padrões de Conectividade e Cartéis (Foco Prioritário):** Vínculos societários compartilhados em certames comuns e suspeitas de propostas de cobertura (*cover bidding*).
   - **Padrões de Concentração e Monopólios:** Dependência orçamentária de secretarias e dominância econômica de fornecedores.
   - **Padrões de Recorrência e Fracionamento:** Sucessão atípica de dispensas de licitação (Lei 14.133/2021).
4. **Exportação e Comunicação Visual:** Exportar subgrafos anômalos no formato `.gexf` para visualização pericial no **Gephi** e relatórios estruturados em Markdown e JSON.

---

## 3. Entregáveis do Projeto

- **Código-Fonte de Produção (`src/`):** Módulos Python documentados, desacoplados e testáveis (`etl`, `graph`, `detectors`, `reports`).
- **Laboratório Exploratório (`scripts/DA.ipynb`):** Jupyter Notebook documentando as hipóteses periciais, análises exploratórias preliminares e validação de cruzamento de chaves.
- **Artefatos Processados (`database/2025/processed/`):** Datasets limpos em formato Parquet (`nodes.parquet`, `edges.parquet`).
- **Exportações para Gephi (`outputs/*.gexf`):** Redes formatadas com atributos de nós e arestas para renderização pericial.
- **Relatório Pericial de Auditoria (`outputs/*.md`, `outputs/*.json`):** Resumo executivo contendo scores de risco, comunidades de empresas suspeitas e métricas de centralidade.
- **Suíte de Testes Automatizados (`tests/`):** Testes unitários com `pytest` cobrindo integridade de schemas e invariantes topológicos do grafo.

---

## 4. Critérios de Qualidade e Restrições

1. **Rigor e Linguagem Pericial:**
   - O projeto classifica situações atípicas como "indicadores de risco", evitando afirmações categóricas de dolo ou fraude jurídica.
2. **Reprodutibilidade:**
   - Qualquer analista deve ser capaz de clonar o repositório, executar o pipeline de ponta a ponta e reproduzir exatamente os mesmos grafos e métricas.
3. **Desacoplamento e Didática:**
   - O código deve priorizar a clareza didática, sendo adequado para apresentação acadêmica na disciplina de Algoritmos e Estruturas de Dados (AEDS).
4. **Eficiência Algorítmica:**
   - As consultas e algoritmos de detecção devem ser implementados considerando a complexidade assintótica $O(V + E)$ em relação ao tamanho da base.
