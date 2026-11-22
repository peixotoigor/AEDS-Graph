SHELL := /bin/bash
PYTHON_SYS := python3
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
STAMP := $(VENV)/.installed

.PHONY: all setup run step1 step2 step3 clean clean-csv distclean help

all: run

$(STAMP): requirements.txt
	@if [ ! -d "$(VENV)" ]; then \
		echo ">>> Criando ambiente virtual em $(VENV)..."; \
		$(PYTHON_SYS) -m venv $(VENV) || { echo "Erro ao criar .venv. No Ubuntu execute: sudo apt update && sudo apt install -y python3-venv"; exit 1; }; \
	fi
	@echo ">>> Instalando dependências de requirements.txt..."
	$(PIP) install -r requirements.txt
	@touch $(STAMP)

setup: $(STAMP)

step1: $(STAMP)
	@echo ">>> [Etapa 1/3] Executando src/01_limpeza_dados.py..."
	$(PYTHON) src/01_limpeza_dados.py

step2: $(STAMP)
	@echo ">>> [Etapa 2/3] Executando src/02_enriquecimento_socios.py..."
	$(PYTHON) src/02_enriquecimento_socios.py

step3: $(STAMP)
	@echo ">>> [Etapa 3/3] Executando src/03_reduzir_grafo.py..."
	$(PYTHON) src/03_reduzir_grafo.py

run: $(STAMP)
	@echo ">>> [Etapa 1/3] Executando src/01_limpeza_dados.py..."
	$(PYTHON) src/01_limpeza_dados.py
	@echo ">>> [Etapa 2/3] Executando src/02_enriquecimento_socios.py..."
	$(PYTHON) src/02_enriquecimento_socios.py
	@echo ">>> [Etapa 3/3] Executando src/03_reduzir_grafo.py..."
	$(PYTHON) src/03_reduzir_grafo.py
	@echo ">>> Pipeline concluído! Arquivos gerados em results/"

clean:
	@echo ">>> Removendo pasta results/ e caches __pycache__..."
	rm -rf results
	find . -type d -name "__pycache__" -exec rm -rf {} +

clean-csv:
	@echo ">>> Removendo CSVs de results/ (mantendo cache da BrasilAPI)..."
	rm -f results/*.csv

distclean: clean
	@echo ">>> Removendo ambiente virtual $(VENV)..."
	rm -rf $(VENV)

help:
	@echo "Alvos disponíveis:"
	@echo "  make run        - Cria .venv (se necessário), instala dependências e roda as 3 etapas"
	@echo "  make setup      - Apenas cria .venv e instala requirements.txt"
	@echo "  make step1      - Executa apenas src/01_limpeza_dados.py"
	@echo "  make step2      - Executa apenas src/02_enriquecimento_socios.py"
	@echo "  make step3      - Executa apenas src/03_reduzir_grafo.py"
	@echo "  make clean      - Apaga a pasta results/ e __pycache__"
	@echo "  make clean-csv  - Apaga results/*.csv mantendo cache_qsa_brasilapi.json"
	@echo "  make distclean  - Executa clean e remove também .venv/"
