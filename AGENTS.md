# AGENTS.md — Guia Operacional do Projeto AEDS-Graph

## 1. Visão Geral e Contexto Acadêmico
O **AEDS-Graph** é uma estrutura computacional baseada em Teoria dos Grafos para modelagem, rastreamento e análise pericial das relações comerciais entre a administração pública do município de Divinópolis (código IBGE/SICOM `3122306`) e empresas privadas, com base no exercício fiscal de 2025.

### Questão Central do Projeto
> *"Como a análise de grafos pode ser utilizada para identificar padrões anômalos e indicadores de risco nas relações entre municípios, empresas fornecedoras e recursos públicos?"*

### Metodologia de Construção Passo a Passo
O projeto adota uma metodologia evolutiva e rigorosamente modular:
1. **Laboratório de Hipóteses (`scripts/DA.ipynb`):** Análise exploratória de dados (EDA), inspeção de esquemas das tabelas e validação preliminar de regras periciais e cruzamentos de chaves.
2. **Engenharia de Produção (`src/`):** Construção desacoplada de pipelines reutilizáveis em Python (`etl`, `graph`, `detectors`, `reports`), onde cada módulo deve ser compreensível isoladamente para fins acadêmicos e periciais.

---

## 2. Mapa de Navegação de Contexto (Leia sob demanda)
Para otimizar o uso do contexto, **NÃO carregue todos os arquivos de documentação simultaneamente**. Consulte a documentação técnica específica conforme a demanda da sua tarefa:

