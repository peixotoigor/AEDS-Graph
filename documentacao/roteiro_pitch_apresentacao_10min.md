# Roteiro Completo do Pitch Oral (10 Minutos)
**Projeto Final:** Estruturas em Árvores e Teoria dos Grafos (CEFET-MG / UFCI-MG)  
**Tema:** Detecção de Conluio e Concorrência Simulada em Contratações Públicas Municipais via Grafos Heterogêneos Multicamada  
**Estudo de Caso:** Divinópolis/MG (Exercício 2025)  
**Apresentador:** Pedro Henrique  

---

## 1. Visão Geral da Gestão de Tempo

| Bloco | Minutagem | Slide | Objetivo Principal |
|---|:---:|---|---|
| **I. Abertura & O Problema** | 00:00 - 02:00 | Slides 1 e 2 | Capturar a atenção da banca com a relevância do tema e a falha das abordagens tradicionais |
| **II. A Modelagem em Grafos** | 02:00 - 04:30 | Slides 3 e 4 | Explicar o modelo heterogêneo multicamada e a formulação matemática ($E^* = E_E \cap E_V$) |
| **III. Algoritmos e Complexidade**| 04:30 - 06:30 | Slides 5 e 6 | Demonstrar domínio técnico: redução do grafo gigante ao subgrafo limpo em tempo linear $O(V+E)$ |
| **IV. Resultados Empíricos & Gephi**| 06:30 - 08:30 | Slides 7 e 8 | O "Momento Uau": mostrar os 5 casos reais, o triângulo Dentemed × Odontomaster e o Gephi |
| **V. Conclusão & Próximos Passos** | 08:30 - 10:00 | Slide 9 | Fechamento de impacto: valor prático para Tribunais de Contas e combate à corrupção |

---

## 2. Roteiro Slide a Slide com Script de Fala

```
========================================================================================
SLIDE 1: CAPA
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Título: Detecção de Conluio em Licitações Públicas via Grafos Heterogêneos Multicamada
- Subtítulo: Uma Abordagem Estrutural para Identificação de Concorrência Simulada e Parentesco
- Autor: Pedro Henrique
- Instituição: CEFET-MG / UFCI-MG — Estruturas em Árvores e Teoria dos Grafos
- Ano: 2026 / Caso de Estudo: Divinópolis-MG (2025)
========================================================================================
```
🗣️ **Fala do Apresentador (00:00 - 00:45):**  
*"Boa tarde a todos os membros da banca e colegas. As compras públicas no Brasil movimentam mais de 10% do PIB nacional, sendo regidas pela Nova Lei de Licitações sob a premissa fundamental da justa competição. No entanto, um dos crimes mais danosos e discretos contra a administração pública é a **concorrência simulada**: empresas formalmente separadas, mas controladas pelo mesmo grupo ou pela mesma família, disputando o mesmo certame para manipular preços e cotas. Hoje vou demonstrar como a Teoria dos Grafos permite transformar esse problema relacional complexo em uma detecção algorítmica exata e visual em tempo linear."*

---

```
========================================================================================
SLIDE 2: O PROBLEMA E O DESAFIO DOS DADOS (SICOM / TCE-MG)
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- O gargalo da auditoria tabular: consultas SQL falham em cruzamentos de múltiplos saltos.
- Desafio dos Dados Abertos (SICOM):
  * Problema 1: Notação científica corrompendo CNPJs (ex: 2.71E+13).
  * Problema 2: Anonimização de sócios pelo TCE-MG devido à LGPD (nomes de pessoas físicas omitidos).
- A Solução: Enriquecimento cadastral automatizado com o QSA da Receita Federal (BrasilAPI).
========================================================================================
```
🗣️ **Fala do Apresentador (00:45 - 02:00):**  
*"O primeiro grande desafio prático deste trabalho residiu na qualidade dos dados públicos. Analisando a base do SICOM do Tribunal de Contas de Minas Gerais referente a Divinópolis em 2025, deparamo-nos com duas barreiras técnicas: identificadores corrompidos por notação científica durante a exportação e, mais grave, a **anonimização dos sócios** em virtude da LGPD, onde o TCE substituiu os CPFs e nomes dos proprietários pelo próprio CNPJ da empresa.*  
*Para contornar essa limitação e viabilizar a análise de parentesco, construímos um pipeline de enriquecimento em Python que consultou a base pública do Quadro de Sócios e Administradores da Receita Federal para todos os 673 CNPJs participantes, reconstruindo uma base com 1.112 pessoas físicas reais."*

