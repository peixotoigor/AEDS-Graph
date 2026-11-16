#!/usr/bin/env bash
set -euo pipefail

# Script de configuração e execução para Linux (Ubuntu 24.04)
# Uso:
#   chmod +x run_ubuntu.sh
#   ./run_ubuntu.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== [1/4] Verificando Python 3 e venv no Ubuntu 24.04 ==="
if ! command -v python3 >/dev/null 2>&1; then
  echo "Erro: python3 não encontrado. Instale com: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Criando ambiente virtual em .venv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "=== [2/4] Instalando dependências (requirements.txt) ==="
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "=== [3/4] Executando pipeline completo (modo cache offline + grafos ForceAtlas2) ==="
export PYTHONUTF8=1
export MPLBACKEND=Agg
python run_pipeline.py --offline --with-graphs "$@"

echo "=== [4/4] Concluído! Saídas geradas em outputs/ e database/2025/processed/ ==="
