"""Monta a pasta que a Cloudflare Pages publica.

Uso, na raiz do repositório (é o comando de build do projeto na Cloudflare):

    python3 scripts/montar_site_cloudflare.py [SAIDA]

SAIDA é recriada a cada execução (padrão: _site_cloudflare, a pasta de saída
configurada na Cloudflare). Entram os arquivos rastreados pelo git com o mesmo
filtro do Jekyll no GitHub Pages: caminhos com parte iniciada por . _ # ~ e a
lista exclude do _config.yml ficam fora. Assim CLAUDE.md, tests/, scripts/ e
rascunhos não vão para o site. Também fica fora o CNAME, que só serve ao
GitHub Pages. Por fim, entra o _headers (headers de segurança da Cloudflare).
"""
import re
import shutil
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = "_site_cloudflare"
ONLY_GITHUB_PAGES = {"CNAME"}
REQUIRED = ("index.html", "404.html", "ads.txt", "robots.txt", "sitemap.xml")


def exclude_patterns():
    text = (ROOT / "_config.yml").read_text(encoding="utf-8")
    block = re.search(r"^exclude:\n((?:[ \t]+-[^\n]*\n?)+)", text, re.MULTILINE)
    if block is None:
        raise SystemExit("_config.yml sem lista exclude")
    return [line.split("-", 1)[1].strip().strip("'\"") for line in block.group(1).splitlines()]


def published(relative_path, patterns):
    """Mesmo critério de tests/seo/test_publicacao_pages.py (Jekyll 3)."""
    if any(part[:1] in "._#~" for part in relative_path.split("/")):
        return False
    return not any(fnmatch(relative_path, pattern) or relative_path.startswith(pattern) for pattern in patterns)


def tracked_files():
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [path for path in listed.decode("utf-8").split("\0") if path and (ROOT / path).is_file()]


def site_files():
    patterns = exclude_patterns()
    return sorted(
        path for path in tracked_files()
        if published(path, patterns) and path not in ONLY_GITHUB_PAGES
    )


def build(output):
    output = (ROOT / output).resolve()
    if output == ROOT or ROOT not in output.parents:
        raise SystemExit(f"SAIDA tem de ser uma pasta dentro do repositório: {output}")
    if output.exists():
        shutil.rmtree(output)
    files = site_files()
    for relative in files:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    shutil.copy2(ROOT / "_headers", output / "_headers")
    missing = [name for name in REQUIRED if not (output / name).is_file()]
    if missing:
        raise SystemExit(f"faltam na saída: {', '.join(missing)}")
    print(f"{len(files) + 1} arquivos em {output.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)
