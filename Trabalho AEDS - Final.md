# **Construção de Ideias e Guia Orientador**

1. # **PERGUNTA INICIAL**

É possível estabelecer/rastrear as relações comerciais entre o Estado e as empresas privadas? Estabelecido o vínculo, é possível classificar esse tipo de relação? Quais métricas podem ser utilizadas para o processo de classificação?  
**Restrição de escopo**: o Estado, nesse contexto, será definido como uma cidade, em particular, Divinópolis. A restrição está associada ao tempo e à maturação da construção do pipeline de análises.

2. # **BANCO DE DADOS**

Existe um portal em que é possível acessar parcialmente os dados referentes aos gastos da prefeitura de Divinópolis, disponível em:

* [https\://transparencia.betha.cloud/\#/oU8BIS7tF8icFMLVMRCkJA==/dados-abertos](https://transparencia.betha.cloud/#/oU8BIS7tF8icFMLVMRCkJA==/dados-abertos)  
  **Esse portal é limitado e não contém todos os dados para análise.**

Um segundo portal de dados está associado ao Tribunal de Contas do Estado de Minas Gerais (TCE-MG), disponível em:

* [https\://dadosabertos.tce.mg.gov.br/\#/public/inicio](https://dadosabertos.tce.mg.gov.br/#/public/inicio)

Esse portal contém os dados: 

* **Dados Jurisdicionados:** são os dados enviados pelas entidades fiscalizadas (prefeituras, câmaras, autarquias, fundações, empresas públicas etc.). Exemplos: balanços contábeis, relatórios de execução orçamentária, informações sobre licitações e contratos. Ou seja, é o que os órgãos públicos prestam contas ao tribunal.  
* **Dados do TCE-MG**: são informações produzidas pelo próprio tribunal, como decisões, acórdãos, relatórios de auditoria, indicadores de fiscalização, estatísticas de processos e julgamentos. Aqui você vê o trabalho do órgão fiscalizador em cima dos dados que recebeu dos jurisdicionados.

**Para o trabalho, usaremos os dados JURISDICIONADOS, que são considerados os dados brutos.**

## **2.1 ENTENDENDO O BANCO DE DADOS**

O banco de dados atual será direcionado ao ano fiscal de 2025, uma vez que está totalmente consolidado. São dispostas 55 tabelas que englobam todo o processo desde a licitação até o empenho final do valor. Os dados são coletados através da plataforma SICOM. O Sistema Informatizado de Contas dos Municípios — Módulo de Acompanhamento Mensal (SICOM/AM) é a plataforma digital oficial mantida pelo Tribunal de Contas do Estado de Minas Gerais (TCE-MG). Por força da Constituição Estadual e das Instruções Normativas do TCE-MG (com destaque para a IN nº 02/2023 para editais e a IN nº 01/2025 para o Acompanhamento Mensal), todos os 853 municípios mineiros são legalmente obrigados a transmitir suas contas públicas em prazos rígidos: 5 (cinco) dias úteis após a publicação de editais e atos de dispensa, e remessa mensal continuada com prazos de reenvio/correção até o último dia do mês subsequente	

## **2.2   ESTRUTURA DO BANCO DE DADOS** 

As 55 tabelas (todas em formato CSV) estão distribuídas em 5 pastas físicas, cada uma responsável por um estágio da administração:

### **1\. Módulo orgao (4 tabelas — 7% da base): Governança e Estrutura**

* **Escopo analítico**: Identificação das entidades e unidades administrativas dotadas de competência legal para a realização de despesas públicas.  
* **Descrição funcional**: Registra a municipalidade no Tribunal de Contas (remessaMunicipio), estrutura os órgãos públicos formais (orgao), desagrega as unidades orçamentárias e secretarias (orgaoUnidade) e armazena a qualificação dos gestores e ordenadores de despesa responsáveis (orgaoResp).

### **2\. Módulo licitacao (24 tabelas — 44% da base): Processos Licitatórios e Aquisições**

* **Escopo analítico**: Mapeamento dos procedimentos administrativos de seleção de fornecedores e contratação pública.  
* **Descrição funcional**: Trata-se do maior conjunto de dados da base, estruturado segundo os regimes legais de contratação:  
  * **Processos Licitatórios Regulares (13 tabelas)**: Contempla certames nas modalidades concorrenciais e pregões (licitacao), especificação dos itens licitados (itemLicitacao), estimativas de preços de mercado (cotacaoLicitacao), documentos de habilitação jurídica e técnica (habLicitacao), julgamento das propostas (julgLicitacao), atos de homologação (homologLicitacao), composição das comissões de contratação (comissaoLicitacao) e quadro societário das empresas participantes (quadroSocLicitacao).  
  * **Contratações Diretas (7 tabelas)**: Engloba casos de dispensa e inexigibilidade de licitação (dispensa), bem como os itens relacionados (itemDispensa), pesquisas de preços prévias (cotDispensa) e fornecedores contratados (fornDispensa).  
  * **Adesões a Atas de Registro de Preços (4 tabelas)**: Registra as adesões do município a atas de registro de preços gerenciadas por outros entes federativos (regadesao, itemRegadeso).

### **3\. Módulo contrato (8 tabelas — 15% da base): Instrumentos Contratuais e Aditivos**

* **Escopo analítico**: Formalização jurídica dos vínculos firmados entre a administração pública e os fornecedores.  
* **Descrição funcional**: Vincula o processo licitatório ao instrumento contratual (contratos), qualifica as partes e representantes legais (contContrato), discrimina o quantitativo e os custos unitários dos itens ajustados (itemContrato), além de registrar alterações qualitativas e quantitativas por termos aditivos (termoContrato), reajustes financeiros (apostContrato) e rescisões contratuais (resContrato).

### **4\. Módulo empenho (8 tabelas — 15% da base): Execução Orçamentária e Reserva de Crédito**

* **Escopo analítico**: Registro e vinculação prévia do crédito orçamentário necessário ao atendimento das obrigações contratadas.  
* **Descrição funcional**: Em conformidade com a Lei Federal nº 4.320/1964, documenta o ato de empenho da despesa (empenho), associando a reserva orçamentária ao credor correspondente (credorEmpenho) e às fontes de recursos específicas (empenhoFonte). Contempla também o controle dos compromissos financeiros inscritos em Restos a Pagar (rsp).

### **5\. Módulo despesa (11 tabelas — 20% da base): Planejamento, Liquidação e Pagamento**

* **Escopo analítico**: Acompanhamento da programação orçamentária e do adimplemento das obrigações até o desembolso financeiro.  
* **Descrição funcional**: Abrange o ciclo de execução da despesa, dividido entre as etapas de planejamento e de liquidação/pagamento:  
  * **Planejamento e Programação Orçamentária**: Controla as dotações fixadas na Lei Orçamentária Anual (despesa) e suas modificações por meio de créditos adicionais e decretos suplementares (decretos, altOrcamentaria).  
  * **Estágios de Execução Financeira**:  
    * **Estágio de Liquidação**: Comprovação do adimplemento da obrigação e recebimento do bem ou serviço (liquidacao), correlacionada aos documentos fiscais e notas fiscais eletrônicas pertinentes (notasfiscais, liquidacaoNfs).  
    * **Estágio de Pagamento**: Emissão das ordens de pagamento (pagamento) e efetivação das movimentações bancárias de débito nas contas do ente público (movPagamento).

O arquivo [estrutura\_diretorio.txt](https://drive.google.com/file/d/1bkumc0pGDsdbex8Qv5_h3sfLllLHdr6I/view?usp=drive_link) contém mais informações.

## 

## **2.3 CICLO BÁSICO DAS COMPRAS PÚBLICAS**

O fluxograma representa o ciclo da despesa pública, desde a previsão orçamentária até o pagamento ao fornecedor.

O processo começa com a fixação e as alterações do orçamento, seguidas pela pesquisa de preços e pela seleção do fornecedor por licitação ou contratação direta. Em seguida, ocorre a formalização da contratação, quando aplicável, e o empenho da despesa, que reserva o crédito orçamentário.Posteriormente, a despesa é liquidada, mediante a verificação do cumprimento da obrigação, com documentação comprobatória, como notas fiscais. Após a liquidação, ocorre o pagamento, que pode ser relacionado às movimentações financeiras para conferência. Se a despesa empenhada não for paga até 31 de dezembro, poderá ser inscrita em restos a pagar, conforme as regras legais.

3. # **POSSÍVEIS PIPELINES DE ANÁLISES**

1. **Fluxo Comportamental e Rodízio de Cartéis (Cadeia de Lances no Tempo):** Analisa a interação entre empresas concorrentes ao longo de múltiplos certames no tempo, tratando a sucessão de disputas como um fluxo relacional:  
* **Cadeia de Relações:** Empresa A (Lance de Cobertura) → Licitação N → Empresa B Vencedora → Licitação N+1 → Empresa A Vencedora (Inversão de Papéis)  
* **O que busca identificar:** Padrões de rodízio de vencedores, propostas de cobertura (*cover bidding*) e divisão velada de mercado entre um grupo fixo de fornecedores.  
1. 

## 

# **Pergunta Central:** 

# Como a análise de grafos pode ser utilizada para identificar padrões anômalos e indicadores de risco nas relações entre municípios, empresas fornecedoras e recursos públicos?

## **Análises:**

## **Essa seria uma boa pergunta norteadora?**

## **Existe algum trabalho que já foi feito?**

##


# **Objetivo:** 

# Desenvolver uma estrutura computacional baseada em grafos para modelar e analisar as relações entre municípios e empresas fornecedoras, identificando padrões de concentração, recorrência e conectividade que possam constituir indicadores de risco em contratações públicas.

1. Padrões de Concentração (Monopólios e Dependência Orçamentária):  
   1. Conceito Pericial: Avalia situações em que determinados fornecedores retêm fatias desproporcionais do orçamento de pastas municipais, asfixiando a concorrência e criando dependência econômica crônica.  
2. Padrões de Recorrência (Fracionamento e Temporalidade):  
   1. Conceito Pericial: Mapeia a repetição sucessiva de contratações diretas destinadas a burlar os limites constitucionais de dispensa licitatória previstos na Lei 14.133/2021.  
3. Padrões de Conectividade (Cartéis e Alcance a Sanções/PEPs):  
   1. Conceito Pericial: Revela redes de conluio entre fornecedores que dividem contratos públicos e rastreia o direcionamento de recursos para empresas impedidas de contratar com o Estado ou ligadas a agentes políticos.  
4. 

