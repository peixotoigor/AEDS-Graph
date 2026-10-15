# AEDS-Graph: Análise de Contratações Públicas com Teoria dos Grafos

Estrutura computacional baseada em Teoria dos Grafos para modelagem, rastreamento e identificação pericial de padrões anômalos nas relações comerciais entre a administração municipal de Divinópolis (MG) e empresas privadas no exercício fiscal de 2025 (base SICOM / TCE-MG).

## 📌 Guia Rápido e Documentação
- **Instruções para Agentes de IA:** Veja [AGENTS.md](AGENTS.md)
- **Requisitos e Domínio Pericial:** Veja [docs/requirements.md](docs/requirements.md)
- **Arquitetura do Grafo e Pipeline:** Veja [docs/architecture.md](docs/architecture.md)
- **Guia de Instalação e Execução:** Veja [docs/development.md](docs/development.md)
- **Convenções de Código:** Veja [docs/coding-style.md](docs/coding-style.md)
- **Testes e Validação:** Veja [docs/testing.md](docs/testing.md)

## 🚀 Como Executar

```powershell
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Iniciar laboratório exploratório (Jupyter)
jupyter notebook scripts/DA.ipynb
```
