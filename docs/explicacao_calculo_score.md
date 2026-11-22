================================================================================
EXPLICAÇÃO COMPLETA DO CÁLCULO DE SCORE, PESOS E CLASSIFICAÇÃO DE RISCO
================================================================================
Arquivos de referência no código:
  - src/01_limpeza_dados.py         (cálculo do Peso_Concorrencia)
  - src/02_enriquecimento_socios.py (extração de atributos, cálculo do Score e Nivel)
  - src/03_reduzir_grafo.py         (corte pelo limiar LIMIAR_SCORE_ALTO_RISCO = 2.0)


--------------------------------------------------------------------------------
1. VISÃO GERAL: O QUE É O SCORE E COMO ELE NASCE
--------------------------------------------------------------------------------
Na Etapa 1 (`data_cleaning.py`), todas as empresas que participaram da mesma
licitação ou disputaram o mesmo item recebem uma aresta do tipo
`Concorreu_Contra` (total de 4.059 pares).

Na Etapa 2 (`enriquecimento_socios.py`), para cada um desses 4.059 pares de
empresas concorrentes (a, b), o algoritmo consulta os dados cadastrais reais
obtidos da Receita Federal (via BrasilAPI) e calcula um Score de Vínculo.

O objetivo do Score é responder:
  "Quão forte é a evidência de que essas duas empresas concorrentes pertencem
   ao mesmo grupo econômico, familiar ou operacional?"

Se Score == 0 (nenhuma sobreposição encontrada), o par é ignorado.
Se Score > 0, o par entra na planilha `alertas_vinculos_concorrentes.csv`
(202 pares encontrados).


--------------------------------------------------------------------------------
2. O QUE ENTRA (E O QUE NÃO ENTRA) NA FÓRMULA
--------------------------------------------------------------------------------
2.1. Jaccard e IDF logarítmico estão no código?
  - Jaccard: NÃO é utilizado no código.
  - Louvain: NÃO é utilizado no código.
  - IDF logarítmico contínuo log(|P| / f(n)): NÃO é utilizado no código. Em seu
    lugar, o código implementa uma heurística discreta binária inspirada no
    princípio de raridade do IDF (peso 0,25 para sobrenomes muito frequentes vs.
    1,00 para os demais).
  - Peso_Concorrencia (quantas vezes disputaram juntas): NÃO entra na soma do
    Score. Ele é guardado como coluna informativa e usado apenas como critério
    de desempate ao ordenar a planilha de alertas do maior para o menor risco.

2.2. Os 6 critérios que formam o Score (`enriquecimento_socios.py`, L73-79 e L316-324):

  Variável no código        | Peso  | Condição para pontuar
  --------------------------+-------+-------------------------------------------
  PESO_SOCIO_EM_COMUM       | 10,00 | Multiplicado pelo nº de sócios em comum
  PESO_MESMA_RAIZ_CNPJ      | 10,00 | Primeiros 8 dígitos do CNPJ idênticos
  PESO_MESMO_ENDERECO       | 10,00 | Mesmo endereço físico normalizado
  PESO_MESMO_TELEFONE       |  8,00 | Mesmo telefone (com DDD) normalizado
  PESO_MESMO_EMAIL          |  5,00 | Mesmo e-mail corporativo (não contábil)
  PESO_SOBRENOME_RARO       |  1,00 | Por sobrenome comum fora da lista trivial
  PESO_SOBRENOME_COMUM      |  0,25 | Por sobrenome comum dentro da lista trivial

Fórmula matemática exata executada pelo código:

  Score(a, b) = 10 * |S(a) ∩ S(b)|
              + 10 * [raiz(a) == raiz(b)]
              + 10 * [end(a)  == end(b)]
              +  8 * [tel(a)  == tel(b)]
              +  5 * [email(a) == email(b)]
              +  soma_{n em N(a) ∩ N(b)} w(n)

  onde:
    - S(x)     = conjunto de sócios (PF, PJ ou titular MEI) da empresa x
    - raiz(x)  = os 8 primeiros dígitos de um CNPJ de 14 dígitos
    - end(x)   = endereço normalizado da empresa x
    - tel(x)   = telefone normalizado da empresa x
    - email(x) = e-mail corporativo normalizado da empresa x
    - N(x)     = conjunto de sobrenomes extraídos dos sócios PF/MEI da empresa x
    - w(n)     = 0,25 se n pertence à lista SOBRENOMES_COMUNS (53 sobrenomes)
                 1,00 caso contrário (sobrenome raro)