- 📋 **Requisitos, Domínio Pericial e Metas:** Leia [docs/requirements.md](file:///C:/Users/igorp/OneDrive/Arquivos%20Antigos/%C3%81rea%20de%20Trabalho/Projetos_26_2/AEDS-Graph/docs/requirements.md)
- 🏗️ **Arquitetura do Grafo, ETL e Esquema SICOM:** Leia [docs/architecture.md](file:///C:/Users/igorp/OneDrive/Arquivos%20Antigos/%C3%81rea%20de%20Trabalho/Projetos_26_2/AEDS-Graph/docs/architecture.md)
- 🐍 **Convenções de Código, Tipagem e Estilo:** Leia [docs/coding-style.md](file:///C:/Users/igorp/OneDrive/Arquivos%20Antigos/%C3%81rea%20de%20Trabalho/Projetos_26_2/AEDS-Graph/docs/coding-style.md)
- ⚙️ **Ambiente Virtual, Dependências e Execução:** Leia [docs/development.md](file:///C:/Users/igorp/OneDrive/Arquivos%20Antigos/%C3%81rea%20de%20Trabalho/Projetos_26_2/AEDS-Graph/docs/development.md)
- 🧪 **Testes de Invariantes de Grafos e Validação de Dados:** Leia [docs/testing.md](file:///C:/Users/igorp/OneDrive/Arquivos%20Antigos/%C3%81rea%20de%20Trabalho/Projetos_26_2/AEDS-Graph/docs/testing.md)

---

## 3. Diretórios de Trabalho e Organização

```text
AEDS-Graph/
├── database/
│   └── 2025/
│       ├── raw/                 # SOMENTE LEITURA. 55 tabelas brutas do SICOM/TCE-MG
│       │   ├── SICOM.2025.3122306.orgao/
│       │   ├── SICOM.2025.3122306.licitacao/
│       │   ├── SICOM.2025.3122306.contrato/
│       │   ├── SICOM.2025.3122306.empenho/
│       │   └── SICOM.2025.3122306.despesa/
│       └── processed/           # Tabelas limpas e artefatos intermediários (Parquet)
├── scripts/
│   └── DA.ipynb                 # Laboratório exploratório (EDA e testes de hipóteses)
├── src/                         # Código de produção estritamente modular
│   ├── etl/                     # Ingestão, limpeza e modelagem de nós/arestas (Polars)
│   ├── graph/                   # Construção do grafo heterogêneo (NetworkX) e exportação .gexf
│   ├── detectors/               # Heurísticas de detecção de risco (conluio, rodízio, monopólio)
│   └── reports/                 # Geração de relatórios analíticos (Markdown/JSON)
├── tests/                       # Testes automatizados de ETL e invariantes de grafos (pytest)
├── docs/                        # Documentação técnica e arquitetural de referência
├── outputs/                     # Relatórios de auditoria e grafos .gexf para Gephi
├── requirements.txt             # Dependências oficiais (polars, networkx, pyvis, etc.)
└── AGENTS.md                    # Este guia operacional mestre
```

---

## 4. Estrutura do Grafo e Base de Dados SICOM/TCE-MG

### 4.1. Topologia do Grafo Heterogêneo Multicamadas
O sistema modela contratações públicas como uma rede heterogênea:
- **Tipos de Nós ($V$):**
  - `Orgao`: Secretarias e unidades orçamentárias municipais (`codOrgao`, `codUnidadeOrcamentaria`).
  - `Licitacao`: Processos licitatórios regulares e dispensas (`nroProcessoLicitatorio`, `exercicioLicitacao`).
  - `Empresa`: Pessoas jurídicas concorrentes e contratadas (`nroCnpjCpf`).
  - `Socio`: Pessoas físicas e sócios-administradores (`cpfSocio`, `nomeSocio`).
- **Tipos de Arestas ($E$):**
  - `DISPUTOU`: Direcionada `Empresa -> Licitacao` (com atributos de proposta e habilitação).
  - `VENCEU`: Direcionada `Empresa -> Licitacao` (com valor homologado).
  - `SOCIO_DE`: Direcionada `Socio -> Empresa` (extraída de `quadroSocLicitacao`).
  - `CONTRATOU`: Direcionada `Orgao -> Empresa` (vinculada a contratos formalizados).
  - `EMPENHOU_PAGOU`: Direcionada `Orgao -> Empresa` (com peso acumulado em R$ liquidado/pago).

### 4.2. Os 5 Módulos SICOM
1. `orgao` (4 tabelas): Identificação e estrutura formal das secretarias e ordenadores.
2. `licitacao` (24 tabelas): Certames, itens, cotações, julgamentos, dispensas e quadro societário.
3. `contrato` (8 tabelas): Instrumentos jurídicos, aditivos e rescisões.
4. `empenho` (8 tabelas): Reserva orçamentária e vinculação de credores.
5. `despesa` (11 tabelas): Execução financeira (liquidação, notas fiscais e ordens de pagamento).

---

## 5. Regras de Ouro Inegociáveis

1. **Imutabilidade Absoluta dos Dados Brutos:**
   - NUNCA altere, renomeie, sobrescreva ou delete qualquer arquivo dentro de `database/2025/raw/`. Toda escrita deve ser direcionada para `database/2025/processed/` ou `outputs/`.
2. **Inspeção Prévia de Delimitadores e Encodings:**
   - Antes de carregar um CSV do SICOM no pipeline, inspecione as primeiras linhas (`head -n 5`) para validar o delimitador (comumente `;` ou `,`) e codificação (`utf-8` ou `latin1`/`iso-8859-1`).
3. **Modularidade e Compreensão Didática:**
   - Evite monólitos ou scripts gigantescos. Cada transformação ou algoritmo deve ser encapsulado em funções puras, testáveis e acompanhadas de docstrings explicativas.
4. **Parametrização Agnóstica a Ano e Município:**
   - Não fixe valores como `2025` ou `3122306` hardcoded no núcleo de processamento. Use configurações ou parâmetros padronizados com valores default para viabilizar reuso futuro em outros municípios e exercícios fiscais.
5. **Rigor e Prudência Pericial:**
   - As anomalias computacionais encontradas nos grafos devem ser tratadas formalmente como **"indicadores de risco"**, **"alertas periciais"** ou **"padrões de conectividade atípicos"**, e nunca como "crimes", "fraudes confirmadas" ou julgamentos de má-fé.
6. **Controle de Complexidade Assintótica:**
   - Toda operação sobre a estrutura do grafo deve documentar sua complexidade assintótica de tempo e espaço $O(V + E)$ nas docstrings e na documentação técnica.