# Guia Teórico e Metodológico: Da Rede Completa ao Subgrafo de Fraudes

Este documento apresenta a fundamentação teórica, a interpretação estrutural e a formulação algorítmica detalhada que explicam:
1. **O que o subgrafo de fraudes representa visual, estrutural e juridicamente;**
2. **O pipeline passo a passo completo (do dado bruto do SICOM até as planilhas finais);**
3. **O passo a passo detalhado dos algoritmos de Teoria dos Grafos que transformam o grafo gigante no grafo reduzido.**

---

## 1. O Que o Grafo Reduzido Representa?

O subgrafo gerado nos arquivos [`subgrafos_fraudes_nos.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_nos.csv) e [`subgrafos_fraudes_arestas.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_arestas.csv) (com **26 nós, 23 arestas e 6 componentes conexas isoladas**) é a **representação topológica pura dos núcleos de conluio, conluio familiar e concorrência simulada** detectados no município de Divinópolis em 2025.

Diferente do grafo gigante completo — que mistura todas as relações normais de mercado —, o subgrafo isola estritamente os **grupos que violam o princípio da competitividade e da isonomia** (Art. 14 da Lei nº 14.133/2021).

### A. Elementos do Grafo (Tipos de Vértices e Arestas)
* **Vértices de Empresas (Azul/Verde):** Pessoas jurídicas ou empresários individuais que participaram de certames públicos.
* **Vértices de Sócios Reais (Laranja/Roxo):** Pessoas físicas e holdings controladoras que compõem o Quadro de Sócios e Administradores (QSA) oficial obtido na Receita Federal do Brasil.
* **Aresta Direcionada `É_Dono_De`:** Liga a pessoa física/holding à empresa da qual ela é proprietária ou administradora legal.
* **Aresta Não-Direcionada `Vinculo_Suspeito`:** Liga duas empresas que concorreram entre si na mesma licitação e acumulam sócios, endereços físicos, telefones ou sobrenomes idênticos (peso proporcional à gravidade do conluio).

---

### B. O Padrão Topológico Central: O "Triângulo Societário" ($K_3$)

No jargão de mineração de redes (*network motifs*), a simulação de concorrência societária manifesta-se visualmente como um **Triângulo Fechado** ou **3-Clique ($K_3$)**:

```mermaid
flowchart TD
    S["SÓCIO CONTROLADOR<br>(Leonardo Antonio R. Cury)"]
    H["HOLDING SÓCIA<br>(LARC Participações Ltda)"]
    
    E1["EMPRESA CONCORRENTE A<br>(DENTEMED - CNPJ 07.897.039)"]
    E2["EMPRESA CONCORRENTE B<br>(ODONTOMASTER - CNPJ 54.860.907)"]
    
    S -- "É_Dono_De" --> E1
    S -- "É_Dono_De" --> E2
    H -- "É_Dono_De" --> E1
    H -- "É_Dono_De" --> E2
    
    E1 == "Vinculo_Suspeito<br>(Disputaram 59 itens juntos!)" === E2
```

**Por que isso constitui fraude evidente?**
* No papel, *Dentemed* e *Odontomaster* apresentam-se ao município como concorrentes independentes disputando **59 itens** de materiais odontológicos (Licitação 1499516, Processo 208/2025).
* Na topologia do grafo, as duas empresas convergem para o **mesmo nó controlador central** (*Leonardo Antonio Rodrigues Cury*) e para a mesma holding (*LARC Participações*).
* Não existe concorrência econômica real: qualquer que seja a empresa vencedora, o faturamento converge para a mesma pessoa física, frustrando o caráter competitivo do certame (Art. 337-F do Código Penal e Art. 14 da Lei 14.133/2021).

---

### C. Os 6 Núcleos Isolados no Subgrafo de Alto Risco

A análise simultânea (sócios + parentesco + domicílio fiscal + contato telefônico) isolou 6 componentes conexas de alta gravidade:

1. **Tríplice Evidência Máxima (Score 29.00):** *Masif Artigos Médicos* $\times$ *Joaomed Cirúrgica*
   - Mesma sócia controladora (*Katty Gessele*);
   - **Mesmo endereço físico:** *R. Wilson Lois Koehler Jr, 406 - Curitiba/PR*;
   - **Mesmo telefone fixo:** *(41) 2108-4545*;
   - Sobrenome comum: *Gessele*.
2. **Triângulo Societário Fechado (Score 22.25):** *Dentemed* $\times$ *Odontomaster*
   - Mesmo sócio pessoa física (*Leonardo Antonio Rodrigues Cury*);
   - Mesma holding controladora (*LARC Participações e Investimentos Ltda*);
   - **Disputa simultânea em 59 itens individuais de odontologia.**
