# Detecção de Conluio e Concorrência Simulada em Licitações Municipais via Grafos Multicamada

Pipeline computacional em Python para modelagem e mineração de redes heterogêneas multicamada aplicadas à triagem de riscos em contratações públicas municipais, combinando registros de licitações do **SICOM/TCE-MG** (estudo empírico em Divinópolis/MG, exercício de 2025) com dados do **Quadro de Sócios e Administradores (QSA)** da Receita Federal via **BrasilAPI**.

---

## Sumário

- [Visão Geral da Metodologia](#visão-geral-da-metodologia)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pré-requisitos (Ubuntu / Linux)](#pré-requisitos-ubuntu--linux)
- [Como Usar o Makefile](#como-usar-o-makefile)
- [Arquivos Gerados (`results/`)](#arquivos-gerados-results)
- [Síntese dos Resultados Empíricos](#síntese-dos-resultados-empíricos)
- [Nota Ética e LGPD](#nota-ética-e-lgpd)

---

## Visão Geral da Metodologia

O projeto executa um pipeline determinístico em **3 etapas sequenciais**:

1. **Etapa 1 — Higienização e Grafo Base (`src/01_limpeza_dados.py`)**
   - Lê as tabelas do SICOM/TCE-MG em `data/raw/` (`licitacao`, `habLicitacao`, `quadroSocLicitacao`, `julgLicitacao`).
   - Recupera CNPJs/CPFs corrompidos por notação científica (ex.: `2.71E+13`) e restaura zeros à esquerda (14 dígitos para CNPJ e 11 para CPF).
   - Constrói as relações `Participou_Licitacao` (Empresa $\leftrightarrow$ Órgão) e a projeção de disputa `Concorreu_Contra` (soma de certames e itens disputados em comum).

2. **Etapa 2 — Enriquecimento Societário via BrasilAPI e Grafo Completo (`src/02_enriquecimento_socios.py`)**
   - Supera a supressão de CPFs/nomes da tabela `quadroSocLicitacao.csv` consultando os 673 CNPJs na BrasilAPI (`https://brasilapi.com.br/api/cnpj/v1/{cnpj}`), com controle de vazão (*rate limiting*) e cache persistente em `results/cache_qsa_brasilapi.json`.
   - Recupera integrantes do QSA (sócios, controladores e administradores — PF e PJ) e titulares de MEI/EI.
   - Calcula o **Escore de Vínculo** entre pares de concorrentes (`Concorreu_Contra`):
     - Integrante em comum no QSA: `+10,00` por vínculo
     - Mesma raiz de CNPJ (8 primeiros dígitos): `+10,00`
     - Mesmo endereço normalizado: `+10,00`
     - Mesmo telefone normalizado: `+8,00`
     - Mesmo e-mail corporativo (filtrando domínios/termos contábeis): `+5,00`
     - Sobrenome raro em comum: `+1,00`
     - Sobrenome comum em comum (dicionário de 53 sobrenomes frequentes no Brasil): `+0,25`
   - Classifica cada par em **`ALTO`**, **`MEDIO`** ou **`BAIXO`** e gera o **Grafo Completo** (`results/grafo_cheio_nos.csv` e `results/grafo_cheio_arestas.csv`, retendo arestas `Vinculo_Suspeito` das faixas `MEDIO` e `ALTO`).

3. **Etapa 3 — Redução Topológica e Detecção de Motivos $K_3$ (`src/03_reduzir_grafo.py`)**
   - Carrega o grafo completo em uma estrutura de **Lista de Adjacência** (`GrafoMulticamada`) e executa quatro algoritmos em grafos:
     1. **Filtragem por Predicado de Arestas** — $O(|V| + |E|)$: mantém apenas arestas `Vinculo_Suspeito` com `Score >= 2,00` e as arestas `É_Dono_De` incidentes às empresas selecionadas.
     2. **Remoção de Vértices Isolados (*1-Core*)** — $O(|V| + |E|)$: remove os 1.762 vértices de grau zero.
     3. **Componentes Conexas via *Union-Find*** (*Path Compression* + *Union by Rank*) — $O((|V| + |E|)\,\alpha(|V|))$: isola as componentes não triviais ($|C_i| \ge 2$).
     4. **Enumeração de Motivos Triangulares ($K_3$)** — $O(|E_s|\,d_{\max})$: identifica ciclos fechados (*Integrante do QSA $\to$ Empresa A $\leftrightarrow$ Empresa B $\leftarrow$ Integrante do QSA*).

---

## Estrutura do Projeto

```text
AEDS-Graph/
├── data/
│   └── raw/                             # Planilhas CSV públicas do SICOM/TCE-MG (2025)
├── src/
│   ├── 01_limpeza_dados.py              # Etapa 1: saneamento cadastral e grafo base
│   ├── 02_enriquecimento_socios.py      # Etapa 2: BrasilAPI, escores e grafo completo
│   └── 03_reduzir_grafo.py              # Etapa 3: redução topológica (1-Core, Union-Find, K_3)
├── results/                             # Gerado automaticamente pelo pipeline (ignorado pelo Git)
├── Makefile                             # Automação de execução e limpeza no Ubuntu/Linux
├── requirements.txt                     # Dependências Python (pandas e numpy)
├── README.md                            # Este guia
└── .gitignore
```

---

## Pré-requisitos (Ubuntu / Linux)

- **Python 3** (com `venv`)
- **GNU Make**
- **Acesso à internet** (necessário na Etapa 2 caso `results/cache_qsa_brasilapi.json` ainda não exista)

Em uma instalação limpa do Ubuntu (22.04 / 24.04+), instale os pacotes básicos uma única vez:

```bash
sudo apt update && sudo apt install -y make python3 python3-venv
```

> O `Makefile` gerencia um ambiente virtual isolado (`.venv/`) automaticamente, compatível com a política PEP 668 (`externally-managed-environment`) do Ubuntu.

---

## Como Usar o Makefile

Execute os comandos na **raiz do repositório**:

### Executar o pipeline completo
```bash
make run
```
*(Ou simplesmente `make`.)*  
Cria `.venv/` (se necessário), instala `requirements.txt` (`pandas>=2.0.0`, `numpy>=1.24.0`) e executa em sequência `src/01_limpeza_dados.py`, `src/02_enriquecimento_socios.py` e `src/03_reduzir_grafo.py`.

### Limpar arquivos gerados
```bash
make clean
```
Apaga completamente `results/` e diretórios `__pycache__/`.

### Todos os alvos disponíveis

| Comando | O que faz |
|---|---|
| `make run` | Configura `.venv/` (se necessário) e executa as 3 etapas do pipeline. |
| `make setup` | Apenas cria `.venv/` e instala `requirements.txt`. |
| `make step1` | Executa somente `src/01_limpeza_dados.py`. |
| `make step2` | Executa somente `src/02_enriquecimento_socios.py`. |
| `make step3` | Executa somente `src/03_reduzir_grafo.py`. |
| `make clean` | Apaga `results/` e caches `__pycache__/`. |
| `make clean-csv` | Apaga apenas `results/*.csv`, **mantendo** `cache_qsa_brasilapi.json`. |
| `make distclean` | Executa `make clean` e remove também `.venv/`. |
| `make help` | Lista os comandos disponíveis no terminal. |

> **Dica ao migrar do Windows para o Ubuntu:** caso copie a pasta diretamente do Windows com uma `.venv/` já existente, execute `make distclean && make run` para recriar o ambiente Linux.

---

## Arquivos Gerados (`results/`)

| Arquivo | Etapa | Descrição |
|---|---|---|
| `tabela_nos_gephi.csv` / `tabela_arestas_gephi.csv` | Etapa 1 | Grafo base anterior ao enriquecimento do QSA. |
| `cache_qsa_brasilapi.json` | Etapa 2 | Cache local das respostas da BrasilAPI por CNPJ. |
| `socios_reais.csv` | Etapa 2 | Integrantes do QSA e titulares de MEI recuperados para os participantes. |
| `alertas_vinculos_concorrentes.csv` | Etapa 2 | Ranking dos 202 pares concorrentes com `Score > 0`, motivos e faixa (`ALTO`, `MEDIO`, `BAIXO`). |
| `grafo_cheio_nos.csv` / `grafo_cheio_arestas.csv` | Etapa 2 | Grafo heterogêneo completo (`1.788` nós e `5.914` arestas). |
| `subgrafos_fraudes_nos.csv` / `subgrafos_fraudes_arestas.csv` | Etapa 3 | Subgrafo reduzido da faixa superior (`26` nós e `23` arestas). |

---

## Síntese dos Resultados Empíricos

Validação sobre os registros de **Divinópolis/MG (exercício de 2025)**:

- **Grafo Completo:** `1.788` vértices (`2` órgãos públicos: Prefeitura com `245` certames / `628` ligações e Câmara com `19` certames / `52` ligações; `674` empresas licitantes = `673` PJ + `1` PF; `1.112` integrantes do QSA = `1.044` PF + `68` PJ) e `5.914` arestas (`680` `Participou_Licitacao`, `4.059` `Concorreu_Contra`, `1.132` `É_Dono_De` e `43` `Vinculo_Suspeito`).
- **Estratificação (`alertas_vinculos_concorrentes.csv`):** de `4.059` pares co-disputantes, `202` (`4,98%`) apresentaram sobreposição positiva: **`6` `ALTO`**, **`37` `MEDIO`** e **`159` `BAIXO`**.
- **Subgrafo Reduzido (`subgrafos_fraudes`):** redução de `98,55%` dos vértices e `99,61%` das arestas, isolando **`26` vértices** (`12` empresas e `14` integrantes do QSA/MEI), **`23` arestas** (`17` `É_Dono_De` e `6` `Vinculo_Suspeito`), **`6` componentes conexas independentes** e **`3` motivos triangulares ($K_3$)** concentrados em duas componentes.

---

## Nota Ética e LGPD

Os nomes civis, razões sociais, CNPJs, endereços completos e telefones recuperados na execução ficam restritos à pasta local `results/` (ignorada pelo `.gitignore`). Os resultados têm caráter exclusivamente **indiciário para triagem de auditoria**, não constituindo comprovação automática de fraude ou conluio.
