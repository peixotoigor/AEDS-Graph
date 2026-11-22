================================================================================
GUIA EXPLICATIVO E DISCUSSÃO DE RESULTADOS:
PLANILHA results/alertas_vinculos_concorrentes.csv
================================================================================

1. VISÃO GERAL DO ARQUIVO
--------------------------------------------------------------------------------
A planilha `results/alertas_vinculos_concorrentes.csv` é gerada na Etapa 2
do pipeline (`src/02_enriquecimento_socios.py`), após o cruzamento entre:
  (a) As relações de disputa direta em licitações (`Concorreu_Contra`), obtidas
      na Etapa 1 (`src/01_limpeza_dados.py`) a partir dos dados do SICOM/TCE-MG
      (Divinópolis/MG, exercício de 2025); e
  (b) Os dados cadastrais e societários reais (QSA, endereço, telefone e e-mail)
      recuperados da Receita Federal do Brasil via BrasilAPI.

Do universo total de 4.059 pares de empresas que competiram entre si nos
certames (`Concorreu_Contra`), a planilha registra apenas os 202 pares (4,98%)
em que foi identificado ao menos um indício de vínculo societário, familiar ou
operacional (Score > 0), ordenados do maior risco para o menor.


2. DICIONÁRIO DAS COLUNAS DA PLANILHA
--------------------------------------------------------------------------------
1. Empresa_A / Empresa_B:
   CNPJs (14 dígitos, com zeros à esquerda restaurados) das duas empresas que
   participaram simultaneamente da mesma licitação ou disputaram o mesmo item.

2. Nome_A / Nome_B:
   Razão social das respectivas empresas concorrentes.

3. Peso_Concorrencia:
   Quantidade acumulada de coocorrências competitivas entre Empresa_A e
   Empresa_B mapeadas na Etapa 1 (soma de participações na mesma licitação e
   de itens disputados em comum na tabela de julgamento). Valores altos (como
   60 ou 65) indicam que as duas empresas se enfrentaram repetidamente ou em
   dezenas de itens individuais.

4. Socios_Em_Comum:
   Lista dos sócios (pessoas físicas ou jurídicas/holdings) que aparecem no QSA
   de ambas as empresas simultaneamente (separados por " | ").

5. Sobrenomes_Em_Comum:
   Sobrenomes compartilhados entre os sócios pessoas físicas (ou titulares de
   MEI/EI) das duas empresas, após remoção de preposições (DE, DA, DOS, E) e
   sufixos (FILHO, JUNIOR, NETO, etc.).

6. Mesmo_Endereco:
   Endereço completo normalizado (logradouro, número e município/UF), preenchido
   quando Empresa_A e Empresa_B possuem exatamente o mesmo domicílio fiscal na
   Receita Federal.

7. Mesmo_Telefone:
   Número telefônico (com DDD) compartilhado entre as duas empresas na base
   cadastral da Receita Federal.

8. Mesmo_Email:
   Endereço de e-mail compartilhado entre as duas empresas (0 ocorrências na
   base analisada).

9. Mesma_Raiz_CNPJ:
   Valor booleano (`True` / `False`) que indica se Empresa_A e Empresa_B
   compartilham os 8 primeiros dígitos do CNPJ (ou seja, matriz e filial
   disputando a mesma licitação). Na base analisada, todas as 202 linhas
   resultaram em `False`.

10. Motivos_Vinculo:
    Campo textual legível resumindo todos os indícios encontrados para o par
    (separados por " ; "), ideal para inspeção rápida por auditores.

11. Score:
    Pontuação numérica composta que quantifica a força do vínculo estrutural
    entre as concorrentes.

12. Nivel:
    Classificação categórica de prioridade de auditoria (`ALTO`, `MEDIO` ou
    `BAIXO`), derivada do Score e da presença de vínculos objetivos.


3. MODELO DE PONTUAÇÃO (SCORE) E CLASSIFICAÇÃO (NIVEL)
--------------------------------------------------------------------------------
O `Score` de cada par é calculado em `enriquecimento_socios.py` pela soma
ponderada dos seguintes critérios:

  + 10,00 pontos por cada Sócio em comum (`Socios_Em_Comum`)
  + 10,00 pontos se houver Mesma Raiz de CNPJ (`Mesma_Raiz_CNPJ`)
  + 10,00 pontos se houver Mesmo Endereço físico (`Mesmo_Endereco`)
  +  8,00 pontos se houver Mesmo Telefone (`Mesmo_Telefone`)
  +  5,00 pontos se houver Mesmo E-mail (`Mesmo_Email`)
  +  1,00 ponto  por cada Sobrenome Raro em comum
  +  0,25 ponto  por cada Sobrenome Comum em comum (lista de 53 sobrenomes
                 muito frequentes no Brasil, como SILVA, SANTOS, OLIVEIRA, etc.)