---

```
========================================================================================
SLIDE 3: A MODELAGEM MATEMÁTICA MULTICAMADA
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Definição Formal: G = (V, E, τ, φ, w)
- As 4 Camadas:
  * G_B: Grafo Bipartido Empresa-Licitação (seq_licitacao).
  * G_E: Projeção de Concorrência Monopartida (pesos por frequência e índice de Jaccard).
  * G_S: Grafo Societário Real (Pessoas Físicas -> Empresas).
  * G_V: Grafo de Vínculos com ponderação IDF de raridade de sobrenome.
- Diagrama esquemático das camadas conectando-se.
========================================================================================
```
🗣️ **Fala do Apresentador (02:00 - 03:15):**  
*"Para modelar esse ecossistema, formalizamos o problema como um **Grafo Heterogêneo Multicamada**. Não temos apenas um grafo simples, mas sim diferentes tipos de nós — Empresas, Sócios e Licitações — e múltiplos tipos de arestas.*  
*Temos a camada de concorrência direta $G_E$, obtida pela projeção bipartida ponderada por Jaccard das empresas que disputaram os mesmos itens; a camada societária $G_S$, ligando cada pessoa física às suas empresas; e a camada de vínculos $G_V$. Para evitar que patronímicos muito comuns como 'Silva' gerassem falsos positivos, adaptamos o conceito de **IDF (Inverse Document Frequency)** para atribuir peso máximo apenas a sobrenomes raros."*

---

```
========================================================================================
SLIDE 4: O NÚCLEO DA DETECÇÃO: INTERSEÇÃO TOPOLÓGICA
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Equação Central: E* = E_E ∩ E_V
- O que é E*? Arestas onde existe disputa simultânea E vínculo familiar/societário.
- Motivo Topológico Central: O Triângulo Societário (K_3 fechado).
- [Diagrama do Triângulo]:
    Sócio Controlador (w) ---> Empresa A (u)
    Sócio Controlador (w) ---> Empresa B (v)
    Empresa A (u) <==========> Empresa B (v) [Vinculo_Suspeito em 59 itens]
========================================================================================
```
🗣️ **Fala do Apresentador (03:15 - 04:30):**  
*"O coração da nossa metodologia reside na **interseção de camadas**: $E^* = E_E \cap E_V$. Isolamos estritamente os pares de empresas que satisfazem duas condições simultâneas: disputaram o mesmo certame e mantêm sócios em comum ou forte vínculo familiar.*  
*Topologicamente, a simulação de concorrência societária se manifesta como um **Triângulo Fechado ou 3-clique ($K_3$)**: um vértice de sócio controlador que aponta com arestas de propriedade para duas empresas concorrentes, enquanto essas empresas competem diretamente entre si."*

---

```
========================================================================================
SLIDE 5: COMO REDUZIR O GRAFO GIGANTE: OS ALGORITMOS
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- O Problema do "Hairball": 1.788 nós e 3.185 arestas geram um emaranhado denso dominado pelo órgão público.
- O Funil Algorítmico:
  1. Subgrafo Induzido por Arestas (Predicado P(e)) — O(V + E)
  2. Componentes Conexas (Union-Find / BFS) — O(V + E)
  3. Listagem de Triângulos (Triangle Listing) — O(E · d_max)
  4. Poda de 1-Core (Eliminação de nós com Grau = 0)
- Resultado: Redução exata de 1.788 nós para 22 nós de alto risco!
========================================================================================
```
🗣️ **Fala do Apresentador (04:30 - 05:45):**  
*"Quando plotamos inicialmente todos os dados no Gephi, nos deparamos com o clássico 'hairball' — um emaranhado denso. Isso ocorreu porque o órgão municipal atuava como um buraco negro gravitacional, conectando-se a quase todas as empresas pela aresta de participação.*  
*Como contornamos isso estruturalmente? Através de algoritmos formais de grafos: primeiro, extraímos o **Subgrafo Induzido por Arestas de Conluio** em tempo linear $O(V+E)$; em seguida, aplicamos o algoritmo de **Componentes Conexas via Union-Find**, podando todos os nós com grau zero. Por fim, o algoritmo de **Listagem de Triângulos** identifica os ciclos fechados em milissegundos. Esse funil algorítmico reduziu a rede completa de 1.788 nós para exatamente 22 nós críticos."*

