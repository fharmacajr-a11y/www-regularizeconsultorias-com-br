"""Identificação do ambiente no cabeçalho do pytest."""
import subprocess

from support import FONT_FILE, ROOT, SITE_DIR


def _head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"


def _environment():
    origem = "fonte (working tree)" if SITE_DIR == ROOT else "artefato (PAGES_SITE_DIR)"
    return [
        f"site dos testes de navegador: {origem} — {SITE_DIR}",
        f"HTML lido pelos testes estáticos: {ROOT} (HEAD {_head()})",
        "rede do navegador: só 127.0.0.1; AdSense e outros domínios abortados; "
        f"Google Fonts servido pela Inter local ({FONT_FILE.name})",
    ]


def pytest_report_header(config):
    return _environment()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    # Repete no fim, porque o cabeçalho some com -q.
    terminalreporter.section("ambiente dos testes")
    for line in _environment():
        terminalreporter.write_line(line)