3. **Conluio por Domicílio Fiscal Compartilhado (Score 10.25):** *EGC Comércio de Informática* $\times$ *GWC Indústria de Eletrônicos*
   - **Mesmo endereço físico:** *R. Liberdade, 3230 - Bayeux/PB*;
   - Sobrenome em comum: *Costa*.
4. **Contato Telefônico Idêntico + Sobrenomes Raros (Score 10.00):** *Ortom Indústria Têxtil* $\times$ *Ortobens Distribuidora Hospitalar*
   - **Mesmo telefone fixo:** *(15) 3262-5549*;
   - Sobrenomes raros compartilhados: *Padilha* e *Viapiana*.
5. **Vínculo Familiar Consanguíneo (Score 2.00):** *Vilson Cordeiro Marra* $\leftrightarrow$ *Alvimar Cordeiro Marra*
   - Ambos Empresários Individuais / MEI com o mesmo sobrenome composto exclusivo disputando certame de transporte escolar (Lic. 1472202).
6. **Vínculo Familiar Duplo (Score 2.00):** *AMB Distribuidora de Medicamentos* $\times$ *M.H.M. do Couto - Comercial Ltda*
   - Sobrenomes compartilhados entre sócios: *Couto* e *Mori*.

---

## 2. O Pipeline Passo a Passo (Do Dado Bruto ao Subgrafo)

O pipeline do projeto foi estruturado em um fluxo encadeado de **3 scripts Python automatizados**:

```mermaid
flowchart TD
    A["CSVs SICOM (TCE-MG)<br>Pasta arquivos_originais/"] --> B["1. data_cleaning.py"]
    B -->|tabela_nos_gephi.csv<br>tabela_arestas_gephi.csv| C["2. enriquecimento_socios.py"]
    C -->|Consulta BrasilAPI / QSA<br>Cache local em JSON| D["Ficha Cadastral Completa<br>(Sócios, Endereços, Telefones)"]
    D --> E["Cálculo do Escore Multidimensional s(a,b)<br>Sócios + Parentesco IDF + Domicílio + Contato"]
    E -->|grafo_cheio_nos.csv (1.788 nós)<br>grafo_cheio_arestas.csv (5.914 arestas)| F["3. reduzir_grafo.py"]
    F --> G["Cadeia de 4 Algoritmos Formais em Grafos<br>Subgrafo Induzido -> 1-Core -> Union-Find -> K_3"]
    G --> H["subgrafos_fraudes_nos.csv (26 nós)<br>subgrafos_fraudes_arestas.csv (23 arestas)<br>(6 Núcleos Isolados Prontos para o Gephi)"]
```

### Passo 1: Limpeza e Estruturação (`data_cleaning.py`)
* **Entrada:** Arquivos CSV brutos da pasta `arquivos_originais/`.
* **Ações:**
  1. Converte a notação científica (ex.: `2,71E+13`) gerada pela exportação do Excel em inteiros longos e normaliza os zeros à esquerda (14 dígitos para CNPJ e 11 para CPF).
  2. Extrai todos os participantes únicos das tabelas de Habilitação (`habLicitacao.csv`) e Julgamento (`julgLicitacao.csv`).
  3. Mapeia a participação no órgão público (`Participou_Licitacao`) e a concorrência direta (`Concorreu_Contra`) por licitação e por item disputado.
* **Saída:** [`tabela_nos_gephi.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/tabela_nos_gephi.csv) e [`tabela_arestas_gephi.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/tabela_arestas_gephi.csv).

### Passo 2: Enriquecimento via API e Grafo Cheio (`enriquecimento_socios.py`)
* **Entrada:** `tabela_nos_gephi.csv` e `tabela_arestas_gephi.csv`.
* **Ações:**
  1. Como o SICOM omitiu os sócios em virtude da LGPD, o script consulta os 673 CNPJs na BrasilAPI (QSA da Receita Federal) com cache local persistente em `cache_qsa_brasilapi.json`.
  2. Recupera 1.112 pessoas físicas reais, além de logradouro, número, município, UF e telefones de contato de cada empresa.
  3. Analisa simultaneamente todos os pares de empresas que disputaram certames (`Concorreu_Contra`), aplicando a **Fórmula de Escore Multidimensional**:
     $$s(a, b) = \alpha \cdot |S(a) \cap S(b)| + \beta \cdot [\text{raiz}(a) = \text{raiz}(b)] + \gamma \cdot [\text{end}(a) = \text{end}(b)] + \delta \cdot [\text{tel}(a) = \text{tel}(b)] + \sum_{n \in N(a) \cap N(b)} \omega(n)$$
     onde $\alpha = 10$, $\beta = 10$, $\gamma = 10$, $\delta = 8$, e $\omega(n)$ é a raridade do sobrenome (estilo IDF).
  4. Substitui os nós anônimos pelos Sócios Reais e adiciona a aresta `Vinculo_Suspeito` com o escore calculado.
