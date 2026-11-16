#!/usr/bin/env python3
"""Orquestrador principal do pipeline AEDS-Graph (Linux Ubuntu 24.04 / Windows).

Executa de ponta a ponta os três eixos analíticos em grafos sobre os dados do
SICOM/TCE-MG (Divinópolis/MG, 2025) e, opcionalmente, regenera as figuras estilo
Gephi (ForceAtlas2) e compila o artigo LaTeX em `report/main.pdf`.

Uso recomendado (terminal Ubuntu 24.04):
    python3 run_pipeline.py --offline --with-graphs
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ETAPAS_ANALITICAS = [
    ("E1.1 Saneamento SICOM (Base Societária)", "scripts/01_analise_socios/01_limpeza_dados.py"),
    ("E1.2 Enriquecimento QSA (BrasilAPI / Cache)", "scripts/01_analise_socios/02_enriquecimento_socios.py"),
    ("E1.3 Redução 1-Core + Union-Find + K3", "scripts/01_analise_socios/03_reduzir_grafo.py"),
    ("E1.4 Materialidade Financeira e Triagem Onomástica", "scripts/01_analise_socios/04_materialidade_financeira.py"),
    ("E2.1 Preparação de Disputas (P -> V)", "scripts/02_rodizio_cover_bidding/01_preparar_disputas.py"),
    ("E2.2 Dígrafo de Rodízio, Ciclos C3/C4 e Tarjan SCC", "scripts/02_rodizio_cover_bidding/02_analise_rodizio.py"),
    ("E3.1 Saneamento de Empenhos e Liquidações", "scripts/03_concentracao_orcamentaria/01_preparar_empenhos.py"),
    ("E3.2 Grafo Bipartido, HHI, Entropia e PageRank", "scripts/03_concentracao_orcamentaria/02_analise_concentracao.py"),
]


def executar_script(nome: str, rel_path: str, offline: bool = False) -> float:
    caminho = ROOT / rel_path
    if not caminho.exists():
        raise FileNotFoundError(f"Script não encontrado: {caminho}")

    cmd = [sys.executable, str(caminho)]
    if offline and caminho.name == "02_enriquecimento_socios.py":
        cmd.append("--offline")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("MPLBACKEND", "Agg")
    if offline:
        env["AEDS_OFFLINE"] = "1"

    print(f"\n{'=' * 72}\n[EXECUTANDO] {nome}\n -> {' '.join(cmd)}\n{'=' * 72}")
    t0 = time.perf_counter()
    res = subprocess.run(cmd, cwd=str(ROOT), env=env)
    dt = time.perf_counter() - t0
    if res.returncode != 0:
        raise RuntimeError(f"Falha na etapa '{nome}' (código {res.returncode}).")
    print(f"[OK] {nome} concluída em {dt:.3f} s")
    return dt


def compilar_artigo_pdf() -> float:
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if not pdflatex or not bibtex:
        print("[AVISO] pdflatex/bibtex não encontrados no PATH; pulando compilação PDF.")
        return 0.0

    report_dir = ROOT / "report"
    t0 = time.perf_counter()
    comandos = [
        [pdflatex, "-interaction=nonstopmode", "main.tex"],
        [bibtex, "main"],
        [pdflatex, "-interaction=nonstopmode", "main.tex"],
        [pdflatex, "-interaction=nonstopmode", "main.tex"],
    ]
    for cmd in comandos:
        res = subprocess.run(cmd, cwd=str(report_dir))
        if res.returncode != 0:
            raise RuntimeError(f"Falha ao executar {' '.join(cmd)} em {report_dir}.")
    dt = time.perf_counter() - t0
    print(f"[OK] Artigo compilado em {report_dir / 'main.pdf'} ({dt:.3f} s)")
    return dt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa o pipeline completo AEDS-Graph (Divinópolis/MG 2025)."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Usa exclusivamente o cache local da BrasilAPI sem requisições HTTP externas.",
    )
    parser.add_argument(
        "--with-graphs",
        action="store_true",
        help="Regenera as visualizações estilo Gephi (ForceAtlas2) em outputs/figuras/ e report/figures/.",
    )
    parser.add_argument(
        "--with-html-viz",
        action="store_true",
        help="Regenera também o fluxograma HTML->PDF/PNG e painel de fluxo (requer Chromium/Chrome).",
    )
    parser.add_argument(
        "--compile-pdf",
        action="store_true",
        help="Recompila report/main.pdf via pdflatex + bibtex.",
    )
    args = parser.parse_args()

    tempos: list[tuple[str, float]] = []
    t_total = time.perf_counter()

    for nome, rel_path in ETAPAS_ANALITICAS:
        dt = executar_script(nome, rel_path, offline=args.offline)
        tempos.append((nome, dt))

    if args.with_html_viz:
        for nome, rel_path in [
            ("V1 Fluxograma Metodológico", "scripts/04_visualizacoes/gerar_fluxograma_metodologia.py"),
            ("V2 Painel Fluxo Financeiro", "scripts/04_visualizacoes/gerar_paineis_eixos.py"),
        ]:
            dt = executar_script(nome, rel_path, offline=args.offline)
            tempos.append((nome, dt))

    if args.with_graphs:
        dt = executar_script(
            "V3 Grafos Reais Gephi / ForceAtlas2",
            "scripts/04_visualizacoes/gerar_grafos_gephi.py",
            offline=args.offline,
        )
        tempos.append(("V3 Grafos Reais Gephi / ForceAtlas2", dt))

    if args.compile_pdf:
        dt = compilar_artigo_pdf()
        if dt > 0:
            tempos.append(("Compilação LaTeX (main.pdf)", dt))

    total = time.perf_counter() - t_total
    print(f"\n{'=' * 72}\nRESUMO DE EXECUÇÃO AEDS-Graph ({'OFFLINE' if args.offline else 'ONLINE/CACHE'})\n{'=' * 72}")
    for nome, dt in tempos:
        print(f"  - {nome:<52} {dt:7.3f} s")
    print(f"  {'TEMPO TOTAL':<52} {total:7.3f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
