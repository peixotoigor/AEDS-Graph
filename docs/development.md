# Guia de Desenvolvimento e Comandos Operacionais

## 1. Configuração do Ambiente Virtual (Windows / PowerShell)

O projeto requer **Python 3.10 ou superior**. Utilize o ambiente virtual padrão (`venv`) com o arquivo `requirements.txt`:

### Passo 1: Criar o Ambiente Virtual
No diretório raiz do projeto (`AEDS-Graph`):

```powershell
python -m venv .venv
```

### Passo 2: Ativar o Ambiente Virtual
```powershell
.\.venv\Scripts\Activate.ps1
```
> *Caso o PowerShell bloqueie a execução de scripts, execute previamente:*
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Passo 3: Instalar as Dependências
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Fluxo de Trabalho e Execução

### 2.1. Laboratório Exploratório (Jupyter)
Para exploração interativa de tabelas, testes de chaves primárias e prototipação de heurísticas periciais:

```powershell
jupyter notebook scripts/DA.ipynb
```

### 2.2. Execução do Pipeline de Produção (Passo a Passo)

1. **Executar a Ingestão e Geração de Parquet (ETL):**
   ```powershell
   python -m src.etl.builder_tables
   ```
   *Gera `database/2025/processed/nodes.parquet` e `database/2025/processed/edges.parquet`.*

2. **Construir e Exportar o Grafo para o Gephi (`.gexf`):**
   ```powershell
   python -m src.graph.exporter
   ```
   *Gera o arquivo `outputs/rede_divinopolis_2025.gexf`.*

3. **Executar os Detectores de Anomalias e Gerar Relatório:**
   ```powershell
   python -m src.detectors.runner
   ```
   *Executa as heurísticas em `src/detectors/` e grava `outputs/relatorio_risco.md` e `outputs/alertas.json`.*

### 2.3. Execução dos Testes Automatizados
```powershell
pytest tests/ -v
```

---

## 3. Comandos Úteis para Inspeção de Dados Brutos

Como os arquivos em `database/2025/raw/` são volumosos (alguns ultrapassam 15 MB com milhões de registros), **nunca abra os arquivos inteiros sem necessidade**:

### Inspecionar Cabeçalho e Primeiras Linhas (PowerShell)
```powershell
Get-Content -Path "database\2025\raw\SICOM.2025.3122306.licitacao\2025.3122306.licitacao.quadroSocLicitacao.csv" -TotalCount 5
```

### Descobrir a Quantidade de Linhas de um CSV
```powershell
(Get-Content -Path "database\2025\raw\SICOM.2025.3122306.licitacao\2025.3122306.licitacao.licitacao.csv" | Measure-Object -Line).Lines
```