Critério de classificação da coluna `Nivel`:
  - ALTO  : possui sócio em comum, mesma raiz de CNPJ, mesmo endereço, mesmo
            telefone OU Score >= 2,00.
  - MEDIO : não atende aos critérios de ALTO e possui 1,00 <= Score < 2,00.
  - BAIXO : possui 0 < Score < 1,00 (coincidência apenas de sobrenomes comuns).

Conexão com os grafos gerados:
  - Grafo Cheio (`grafo_cheio_arestas.csv`): inclui as arestas `Vinculo_Suspeito`
    apenas dos níveis ALTO e MEDIO (6 + 37 = 43 arestas), descartando o nível
    BAIXO para não poluir a rede com homônimos triviais.
  - Subgrafo de Fraudes (`subgrafos_fraudes_arestas.csv`): aplica corte
    `Weight >= 2,0` (`reduzir_grafo.py`), isolando exatamente os 6 pares de
    nível ALTO.


4. SÍNTESE QUANTITATIVA DOS RESULTADOS
--------------------------------------------------------------------------------
- Total de pares de concorrência no município (`Concorreu_Contra`): 4.059
- Total de pares com algum alerta (`alertas_vinculos_concorrentes.csv`): 202 (4,98%)
  * Nível ALTO  :   6 pares ( 2,97% dos alertas | 0,15% das concorrências)
  * Nível MEDIO :  37 pares (18,32% dos alertas | 0,91% das concorrências)
  * Nível BAIXO : 159 pares (78,71% dos alertas | 3,92% das concorrências)

Distribuição exata dos Scores:
  - Score 29,00 :   1 par
  - Score 22,25 :   1 par
  - Score 10,25 :   1 par
  - Score 10,00 :   1 par
  - Score  2,00 :   2 pares
  - Score  1,25 :   3 pares
  - Score  1,00 :  34 pares
  - Score  0,50 :   3 pares
  - Score  0,25 : 156 pares

Ocorrência de vínculos objetivos/cadastrais:
  - Sócios em comum       :  2 pares
  - Mesmo endereço físico :  2 pares
  - Mesmo telefone        :  2 pares
  - Mesma raiz de CNPJ    :  0 pares
  - Mesmo e-mail          :  0 pares
  - Pares com Peso_Concorrencia > 1 (disputa recorrente/múltiplos itens): 77 pares


5. DISCUSSÃO ANALÍTICA DOS RESULTADOS
--------------------------------------------------------------------------------

5.1. Nível ALTO (6 pares) — Casos Críticos de Risco de Conluio
Os 6 casos isolados no topo da planilha concentram evidências objetivas
múltiplas ou laços familiares raros que dificilmente ocorrem por acaso:

  (1) Score 29,00 — Conluio Societário, Domiciliar e de Contato:
      Duas empresas do setor médico-hospitalar possuem a mesma sócia
      controladora, compartilham o mesmo endereço comercial (Curitiba/PR) e o
      mesmo telefone fixo. Embora o `Peso_Concorrencia` seja 1 (encontro em um
      mesmo processo), a sobreposição simultânea de controle societário, sede
      física e telefone configura indício fortíssimo de unidade econômica sob
      dois CNPJs distintos.

  (2) Score 22,25 — Triângulo Societário Duplo (K_3) em Disputa Massiva:
      Duas empresas de equipamentos odontológicos apresentam dois controladores
      em comum (uma mesma pessoa física e uma mesma holding), além de
      `Peso_Concorrencia = 60` (participação no mesmo certame e confronto direto
      em 59 itens). É o caso empiricamente mais expressivo de concorrência
      simulada recorrente em um mesmo processo.

  (3) Score 10,25 — Domicílio Fiscal Compartilhado em Disputa Massiva:
      Duas empresas de informática/eletrônicos possuem `Peso_Concorrencia = 65`
      e funcionam exatamente no mesmo endereço físico (Bayeux/PB), com
      sobrenome comum entre sócios (`COSTA`). Mesmo sem sócio idêntico no QSA,
      a coabitação física somada a 65 pontos de concorrência sugere operação
      coordenada ou divisão societária artificial (por exemplo, entre parentes
      ou laranjas).

  (4) Score 10,00 — Telefone Idêntico + Dois Sobrenomes Raros:
      Duas empresas da área têxtil/hospitalar compartilham o mesmo telefone
      fixo (DDD 15) e dois sobrenomes incomuns (`PADILHA` e `VIAPIANA`),
      indicando forte vínculo familiar e operacional entre os sócios.

  (5) Score 2,00 — Vínculo Familiar Consanguíneo em MEI/EI:
      Dois empresários individuais do setor de transporte escolar compartilham
      o mesmo sobrenome composto de baixa frequência (`CORDEIRO MARRA`). Como
      ambos atuam em nome próprio, há evidência direta de parentesco próximo
      participando do mesmo certame.

  (6) Score 2,00 — Vínculo Familiar Duplo:
      Duas empresas do ramo hospitalar/medicamentos compartilham dois
      sobrenomes menos frequentes (`COUTO` e `MORI`), sugerindo pertencimento ao
      mesmo núcleo familiar.