---

```
========================================================================================
SLIDE 6: TABELA DE COMPLEXIDADE COMPUTACIONAL
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
| Algoritmo | Papel no Pipeline | Complexidade |
|---|---|:---:|
| Projeção Bipartida Ponderada | Construção de G_E (Jaccard) | O(Σ d(l)²) |
| Componentes Conexas (Union-Find) | Poda de nós limpos e isolamento de cartéis | O(V + E) |
| Listagem de Triângulos | Mineração do motivo K_3 de conluio | O(E · d_max) |
| Louvain (Modularidade) | Detecção não-supervisionada de comunidades | O(V log V) |
- Conclusão Técnica: O pipeline é plenamente escalável para bases estaduais e nacionais.
========================================================================================
```
🗣️ **Fala do Apresentador (05:45 - 06:30):**  
*"Do ponto de vista da Ciência da Computação, a grande força do método é a sua **eficiência assintótica**. Todas as etapas centrais de detecção operam em tempo linear ou quase-linear $O(V+E)$. Isso significa que essa arquitetura não serve apenas para uma monografia com uma cidade: ela tem complexidade teórica apta a processar os milhões de licitantes de todo o estado de Minas Gerais em questão de segundos em um servidor de auditoria contínua."*

---

```
========================================================================================
SLIDE 7: RESULTADOS EXPERIMENTAIS: OS CASOS CRÍTICOS MULTIDIMENSIONAIS
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Tabela Síntese dos Casos de Alto Risco em Divinópolis (2025):
  1. Masif × Joaomed (Score 29.0): Mesma sócia (Katty Gessele) + Mesmo endereço (R. Wilson Lois Koehler Jr, 406) + Mesmo telefone (41 2108-4545).
  2. Dentemed × Odontomaster (Score 22.25): Mesmo sócio (Leonardo Cury) e mesma holding em 59 itens de odontologia.
  3. EGC × GWC (Score 10.25): Mesmo endereço físico (R. Liberdade, 3230 - Bayeux/PB) em certame de eletrônicos.
  4. Ortom × Ortobens (Score 10.0): Mesmo telefone fixo (15 3262-5549) + Sobrenomes raros (Padilha e Viapiana).
  5. Vilson Marra × Alvimar Marra (Score 2.0): Sobrenome composto idêntico em transporte escolar.
  6. AMB Distribuidora × M.H.M. do Couto (Score 2.0): Sobrenomes duplos (Couto e Mori) em materiais hospitalares.
========================================================================================
```
🗣️ **Fala do Apresentador (06:30 - 07:30):**  
*"Vamos agora aos resultados práticos da aplicação em Divinópolis. O algoritmo de interseção isolou 42 pares com vínculos, dos quais **seis alcançaram nível de alerta máximo**.  
Entre eles, destacamos casos de conluio com tríplice evidência: empresas como Masif e Joaomed que operam no mesmo endereço físico, compartilham a mesma linha telefônica e pertencem à mesma sócia; empresas de eletrônicos sediadas no mesmo galpão na Paraíba concorrendo em Minas Gerais; conluios familiares com sobreposição de telefones e sobrenomes raros em materiais hospitalares; e parentesco consanguíneo no transporte escolar."*

---