--------------------------------------------------------------------------------
3. COMO CADA CAMPO É TRATADO ANTES DA COMPARAÇÃO (FILTROS ANTI-RUÍDO)
--------------------------------------------------------------------------------
Para evitar falsos positivos grosseiros, `enriquecimento_socios.py` aplica
regras específicas de limpeza antes de comparar os campos:

a) Sócios em comum (`socios_por_empresa`):
   - Os nomes dos sócios passam por `normalizar_nome()` (remoção de acentos,
     pontuação e conversão para maiúsculas).
   - No caso de MEI / Empresário Individual (que não possui QSA na Receita),
     o titular é extraído da própria Razão Social removendo dígitos iniciais
     do CPF/CNPJ (`nome_titular_mei()`).

b) Sobrenomes (`extrair_sobrenomes`):
   - Só considera sócios cujo `Tipo_Socio != 'PJ'` (evita que palavras como
     LTDA, S/A ou PARTICIPACOES contem como sobrenome).
   - Remove preposições (`PARTICULAS`: DE, DA, DO, DAS, DOS, E, D, DI, DEL,
     VAN, VON) e sufixos (`SUFIXOS`: FILHO, FILHA, JUNIOR, JR, NETO, NETA,
     SOBRINHO, SOBRINHA, SEGUNDO, TERCEIRO), além de letras isoladas.
   - Descarta o primeiro token (`tokens[0]`, que é o primeiro nome) e guarda o
     restante (`set(tokens[1:])`).
   - Observação importante: segundos prenomes (ex.: CARLOS, JOSE, ANTONIO,
     LUIZ, MARCIO, APARECIDA, CRISTINA) não são descartados por `tokens[1:]` e
     não estão na lista `SOBRENOMES_COMUNS`, recebendo peso 1,00. Isso gera
     alertas de Score 1,00 (nível MEDIO), que são barrados pelo corte >= 2,00.

c) Lista `SOBRENOMES_COMUNS` (53 sobrenomes):
   SILVA, SANTOS, OLIVEIRA, SOUZA, SOUSA, RODRIGUES, FERREIRA, ALVES, PEREIRA,
   LIMA, GOMES, COSTA, RIBEIRO, MARTINS, CARVALHO, ALMEIDA, LOPES, SOARES,
   FERNANDES, VIEIRA, BARBOSA, ROCHA, DIAS, NASCIMENTO, ANDRADE, MOREIRA,
   NUNES, MARQUES, MACHADO, MENDES, FREITAS, CARDOSO, RAMOS, GONCALVES,
   SANTANA, TEIXEIRA, ARAUJO, CASTRO, MELO, PINTO, CAMPOS, CUNHA, REIS, JESUS,
   MOURA, CORREIA, CORREA, BATISTA, FARIA, RESENDE, REZENDE, MIRANDA, TAVARES.

d) Endereço (`normalizar_endereco`):
   - Formato: "{LOGRADOURO}, {NUMERO} - {MUNICIPIO}/{UF}".
   - Exige logradouro diferente de "RUA" genérico e número válido (ignora
     "S/N", "SN", "0" e vazio), evitando falsos positivos por dados incompletos.

e) Telefone (`limpar_telefone`):
   - Mantém apenas os dígitos de `ddd_telefone_1` (ou `ddd_telefone_2` se o
     primeiro estiver vazio). Exige ao menos 8 dígitos e descarta sequências
     iniciadas em "0000".

f) E-mail (`normalizar_email`):
   - Converte para minúsculas e exige "@".
   - Regra anti-falso-positivo: descarta automaticamente qualquer e-mail que
     contenha as palavras `contabil`, `contador`, `contabilidade`, `assessoria`
     ou `escritorio`, pois empresas concorrentes legítimas frequentemente usam
     o mesmo escritório contábil terceirizado.


--------------------------------------------------------------------------------
4. REGRAS DE CLASSIFICAÇÃO (`Nivel`) E FILTRAGEM NOS GRAFOS
--------------------------------------------------------------------------------
Após calcular o `Score`, cada par recebe um `Nivel` (`enriquecimento_socios.py`,
L328-333):

  - ALTO  : se (socios_comuns) OU (mesma_raiz) OU (mesmo_endereco)
            OU (mesmo_telefone) OU (score >= 2.0)
  - MEDIO : senão, se (score >= 1.0)
  - BAIXO : senão (0 < score < 1.0)

