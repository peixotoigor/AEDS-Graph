# Testes e Validação de Grafos

## 1. Objetivo dos Testes
Os testes automatizados em `tests/` garantem a **corretude matemática e estrutural do grafo**, a integridade das transformações do ETL e a acurácia dos algoritmos de detecção de anomalias periciais.

---

## 2. Invariantes Estruturais do Grafo

Qualquer rotina que gere ou manipule o grafo heterogêneo deve satisfazer as seguintes propriedades invariantes:

1. **Ausência de Arestas Órfãs:**
   - Para toda aresta $e = (u, v) \in E$, tanto $u$ quanto $v$ devem existir previamente no conjunto de nós $V$.
2. **Tipagem Consistente de Nós e Arestas:**
   - Arestas do tipo `SOCIO_DE` só podem conectar nós de origem do tipo `Socio` a nós de destino do tipo `Empresa`.
   - Arestas do tipo `DISPUTOU` ou `VENCEU` só podem conectar nós de origem do tipo `Empresa` a nós de destino do tipo `Licitacao`.
   - Arestas do tipo `PAGOU` ou `CONTRATOU` só podem conectar nós de origem do tipo `Orgao` a nós de destino do tipo `Empresa`.
3. **Consistência de Pesos Financeiros:**
   - Os pesos de arestas representando valores empenhados, liquidados ou propostos devem ser estritamente não-negativos ($\text{weight} \ge 0.0$).
4. **Identificadores Únicos Determinísticos:**
   - Não devem existir nós duplicados com o mesmo identificador na lista de nós (`nodes.parquet`).

---

## 3. Testes com Grafos Sintéticos de Referência (Casos-Controle)

Para validar a sensibilidade e especificidade das heurísticas periciais em `src/detectors/`, a suíte de testes utiliza **grafos sintéticos controlados** (*benchmark fixtures*):

### Caso 1: Teste Positivo de Conluio (Cartel com Sócio Compartilhado)
- **Topologia:**
  - 1 nó `Licitacao` ($L_1$).
  - 3 nós `Empresa` ($E_1, E_2, E_3$) todos com arestas `DISPUTOU -> L_1`.
  - 1 nó `Socio` ($S_1$) com arestas `SOCIO_DE -> E_1` e `SOCIO_DE -> E_2`.
- **Comportamento Esperado:**
  - O detector `SharedPartnersDetector` deve identificar obrigatoriamente o par $(E_1, E_2)$ como anômalo de alto risco, e excluir $E_3$ do conluio societário.

### Caso 2: Teste Negativo (Concorrência Sadia / Caso-Controle)
- **Topologia:**
  - 1 nó `Licitacao` ($L_2$).
  - 3 nós `Empresa` com sócios independentes e sem histórico prévio de propostas idênticas.
- **Comportamento Esperado:**
  - O detector deve retornar 0 alertas para o certame $L_2$.

---

## 4. Estrutura de Diretórios de Testes

```text
tests/
├── conftest.py               # Fixtures do pytest (grafos sintéticos e amostras de dados)
├── test_etl.py               # Testes de sanitização de CNPJ/CPF e parsing de valores
├── test_graph_invariants.py  # Verificação formal de invariantes (arestas órfãs, tipos)
└── test_detectors.py         # Testes de detecção de conluio e monopólio nos grafos sintéticos
```

---

## 5. Como Executar os Testes

```powershell
# Execução completa com saída detalhada
pytest tests/ -v

# Executar apenas testes de invariantes de grafos
pytest tests/test_graph_invariants.py -v

# Executar testes verificando cobertura de código
pytest --cov=src tests/
```