```
========================================================================================
SLIDE 8: O CASO PARADIGMÁTICO (DENTEMED × ODONTOMASTER) NO GEPHI
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Print da Visualização do Gephi (Layout ForceAtlas 2 isolado).
- Destaque visual das empresas Dentemed e Odontomaster ligadas ao sócio Leonardo Cury.
- Fato Empírico Irrefutável: 59 itens individuais disputados conjuntamente no Processo 208/2025.
- Enquadramento: Violação direta ao Art. 14 da Lei 14.133/2021 e Súmula 222 do TCU.
========================================================================================
```
🗣️ **Fala do Apresentador (07:30 - 08:30):**  
*"O caso mais emblemático descoberto pelo algoritmo é o que vocês veem destacado nesta figura gerada no Gephi. As empresas **Dentemed** e **Odontomaster** disputaram conjuntamente nada menos que **59 itens individuais** da Licitação 1499516 para fornecimento de instrumentais odontológicos.*  
*Ao cruzarmos o grafo, vemos o triângulo perfeito: ambas as empresas pertencem à mesma pessoa física, o empresário Leonardo Antonio Rodrigues Cury, e à mesma holding controladora. Isso configura, juridicamente, concorrência simulada flagrante com cobertura de propostas, tipificada como crime no Artigo 337-F do Código Penal e sumulada pelo TCU."*

---

```
========================================================================================
SLIDE 9: CONCLUSÃO E CONTRIBUIÇÃO ACADÊMICO-INSTITUCIONAL
----------------------------------------------------------------------------------------
[Conteúdo do Slide]:
- Contribuições:
  1. Superação algorítmica da limitação de anonimização da base pública do TCE-MG.
  2. Ponderação onomástica por raridade (IDF) para erradicação de falsos positivos.
  3. Detecção de redes complexas com complexidade linear O(V+E).
- Impacto: Ferramenta pronta para implementação em Tribunais de Contas e Ministérios Públicos.
- Obrigado! Perguntas da Banca.
========================================================================================
```
🗣️ **Fala do Apresentador (08:30 - 10:00):**  
*"Para concluir: este trabalho demonstrou que a modelagem por grafos não é apenas uma teoria elegante, mas sim uma ferramenta de controle social e combate à fraude indispensável. Conseguimos superar a anonimização de dados abertos, controlar falsos positivos com IDF e, com algoritmos de complexidade linear $O(V+E)$, desmascarar fraudes documentadas em certames reais de Divinópolis.*  
*Essa abordagem fornece aos órgãos de controle externo — como o Ministério Público e o Tribunal de Contas — uma capacidade de auditoria preditiva, permitindo barrar a homologação de certames fraudulentos antes que o recurso público seja empenhado.  
Agradeço a atenção de todos e fico à disposição para as perguntas da banca."*

---

## 3. Preparação para as Perguntas da Banca (FAQ)

### Pergunta 1: *"Por que usar grafos e não simplesmente fazer consultas SQL com GROUP BY e JOIN?"*
* **Resposta Ideal:** *"Uma consulta SQL com JOIN resolve apenas relações diretas de 1 salto (ex: mesma empresa e mesmo sócio). Quando entramos em conluios em cadeia — como o Sócio A que é parente do Sócio B, que controla a Empresa C, que disputou com a Empresa D —, as consultas relacionais exigem múltiplos auto-joins recursivos, cujo custo computacional explode para $O(V^k)$. Em grafos, uma busca em largura (BFS) ou componentes conexas resolve caminhos de qualquer distância em tempo linear $O(V+E)$."*

### Pergunta 2: *"Como vocês garantiram que dois 'Silvas' não fossem acusados de cartel?"*
* **Resposta Ideal:** *"Essa foi uma preocupação metodológica central. Implementamos a métrica de frequência inversa (IDF) adaptada para onomástica: sobrenomes de altíssima ocorrência têm peso marginal ($0,25$), insuficiente para disparar alertas sem outros vínculos fortes. Além disso, o algoritmo exige a conjunção de dois fatores: a partilha do sobrenome e a concorrência efetiva no mesmo certame."*

### Pergunta 3: *"A presença do triângulo societário é uma prova jurídica suficiente para anular o certame?"*
* **Resposta Ideal:** *"No âmbito administrativo sim, segundo a jurisprudência pacífica do TCU (Acórdãos 2.143/2007 e 1.793/2011). O TCU estabelece que a participação de empresas com sócios em comum disputando os mesmos itens gera presunção relativa de conluio, invertendo o ônus da prova contra as licitantes com base no Artigo 14 da Nova Lei de Licitações."*