* **Saída:** O **Grafo Cheio** completo com todas as relações municipais:
  - [`grafo_cheio_nos.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/grafo_cheio_nos.csv) (1.788 nós)
  - [`grafo_cheio_arestas.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/grafo_cheio_arestas.csv) (5.914 arestas)
  - [`alertas_vinculos_concorrentes.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/alertas_vinculos_concorrentes.csv)

### Passo 3: Redução Algorítmica em Grafos (`reduzir_grafo.py`)
* **Entrada:** `grafo_cheio_nos.csv` e `grafo_cheio_arestas.csv`.
* **Ações:** Aplica os algoritmos formais de Teoria dos Grafos para podar o emaranhado e extrair os núcleos de alto risco.
* **Saída:** [`subgrafos_fraudes_nos.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_nos.csv) e [`subgrafos_fraudes_arestas.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_arestas.csv).

---

## 3. Passo a Passo Detalhado dos Algoritmos de Redução

A pergunta central é: **como os algoritmos de grafos transformam o grafo gigante de 1.788 nós no subgrafo limpo de 26 nós?**

O script [`reduzir_grafo.py`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/reduzir_grafo.py) executa uma cadeia de **4 algoritmos encadeados**:

```mermaid
flowchart LR
    G["Grafo Cheio<br>(1.788 nós | 5.914 arestas)"] -->|1. Subgrafo Induzido O(V+E)| G1["Arestas Críticas<br>(Corta Prefeitura e mercado)"]
    G1 -->|2. Poda 1-Core via BFS O(V+E)| G2["Grafo sem Nós Isolados<br>(Remove grau 0)"]
    G2 -->|3. Union-Find O(E · α(V))| G3["Componentes Conexas<br>(6 Núcleos Isolados)"]
    G3 -->|4. Triangle Listing O(E · d_max)| G4["Identificação do Motivo K_3<br>(Triângulos Societários)"]
    G4 --> S["subgrafos_fraudes<br>(26 nós | 23 arestas)"]
```

---

### Algoritmo 1: Subgrafo Induzido por Arestas (*Edge-Induced Subgraph*)
* **Objetivo:** Eliminar o "buraco negro" gravitacional do órgão público (`Participou_Licitacao` com 680 arestas) e a concorrência comum sem suspeita (`Concorreu_Contra` com mais de 4.000 arestas), retendo estritamente as arestas que representam indício formal de conluio.
* **Formulação Matemática:**  
  Dado o grafo heterogêneo completo $G = (V, E)$, define-se um **predicado de seleção de arestas** $\mathcal{P}(u, v, \text{tipo}, \text{peso})$:
  $$\mathcal{P}(e) \iff (\text{tipo}(e) = \text{'Vinculo\_Suspeito'} \land \text{peso}(e) \ge 2.0) \lor (\text{tipo}(e) = \text{'É\_Dono\_De'} \land \text{Target}(e) \in V_{\text{suspeito}})$$
  O subgrafo induzido $G' = (V', E')$ é construído retendo:
  $$E' = \{e \in E \mid \mathcal{P}(e)\}$$
  $$V' = \{u \in V \mid \exists v \in V \text{ tal que } (u, v) \in E' \lor (v, u) \in E'\}$$
* **Complexidade Temporal:** **$O(|V| + |E|)$** (uma única passagem linear sobre a lista de arestas).

---

### Algoritmo 2: Decomposição 1-Core (*Poda de Grau via Fila BFS*)
* **Objetivo:** Eliminar todos os vértices que se tornaram **isolados** (grau zero) após o corte das arestas normais, garantindo que nenhuma empresa sem irregularidades polua a visualização.
* **Funcionamento Passo a Passo:**
  1. Calcula-se o grau de cada vértice: $d(u) = |\text{adj}[u]|$.
  2. Inicializa-se uma fila FIFO contendo todos os nós com $d(u) < 1$.
  3. Enquanto a fila não estiver vazia:
     - Remove-se o nó $u$ e marca-se como descartado;
     - Para cada vizinho $v$ de $u$, decrementa-se $d(v) \leftarrow d(v) - 1$;
     - Se $d(v)$ cair para menos de 1, insere-se $v$ na fila.
  4. O conjunto de vértices sobreviventes forma o **1-Core** da rede.
* **Complexidade Temporal:** **$O(|V| + |E|)$** (cada vértice e aresta é visitado no máximo uma vez).

---

### Algoritmo 3: Decomposição em Componentes Conexas via Union-Find (*Disjoint-Set*)
* **Objetivo:** Particionar os nós sobreviventes em **ilhas desconectadas de suspeita** ($C_1, C_2, \dots, C_k$), isolando cada núcleo de conluio de forma independente.
* **Estrutura de Dados Union-Find com Duas Otimizações:**
  1. **Compressão de Caminho (*Path Compression*):** durante a operação `find(x)`, todos os nós do caminho são apontados diretamente para a raiz da árvore, achatando a profundidade:
     ```python
     def find(self, x):
         if self.pai[x] != x:
             self.pai[x] = self.find(self.pai[x])
         return self.pai[x]
     ```
  2. **União por Rank (*Union by Rank*):** a árvore de menor altura é sempre pendurada sob a raiz da árvore de maior altura:
     ```python
     def union(self, x, y):
         rx, ry = self.find(x), self.find(y)
         if rx != ry:
             if self.rank[rx] < self.rank[ry]:
                 rx, ry = ry, rx
             self.pai[ry] = rx
             if self.rank[rx] == self.rank[ry]:
                 self.rank[rx] += 1
     ```
* **Critério de Poda:** Retém-se apenas componentes com $|C_i| \ge 2$, descartando nós sem par.
* **Complexidade Temporal:** **$O(|E| \cdot \alpha(|V|)) \approx O(V + E)$**, onde $\alpha$ é a função inversa de Ackermann ($\alpha(n) \le 4$ para qualquer valor prático no universo).

---

### Algoritmo 4: Listagem de Triângulos Societários (*Triangle Listing / Motivo $K_3$*)
* **Objetivo:** Identificar e listar explicitamente todas as ocorrências do **Triângulo Societário**, provando o controle societário compartilhado entre empresas concorrentes.
* **Funcionamento Passo a Passo:**
  1. Cria-se um índice invertido de propriedade: $\text{donos}[e] = \{s \in P \mid (s, e) \in E_{\text{É\_Dono\_De}}\}$.
  2. Para cada aresta $(e_1, e_2)$ de tipo `Vinculo_Suspeito`:
     - Calcula-se a interseção dos conjuntos de donos:
       $$\text{interseção} = \text{donos}[e_1] \cap \text{donos}[e_2]$$
     - Se $\text{interseção} \neq \emptyset$, para cada sócio $s \in \text{interseção}$, emite-se a 3-clique formal $\{s, e_1, e_2\}$ como um triângulo de fraude.
* **Complexidade Temporal:** **$O(|E| \cdot d_{\max})$**, onde $d_{\max}$ é o grau máximo de um nó sócio (número de empresas de um mesmo proprietário). Como no mundo real $d_{\max} \ll 50$, o algoritmo executa em **menos de 5 milissegundos**.

---

## 4. Tabela Resumo dos Algoritmos de Redução

| Algoritmo | Papel no Pipeline | Entrada $\to$ Saída | Complexidade | Justificativa Técnica |
|---|---|:---:|:---:|---|
| **Subgrafo Induzido por Arestas** | Filtra as arestas de volume massivo do órgão e concorrência genérica | 5.914 arestas $\to$ arestas críticas | $O(V + E)$ | Elimina a mancha geométrica do órgão municipal |
| **Poda de Grau 1-Core (BFS)** | Remove nós isolados de grau 0 que não têm ligação com fraudes | 1.788 nós $\to$ nós ativos | $O(V + E)$ | Limpa os nós sem conexão que ficariam flutuando na tela |
| **Componentes Conexas (Union-Find)** | Particiona a rede em núcleos conexos de suspeita | Nós ativos $\to$ 6 componentes conexas | $O(E \cdot \alpha(V))$ | Isola duplas e triângulos de conluio de forma modular |
| **Listagem de Triângulos ($K_3$)** | Extrai o ciclo fechado Sócio $\to$ $E_1 \leftrightarrow E_2 \leftarrow$ Sócio | 6 componentes $\to$ 3 triângulos comprovados | $O(E \cdot d_{\max})$ | Prova matemática da simulação de concorrência com controle unificado |

---

## 5. Como Executar Todo o Processo com 1 Comando

No terminal do projeto, execute em sequência:

```powershell
uv run data_cleaning.py
uv run enriquecimento_socios.py
uv run reduzir_grafo.py
```

O script `reduzir_grafo.py` imprimirá no terminal os triângulos $K_3$ encontrados e gravará os arquivos prontos para abrir no Gephi:
* [`subgrafos_fraudes_nos.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_nos.csv) (26 nós)
* [`subgrafos_fraudes_arestas.csv`](file:///c:/Users/Pedro/Documents/DeteccaoDeFraudesEmLicitacoes/arquivos%20modificados/subgrafos_fraudes_arestas.csv) (23 arestas)