5.2. Nível MEDIO (37 pares) — Zona Cinzenta e Análise Crítica do Algoritmo
A inspeção manual das 37 linhas de nível `MEDIO` revela dois fenômenos
importantes para a avaliação crítica do método:

  a) Casos que merecem verificação complementar pelo `Peso_Concorrencia`:
     Alguns pares `MEDIO` acumulam disputas muito frequentes (ex.: Score 1,25
     com `Peso_Concorrencia = 59`; Score 1,00 com `Peso_Concorrencia = 65`, 53 e
     34). Embora o vínculo cadastral isolado seja fraco (apenas 1 ou 2
     sobrenomes), a alta repetição de confrontos em dezenas de itens recomenda
     auditoria manual complementar dos lances (ex.: verificar alternância de
     vitórias ou cobertura de preços).

  b) Limitação técnica identificada na extração onomástica (falsos positivos
     por prenomes compostos):
     Como a função de extração de sobrenomes analisa todos os tokens do nome
     exceto o primeiro nome, preposições e sufixos, **segundos nomes muito
     comuns no Brasil** (como `CARLOS`, `JOSE`, `ANTONIO`, `LUIZ`, `MARCIO`,
     `VICTOR`, `CRISTINA`, `APARECIDA`, `AUGUSTO`) não constam na lista
     `SOBRENOMES_COMUNS` e acabaram recebendo peso `1,0` (de sobrenome raro).
     Isso explica grande parte dos 34 pares com `Score = 1,0` no nível `MEDIO`.
     Esse achado valida a escolha do limiar `Score >= 2,0` para o nível `ALTO`
     e para o corte do `subgrafos_fraudes`, que filtrou eficazmente esse ruído
     onomástico sem perder os casos reais.

5.3. Nível BAIXO (159 pares) — Ruído Estatístico Esperado
Quase 79% de toda a planilha (`159` de `202` pares) é composta por alertas de
nível `BAIXO` (`Score = 0,25` em 156 casos e `0,50` em 3 casos), originados
exclusivamente pelo compartilhamento de sobrenomes triviais na população
brasileira (`SILVA`, `SANTOS`, `OLIVEIRA`, `SOUZA`, `FERREIRA`, `PEREIRA`, etc.).
Ainda que existam pares com alto `Peso_Concorrencia` (como 60, 65, 81 ou 93)
que competem nos mesmos grandes pregões de odontologia, informática ou
medicamentos, o compartilhamento isolado de um sobrenome como `SILVA` ou `SANTOS`
não constitui indício robusto de conluio, justificando sua exclusão das
visualizações principais.


6. CONSIDERAÇÕES METODOLÓGICAS E MELHORIAS FUTURAS
--------------------------------------------------------------------------------
1. Natureza indiciária:
   A presença de um par na planilha `alertas_vinculos_concorrentes.csv` não
   comprova fraude de forma isolada; trata-se de um **ranking de priorização**
   para auditoria (triagem inteligente que reduz 4.059 interações competitivas
   para 6 casos prioritários).

2. Aperfeiçoamento onomástico sugerido:
   Incluir uma lista de prenomes comuns (ex.: `CARLOS`, `JOSE`, `ANTONIO`,
   `LUIZ`, `MARIA`, `JOAO`, `PAULO`, `PEDRO`, `MARCOS`, `APARECIDA`,
   `CRISTINA`) ou aplicar a fórmula contínua de IDF (`log(|P| / f(n))`) sobre a
   própria base de sócios mapeados para eliminar os falsos positivos do nível
   `MEDIO`.

3. Cruzamento econômico complementar:
   Para os 6 casos `ALTO` (e os casos `MEDIO` com `Peso_Concorrencia >= 30`), o
   próximo passo natural de auditoria é confrontar as planilhas de propostas e
   homologação (`julgLicitacao.csv` e `homologLicitacao.csv`) para verificar
   sequência temporal de lances, desistências coordenadas e sobrepreço.
================================================================================

