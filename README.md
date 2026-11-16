# AEDS-Graph — Triagem Indiciária em Contratações Públicas por Teoria dos Grafos

Pipeline computacional desenvolvido para a disciplina de **Algoritmos e Estruturas de Dados II (AEDS II — CEFET-MG / UFCI-MG)**, aplicando Teoria dos Grafos sobre as **55 tabelas do SICOM/TCE-MG (Divinópolis/MG, exercício de 2025)** enriquecidas pelo QSA da Receita Federal (BrasilAPI) para triagem preventiva em três eixos:

1. **Eixo 1 — Rede Societária e Materialidade Financeira:** filtragem $1$-core, decomposição por Union-Find, detecção de triângulos $K_3$ e cruzamento com empenhos/pagamentos e filtro anti-falso positivo onomástico.
2. **Eixo 2 — Rodízio de Vencedores e *Cover Bidding*:** dígrafo Perdedor $\to$ Vencedor ($P \to V$), inversões temporais em datas distintas ($t_1 \neq t_2$), ciclos curtos $C_3/C_4$, componentes fortemente conexas (Tarjan SCC), comunidades (Louvain) e razão de preço frente às cotações prévias.
3. **Eixo 3 — Concentração Orçamentária e Dependência de Fornecedores:** grafo bipartido Unidade Orçamentária $\leftrightarrow$ Credor, Índice Herfindahl–Hirschman (HHI), contração por grupos societários ($\Delta\text{HHI}$), Entropia de Shannon normalizada e *PageRank* ponderado.

> **Nota jurídica e LGPD:** Os achados estruturais têm caráter exclusivamente **indiciário e preventivo** (triagem de auditoria), não configurando prova automática de fraude. Todas as visualizações e o artigo adotam **pseudonimização integral** conforme a Lei nº 13.709/2018 (LGPD).

---

## Execução no Linux (Ubuntu 24.04)

### 1. Pré-requisitos do sistema

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Opcional, apenas caso deseje recompilar o artigo LaTeX (`report/main.pdf`) localmente:

```bash
sudo apt install -y texlive-latex-base texlive-latex-recommended texlive-latex-extra \
                    texlive-publishers texlive-lang-portuguese texlive-bibtex-extra
```

### 2. Execução automática em um comando

Na raiz do repositório:

```bash
chmod +x run_ubuntu.sh
./run_ubuntu.sh
```

O script cria `.venv/`, instala `requirements.txt` e executa as **8 etapas analíticas + geração das visualizações estilo Gephi (`ForceAtlas2`)** em modo offline com cache local (`~18 s`).

### 3. Execução manual via terminal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Execução completa usando cache local da BrasilAPI (recomendado, ~18 s):
python3 run_pipeline.py --offline --with-graphs

# Para consultar CNPJs pendentes ao vivo na BrasilAPI (1 req/s, >= 673 s sem cache):
python3 run_pipeline.py --with-graphs

# Para também recompilar report/main.pdf (requer TeX Live):
python3 run_pipeline.py --offline --with-graphs --compile-pdf
```

---

## Estrutura do Repositório

```text
AEDS-Graph/
├── run_pipeline.py                 # Orquestrador único (Ubuntu 24.04 / Windows)
├── run_ubuntu.sh                   # Script de setup e execução no Ubuntu 24.04
├── requirements.txt                # Dependências Python (NetworkX >= 3.4, etc.)
├── Diretrizes_professor.pdf        # Especificação e regras de avaliação do trabalho
├── database/2025/
│   ├── raw/                        # 55 CSVs originais do SICOM/TCE-MG (Divinópolis 2025)
│   └── processed/                  # Bases intermediárias saneadas e cache QSA local
├── scripts/
│   ├── 01_analise_socios/          # Eixo 1 (limpeza, QSA BrasilAPI, 1-core/UF/K3, materialidade)
│   ├── 02_rodizio_cover_bidding/   # Eixo 2 (disputas P->V, ciclos C3/C4, Louvain, Tarjan SCC)
│   ├── 03_concentracao_orcamentaria/ # Eixo 3 (empenhos, bipartido, HHI, PageRank, entropia)
│   └── 04_visualizacoes/           # Geração de grafos ForceAtlas2 (.gexf -> PNG) e fluxograma
├── outputs/                        # CSVs de métricas, 6 arquivos .gexf (Gephi) e figuras
├── report/                         # Artigo IEEEtran (main.tex, sections/, references.bib, main.pdf)
├── docs/                           # Documentação técnica dos eixos analíticos
└── skills/                         # Manifesto completo de todas as skills usadas pelos agentes
```

---

## Reprodução das Skills e Segurança (LGPD / Zenodo)

* **Skills utilizadas pelos agentes:** a lista completa, os scores de auditoria do NVIDIA SkillSpector e as instruções de instalação estão documentados em [`skills/README.md`](skills/README.md) e [`skills/skills_manifest.json`](skills/skills_manifest.json).
* **Customização das figuras e grafos:** consulte [`scripts/04_visualizacoes/README.md`](scripts/04_visualizacoes/README.md) para detalhes sobre como cada figura é gerada e como ajustar *ForceAtlas2*, cores, pseudonimização LGPD ou usar exportações diretas do Gephi.
* **Cuidado antes de publicar no GitHub / Zenodo:** não publique arquivos com dados pessoais brutos de pessoas físicas ou endereços/telefones do QSA (`outputs/01_analise_socios/socios_reais.csv`, `alertas_vinculos_concorrentes.csv`, `outputs/01_analise_socios/mapeamento_pseudonimos_restrito.csv` ou dumps pessoais não anonimizados — todos protegidos no `.gitignore`). Utilize apenas o resumo agregado livre de PII (`outputs/01_analise_socios/resumo_auditoria_eixo1.json`), os grafos/figuras pseudonimizados e as bases agregadas em conformidade com a LGPD.
