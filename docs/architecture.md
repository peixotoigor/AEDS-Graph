# Arquitetura do Sistema AEDS-Graph

## 1. Visão Arquitetural

O **AEDS-Graph** adota uma arquitetura em camadas orientada a dados (*data pipeline architecture*), separando estritamente a ingestão de dados brutos, a persistência intermediária, a modelagem de grafos e a camada de detecção de anomalias periciais.

```text
┌───────────────────────────┐
│ database/2025/raw/        │ 55 tabelas CSV brutas do SICOM/TCE-MG
│ (Módulos 1 a 5)           │ (Somente Leitura / Imutável)
└─────────────┬─────────────┘
              │ Polars ETL (limpeza, tipagem e deduplicação)
              ▼
┌───────────────────────────┐
│ database/2025/processed/  │ Artefatos intermediários padronizados
│ nodes.parquet & edges.*   │ (Leveza, alta compressão e velocidade)
└─────────────┬─────────────┘
              │ Graph Builder (src/graph/)
              ▼
┌───────────────────────────┐
│ Grafo Heterogêneo         │ NetworkX MultiDiGraph em memória
│ Multicamadas (V, E)       │ Representação formal de entidades e relações
└─────────────┬─────────────┘
              │ Detectores Modulares (src/detectors/)
              ▼
┌────────────────────────────────────────────────────────┐
│ Camada de Saída & Relatórios (outputs/)                │
│ 1. Arquivos .gexf para visualização pericial no Gephi  │
│ 2. Relatórios executivos em Markdown e JSON estruturado│
└────────────────────────────────────────────────────────┘
```

---

## 2. Topologia do Grafo Heterogêneo

### 2.1. Tipos de Nós ($V$)
| Tipo de Nó | Identificador Único | Atributos Principais | Tabela de Origem |
| :--- | :--- | :--- | :--- |
| `Orgao` | `codOrgao` ou `codUnidade` | `nomeOrgao`, `sigla`, `tipoEsfera` | `orgao.csv`, `orgaoUnidade.csv` |
| `Licitacao` | `codOrgao_nroProcesso_exercicio` | `modalidade`, `objeto`, `dataHomologacao`, `vlrHomologado` | `licitacao.csv`, `dispensa.csv` |
| `Empresa` | `nroCnpjCpf` | `razaoSocial`, `nomeFantasia`, `municipio`, `uf` | `credorEmpenho.csv`, `habLicitacao.csv` |
| `Socio` | `cpfSocio` | `nomeSocio`, `tipoParticipacao` | `quadroSocLicitacao.csv` |

### 2.2. Tipos de Arestas ($E$)
| Relação | Origem ($u$) | Destino ($v$) | Direcionamento | Atributos e Pesos |
| :--- | :--- | :--- | :--- | :--- |
| `DISPUTOU` | `Empresa` | `Licitacao` | Direcionada | `vlrProposta`, `statusJulgamento`, `desclassificada` |
| `VENCEU` | `Empresa` | `Licitacao` | Direcionada | `vlrHomologado`, `posicao` |
| `SOCIO_DE` | `Socio` | `Empresa` | Direcionada | `percentualCapital`, `dataEntrada` |
| `CONTRATOU` | `Orgao` | `Empresa` | Direcionada | `nroContrato`, `valorInicial`, `vigencia` |
| `PAGOU` | `Orgao` | `Empresa` | Direcionada | `vlrTotalPago` (soma liquidada e paga no ano) |

---

## 3. Chaves de Cruzamento dos Módulos SICOM/TCE-MG

O cruzamento relacional entre as tabelas brutas requer atenção às chaves compostas definidas pelo Tribunal de Contas:

1. **Processos Licitatórios Regulares:**
   - Chave primária: `codOrgao` + `nroProcessoLicitatorio` + `exercicioLicitacao`.
   - Vínculo com julgamento e participantes: `julgLicitacao.csv` e `habLicitacao.csv`.
   - Vínculo com quadro societário: `quadroSocLicitacao.csv` via `nroInscricao` (CNPJ do participante).
2. **Contratos e Instrumentos:**
   - Chave de ligação com a licitação: `nroProcessoLicitatorio` + `exercicioLicitacao` + `codOrgao`.
   - Identificação do fornecedor: `nroDocumento` (CNPJ/CPF do contratado).
3. **Execução Orçamentária e Pagamentos:**
   - Chave do empenho: `codOrgao` + `codUnidade` + `nroEmpenho` + `exercicioEmpenho`.
   - Credor: `credorEmpenho.csv` via `nroCnpjCpfCredor`.
   - Vínculo com liquidação e notas fiscais: `liquidacao.csv` e `liquidacaoNfs.csv`.
   - Movimentação bancária final: `pagamento.csv` e `movPagamento.csv`.

---

## 4. Estrutura Modular do Código (`src/`)

```text
src/
├── __init__.py
├── config.py                 # Parâmetros gerais (exercício fiscal, caminhos, código IBGE)
├── etl/
│   ├── __init__.py
│   ├── loaders.py            # Leitura otimizada de CSVs com Polars (detecção de encoding/delimiter)
│   ├── processors.py         # Tratamento de CNPJ/CPF, valores monetários e normalização
│   └── builder_tables.py     # Criação de nós e arestas em formato Parquet
├── graph/
│   ├── __init__.py
│   ├── loader.py             # Instanciação do NetworkX MultiDiGraph a partir do Parquet
│   ├── projections.py        # Projeções monopartidas (ex: rede de co-ocorrência Empresa-Empresa)
│   └── exporter.py           # Serialização do grafo em formato .gexf (Gephi)
├── detectors/
│   ├── __init__.py
│   ├── base.py               # Interface base abstrata para detectores de anomalias
│   ├── shared_partners.py    # Detector de concorrentes na mesma licitação com sócios comuns
│   ├── cover_bidding.py      # Detector de co-ocorrência repetida e suspeita de rodízio de lances
│   └── concentration.py      # Métricas de dependência orçamentária e centralidade
└── reports/
    ├── __init__.py
    ├── summary.py            # Consolidação das anomalias em dataframes estruturados
    └── writers.py            # Exportadores em Markdown pericial e JSON
```

---

## 5. Princípios de Engenharia de Software Adotados

1. **Separação Rígida de Responsabilidades:**
   - O módulo de ETL nunca manipula instâncias de grafos. Ele gera tabelas limpas.
   - O construtor de grafos não conhece a lógica pericial de detecção. Ele apenas monta a topologia.
   - Os detectores recebem o grafo pronto e retornam registros de anomalias.
2. **Interface Base Plugável para Detectores:**
   - Todos os detectores em `src/detectors/` herdam de `BaseDetector`, permitindo testar e plugar novas heurísticas exploradas previamente em `scripts/DA.ipynb`.
3. **Eficiência e Memória:**
   - Polars garante processamento colunar vetorizado para as tabelas de milhões de linhas (`pagamento.csv`, `liquidacao.csv`), reservando a memória para a rede no NetworkX.
