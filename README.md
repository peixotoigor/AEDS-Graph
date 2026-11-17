# Detecção de Conluio e Concorrência Simulada em Contratações Públicas Municipais via Grafos Heterogêneos Multicamada

Pipeline computacional em Python para modelagem e mineração de redes heterogêneas multicamada aplicadas à auditoria de compras públicas municipais, combinando registros de licitações do **SICOM/TCE-MG** (estudo empírico em Divinópolis/MG, exercício de 2025) com dados do **Quadro de Sócios e Administradores (QSA)** da Receita Federal via **BrasilAPI**.

---

## Sumário

- [Visão Geral da Metodologia](#visão-geral-da-metodologia)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pré-requisitos (Ubuntu / Linux)](#pré-requisitos-ubuntu--linux)
- [Como Usar o Makefile](#como-usar-o-makefile)
- [Arquivos Gerados (`resultados/`)](#arquivos-gerados-resultados)
- [Síntese dos Resultados Empíricos](#síntese-dos-resultados-empíricos)
- [Nota Ética e LGPD](#nota-ética-e-lgpd)

---

## Visão Geral da Metodologia

O projeto executa um pipeline sequencial em **3 etapas**:

1. **Etapa 1 — Higienização e Grafo Base (`data_cleaning.py`)**
   - Lê as tabelas do SICOM/TCE-MG em `arquivos_originais/` (`licitacao`, `habLicitacao`, `quadroSocLicitacao`, `julgLicitacao`).
   - Recupera CNPJs/CPFs corrompidos por notação científica (ex.: `2.71E+13`) e restaura zeros à esquerda (14 dígitos para CNPJ e 11 para CPF).
   - Constrói as relações `Participou_Licitacao` (Empresa $\leftrightarrow$ Órgão) e a projeção de disputa `Concorreu_Contra` (Empresa $\leftrightarrow$ Empresa na mesma licitação e nos mesmos itens julgados).

2. **Etapa 2 — Enriquecimento Societário via BrasilAPI e Grafo Completo (`enriquecimento_socios.py`)**
   - Supera a supressão de CPFs/nomes da tabela `quadroSocLicitacao.csv` consultando os 674 CNPJs na BrasilAPI (`https://brasilapi.com.br/api/cnpj/v1/{cnpj}`), com controle de vazão (*rate limiting*) e cache persistente em `resultados/cache_qsa_brasilapi.json`.
   - Recupera sócios pessoas físicas, pessoas jurídicas (holdings) e titulares de MEI/EI.
   - Calcula um **Escore de Vínculo** entre pares de concorrentes (`Concorreu_Contra`):
     - Sócio em comum: `+10,00` por sócio
     - Mesma raiz de CNPJ (8 primeiros dígitos): `+10,00`
     - Mesmo endereço normalizado: `+10,00`
     - Mesmo telefone normalizado: `+8,00`
     - Mesmo e-mail corporativo: `+5,00`
     - Sobrenome raro em comum: `+1,00`
     - Sobrenome comum em comum (lista de 53 sobrenomes muito frequentes no Brasil): `+0,25`
   - Classifica cada par em nível **`ALTO`**, **`MEDIO`** ou **`BAIXO`** e monta o **Grafo Cheio** (`grafo_cheio_nos.csv` e `grafo_cheio_arestas.csv`, incluindo arestas `Vinculo_Suspeito` de níveis `MEDIO` e `ALTO`).

3. **Etapa 3 — Redução Algorítmica e Detecção de Núcleos de Conluio (`reduzir_grafo.py`)**
   - Carrega o grafo completo em uma estrutura de **Lista de Adjacência** (`GrafoMulticamada`) e aplica quatro algoritmos clássicos em grafos:
     1. **Subgrafo Induzido por Arestas** — $O(V + E)$: mantém apenas arestas `Vinculo_Suspeito` com `Score >= 2,0` e as arestas societárias `É_Dono_De` das empresas envolvidas.
     2. **Decomposição *1-Core* via BFS** — $O(V + E)$: remove vértices isolados (grau zero).
     3. **Componentes Conexas via *Union-Find*** (com *Path Compression* e *Union by Rank*) — $O(E \cdot \alpha(V))$: isola as componentes independentes de alto risco ($|C_i| \ge 2$).
     4. **Listagem de Triângulos Societários ($K_3$)** — $O(E \cdot d_{\max})$: identifica ciclos fechados (*Sócio $\to$ Empresa A $\leftrightarrow$ Empresa B $\leftarrow$ Sócio*).

---

## Estrutura do Projeto

```text
.
├── arquivos_originais/          # Planilhas CSV originais do SICOM/TCE-MG (2025)
├── data_cleaning.py             # Etapa 1: limpeza cadastral e grafo base
├── enriquecimento_socios.py     # Etapa 2: consultas BrasilAPI, escores e grafo cheio
├── reduzir_grafo.py             # Etapa 3: redução por 1-Core, Union-Find e K_3
├── Makefile                     # Automação de execução e limpeza no Ubuntu/Linux
├── requirements.txt             # Dependências Python (pandas e numpy)
├── .gitignore                   # Ignora resultados/, .venv/, documentacao/, etc.
└── resultados/                  # Gerado automaticamente ao executar o pipeline
```

---

## Pré-requisitos (Ubuntu / Linux)

- **Python 3** (com `venv`)
- **GNU Make**
- **Acesso à internet** (necessário na Etapa 2 caso `resultados/cache_qsa_brasilapi.json` ainda não exista)

Em uma instalação limpa do Ubuntu (22.04 / 24.04+), instale os pacotes básicos do sistema uma única vez:

```bash
sudo apt update && sudo apt install -y make python3 python3-venv
```

> O `Makefile` utiliza um ambiente virtual isolado (`.venv/`) automaticamente, evitando conflitos com a política PEP 668 (`externally-managed-environment`) das versões recentes do Ubuntu.

---

## Como Usar o Makefile

Execute os comandos sempre na **raiz do repositório**:

### Executar o pipeline completo
```bash
make run
```
*(Ou simplesmente `make`.)*  
Esse comando:
1. Cria o ambiente virtual `.venv/` (caso ainda não exista);
2. Instala as dependências de `requirements.txt` (`pandas>=2.0.0`, `numpy>=1.24.0`);
3. Executa sequencialmente `data_cleaning.py`, `enriquecimento_socios.py` e `reduzir_grafo.py`.

### Limpar arquivos gerados
```bash
make clean
```
Apaga completamente a pasta `resultados/` e os caches `__pycache__/`.

### Outros alvos disponíveis

| Comando | O que faz |
|---|---|
| `make setup` | Apenas cria `.venv/` e instala as dependências de `requirements.txt`. |
| `make step1` | Executa somente a Etapa 1 (`data_cleaning.py`). |
| `make step2` | Executa somente a Etapa 2 (`enriquecimento_socios.py`). |
| `make step3` | Executa somente a Etapa 3 (`reduzir_grafo.py`). |
| `make clean-csv` | Remove apenas `resultados/*.csv`, **mantendo** `cache_qsa_brasilapi.json` (evita refazer as ~674 consultas à API ao testar alterações). |
| `make distclean` | Executa `make clean` e remove também o ambiente virtual `.venv/`. |
| `make help` | Lista todos os comandos disponíveis no terminal. |

> **Observação ao migrar do Windows para o Ubuntu:** caso você copie a pasta diretamente de um computador Windows (em vez de clonar pelo Git) e já exista uma `.venv/` do Windows no diretório, rode `make distclean && make run` para recriar o ambiente virtual compatível com Linux.

---

## Arquivos Gerados (`resultados/`)

| Arquivo | Etapa | Descrição |
|---|---|---|
| `tabela_nos_gephi.csv` / `tabela_arestas_gephi.csv` | Etapa 1 | Grafo inicial antes do enriquecimento (com sócios ainda anonimizados pelo SICOM). |
| `cache_qsa_brasilapi.json` | Etapa 2 | Cache local das respostas da BrasilAPI por CNPJ. |
| `socios_reais.csv` | Etapa 2 | Quadro de sócios e titulares recuperado para as empresas participantes. |
| `alertas_vinculos_concorrentes.csv` | Etapa 2 | Ranking dos 202 pares concorrentes com algum vínculo detectado (`Score > 0`), detalhando motivos e nível de risco (`ALTO`, `MEDIO`, `BAIXO`). |
| `grafo_cheio_nos.csv` / `grafo_cheio_arestas.csv` | Etapa 2 | Grafo heterogêneo completo para importação no Gephi (`1.788` nós e `5.914` arestas). |
| `subgrafos_fraudes_nos.csv` / `subgrafos_fraudes_arestas.csv` | Etapa 3 | Subgrafo reduzido de alto risco para análise e visualização no Gephi (`26` nós e `23` arestas). |

---

## Síntese dos Resultados Empíricos

Na validação sobre os certames de **Divinópolis/MG (2025)**:

- **Grafo Completo:** `1.788` vértices (`674` empresas, `1.112` sócios reais e `2` órgãos públicos: `Orgao_02` com 245 processos e `Orgao_01` com 19 processos) e `5.914` arestas (`4.059` de concorrência, `1.132` societárias, `680` de participação em licitações e `43` vínculos suspeitos de nível médio/alto).
- **Triagem de Alertas (`alertas_vinculos_concorrentes.csv`):** de `4.059` relações `Concorreu_Contra`, apenas `202` (`4,98%`) apresentaram algum indício: **`6` de nível `ALTO`**, **`37` de nível `MEDIO`** e **`159` de nível `BAIXO`** (homonímia em sobrenomes frequentes).
- **Subgrafo Reduzido (`subgrafos_fraudes`):** isolou **`26` vértices** (`12` empresas e `14` sócios), **`23` arestas** (`17` societárias e `6` vínculos suspeitos com `Score >= 2,00`) e **`6` componentes conexas independentes**, incluindo **`3` triângulos societários fechados ($K_3$)** distribuídos em dois casos críticos (um com sócia controladora + endereço + telefone idênticos, escore `29,00`; e outro com sócio PF + holding controladora em comum disputando 59 itens do mesmo pregão, escore `22,25`).

---

## Nota Ética e LGPD

Os nomes de empresas, sócios, endereços e telefones obtidos pela API durante a execução ficam restritos à pasta local `resultados/` (ignorada pelo `.gitignore`). A presença de qualquer par nos alertas gerados representa **indício estatístico-topológico para priorização de auditoria**, não constituindo juízo condenatório sem verificação documental complementar dos processos licitatórios.