Como esse nível controla o que entra em cada grafo:
  1. Planilha `alertas_vinculos_concorrentes.csv`:
     Guarda TODOS os pares com Score > 0 (202 pares: 6 ALTO, 37 MEDIO,
     159 BAIXO).
  2. Grafo Cheio (`grafo_cheio_arestas.csv`):
     Insere como aresta `Vinculo_Suspeito` apenas `Nivel != 'BAIXO'` (6 ALTO +
     37 MEDIO = 43 arestas), usando `Weight = Score`.
  3. Subgrafo Reduzido (`subgrafos_fraudes_arestas.csv`, via `reduzir_grafo.py`):
     Aplica o limiar `LIMIAR_SCORE_ALTO_RISCO = 2.0`, retendo exclusivamente
     arestas `Vinculo_Suspeito` com `Weight >= 2.0` — que correspondem aos
     6 casos de nível ALTO.


--------------------------------------------------------------------------------
5. DEMONSTRAÇÃO PASSO A PASSO DA CONTA NOS 6 CASOS CRÍTICOS (ANONIMIZADOS)
--------------------------------------------------------------------------------
Abaixo está a decomposição aritmética exata de como o código chegou ao Score de
cada um dos 6 casos presentes no subgrafo reduzido:

- Caso 1 (E1-A × E1-B) -> Score = 29,00 [ALTO]
    +10,00 : 1 sócia em comum (S1-Comum)
    +10,00 : mesmo endereço normalizado (Curitiba/PR)
    + 8,00 : mesmo telefone fixo (DDD 41)
    + 1,00 : 1 sobrenome raro compartilhado
    Total  = 29,00

- Caso 2 (E2-A × E2-B) -> Score = 22,25 [ALTO]
    +20,00 : 2 sócios em comum (S2-PF e S2-Holding -> 2 * 10,00)
    + 2,00 : 2 tokens raros compartilhados no nome do sócio PF (2 * 1,00)
    + 0,25 : 1 sobrenome comum compartilhado (1 * 0,25)
    Total  = 22,25

- Caso 3 (E3-A × E3-B) -> Score = 10,25 [ALTO]
    +10,00 : mesmo endereço normalizado (Bayeux/PB)
    + 0,25 : 1 sobrenome comum compartilhado entre S3-A e S3-B
    Total  = 10,25

- Caso 4 (E4-A × E4-B) -> Score = 10,00 [ALTO]
    + 8,00 : mesmo telefone fixo (DDD 15)
    + 2,00 : 2 sobrenomes raros compartilhados entre S4-A1/S4-A2 e S4-B (2 * 1,00)
    Total  = 10,00

- Caso 5 (E5-A × E5-B) -> Score = 2,00 [ALTO]
    + 2,00 : 2 sobrenomes raros compartilhados entre S5-A e S5-B (2 * 1,00)
    Total  = 2,00

- Caso 6 (E6-A × E6-B) -> Score = 2,00 [ALTO]
    + 2,00 : 2 sobrenomes raros compartilhados entre S6-A e S6-B (2 * 1,00)
    Total  = 2,00


--------------------------------------------------------------------------------
6. TEXTO SUGERIDO PARA SUBSTITUIR A SEÇÃO 3.3 DO ARTIGO (FIEL AO CÓDIGO)
--------------------------------------------------------------------------------
Para deixar o artigo 100% alinhado à implementação real, você pode usar a
formulação abaixo na Seção 3.3:

  "Para mitigar falsos positivos decorrentes de homonímia em patronímicos de
   alta frequência no Brasil (como Silva, Santos e Oliveira), implementou-se um
   mecanismo de ponderação onomástica discreta inspirada no conceito de
   Frequência Inversa de Documentos (IDF). Após remover preposições e sufixos
   de agnação, cada sobrenome compartilhado n recebe peso w(n) = 0,25 quando
   pertence a um dicionário de 53 sobrenomes triviais, e w(n) = 1,00 caso
   contrário. Combinando vínculos societários, cadastrais e onomásticos, o
   Escore de Vínculo s(a, b) entre duas empresas concorrentes a e b é definido
   por:

     s(a, b) = 10*|S(a) ∩ S(b)| + 10*[raiz(a) = raiz(b)]
             + 10*[end(a) = end(b)] + 8*[tel(a) = tel(b)]
             + 5*[email(a) = email(b)] + sum_{n ∈ N(a) ∩ N(b)} w(n)

   onde e-mails de domínios ou termos contábeis são previamente filtrados para
   evitar falsos positivos por terceirização fiscal. Pares com sócio, raiz de
   CNPJ, endereço ou telefone idênticos, ou com s(a, b) >= 2,00, são
   classificados no nível de alerta ALTO e retidos na etapa de redução do
   grafo."
================================================================================

