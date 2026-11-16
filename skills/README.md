# Registro de Skills Utilizadas — AEDS-Graph

Esta pasta documenta **todas as skills** empregadas durante o desenvolvimento multiagente (*Swarm*) deste projeto, permitindo que qualquer pessoa que clone este repositório consiga identificá-las, auditá-las e reproduzir o ambiente de criação, verificação jurídica/LGPD, revisão bibliográfica, análise visual e compilação científica em LaTeX.

> Todas as skills listadas abaixo passaram por auditoria estática de segurança com o **NVIDIA SkillSpector** (`skillspector scan "<caminho>" --no-llm --format markdown`) antes do carregamento, respeitando o critério de aprovação **Score 0–39/100**.

---

## 1. Arquitetura Multiagente (*Swarm*) e Papel de Cada Skill

O trabalho foi conduzido por um agente coordenador principal e especialistas agrupados em duas frentes:

1. **Orquestração do Swarm (`coordinator`, `monitor`, `programador`, `revisor`, `literatura`, `juridico`, `documentador`):**
   - `swarm` (`native_swarm`) — coordenação em mural compartilhado, delegação paralela e consolidação de entregas.
   - `swarm_monitor` — monitoramento de ociosidade/estagnação do swarm (`stall detection`).
2. **Redação, Validação Científica, Jurídica, Layout e Figuras do Artigo (`redator_tex` + 6 subagentes auditores):**

| Agente / Subagente | Papel no Projeto | Skills Utilizadas | Origem / Fonte | Score SkillSpector |
| :--- | :--- | :--- | :--- | :---: |
| **`coordinator` / `monitor`** | Orquestração do swarm e detecção de gargalos | `swarm` (`native_swarm`), `swarm_monitor` | Antigravity Built-in | **0/100** |
| **`redator_tex`** | Coordenação da escrita em `report/` (`IEEEtran`) | `doc-coauthoring`, `scientific-writing` | Community / K-Dense Inc. | **0/100**, **8/100** |
| **`tex_literatura`** | Validação CrossRef/arXiv/Semantic Scholar e `references.bib` | `citation-management`, `papers-skill`, `literature-search-arxiv` | K-Dense Inc. / `xwmxcz/papers-skill` / Google Science Plugin | **7/100**, **35/100**, **14/100** |
| **`tex_fluidez`** | Fluidez científica, coesão, revisão gramatical e remoção de marcas de IA | `professional-proofreader`, `avoid-ai-writing`, `copy-editing` | Community | **21/100**, **0/100**, **0/100** |
| **`tex_layout`** | Conformidade `IEEEtran`, logs LaTeX, quebras e inspeção do PDF | `latex-paper-conversion`, `pdf-official`, `ui-visual-validator` | Community | **0/100**, **7/100**, **0/100** |
| **`tex_imagens`** | Resolução 300 DPI, legibilidade tipográfica e composição visual | `matplotlib`, `ui-visual-validator`, `high-end-visual-design` | K-Dense Inc. / Community / `Leonxlnx/taste-skill` | **0/100**, **0/100**, **0/100** |
| **`tex_argumentacao`** | Rigor lógico, lastro nos CSVs/.gexf e falsificabilidade argumentativa | `scientific-writing`, `data-storytelling`, `ejentum-reasoning-harness`, `doc-coauthoring` | K-Dense Inc. / Community / `ejentum/ejentum-mcp` | **8/100**, **0/100**, **10/100**, **0/100** |
| **`tex_juridico_lgpd`** | Direito administrativo (Leis 14.133/21, 12.846/13, 12.529/11, TCU) e LGPD (Lei 13.709/18) | `advogado-especialista`, `privacy-by-design`, `gdpr-data-handling`, `legal-advisor` | Community (`renat` / Privacy / GDPR) | **0/100**, **11/100**, **27/100**, **0/100** |

> **Observação tipográfica:** Os scripts em `scripts/04_visualizacoes/` também aproveitam opcionalmente as fontes locais do pacote `canvas-design` (`InstrumentSans` e `IBMPlexMono`), com fallback automático para `DejaVu Sans` no Ubuntu 24.04 quando ausentes.

---

## 2. Skill Avaliada e Bloqueada (NÃO Utilizada)

Para transparência e segurança na reprodução:

* **`literature-search-openalex`** (Science Plugin): obteve **Score 53/100 (`HIGH` — `DO NOT INSTALL`, 7 alertas)** no scanner NVIDIA SkillSpector. Foi **bloqueada e excluída** do fluxo, sendo substituída com segurança por `citation-management` + `papers-skill` + `literature-search-arxiv`.

---

## 3. Como Reproduzir o Ambiente de Skills

Consulte [`skills_manifest.json`](skills_manifest.json) para o catálogo estruturado completo. Para reproduzir o ambiente em outra máquina (Linux/Windows):

1. **Habilitar o ambiente Antigravity e o Plugin Science (built-in / marketplace oficial):**
   - Fornece nativamente `swarm`, `swarm_monitor` e `literature-search-arxiv`.
2. **Instalar as skills comunitárias em `~/.agents/skills/`:**
   - **Pesquisa & Escrita Científica:** `doc-coauthoring`, `scientific-writing`, `citation-management`, `papers-skill` ([`xwmxcz/papers-skill`](https://github.com/xwmxcz/papers-skill)), `data-storytelling`, `latex-paper-conversion`, `pdf-official`.
   - **Revisão & Estilo:** `professional-proofreader`, `avoid-ai-writing`, `copy-editing`.
   - **Visualização & Layout:** `matplotlib`, `ui-visual-validator`, `high-end-visual-design` ([`Leonxlnx/taste-skill`](https://github.com/Leonxlnx/taste-skill)).
   - **Raciocínio & Verificação:** `ejentum-reasoning-harness` ([`ejentum/ejentum-mcp`](https://github.com/ejentum/ejentum-mcp)).
   - **Jurídico & Proteção de Dados:** `advogado-especialista`, `privacy-by-design`, `gdpr-data-handling`, `legal-advisor`.
3. **Auditar antes de ativar qualquer skill:**
   ```bash
   skillspector scan "$HOME/.agents/skills/<nome-da-skill>" --no-llm --format markdown
   ```
   Apenas skills com **Score ≤ 39/100** devem ser carregadas automaticamente.

---

## 4. Importante sobre a Execução do Código Python

As **skills são necessárias apenas para reproduzir o fluxo de trabalho dos agentes de IA** (redação assistida, revisão bibliográfica, auditoria jurídica e revisão de layout). O **código-fonte analítico em Python** (`run_pipeline.py` e `scripts/`) **não depende de nenhuma skill** para rodar no Linux (Ubuntu 24.04) ou Windows — requer apenas Python 3 e os pacotes de `requirements.txt`.
