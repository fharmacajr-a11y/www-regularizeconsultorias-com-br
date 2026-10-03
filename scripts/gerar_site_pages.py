"""Gera localmente o site como o GitHub Pages publica, com a imagem oficial do build.

Uso, na raiz do repositório:

    python scripts/gerar_site_pages.py SAIDA [--wsl DISTRO]

SAIDA é uma pasta temporária de caminho curto, fora do repositório; ela é
recriada a cada execução. --wsl indica que o Docker roda dentro dessa
distribuição do WSL (no Windows). O script:

1. Monta a árvore que seria commitada agora (arquivos rastreados e novos não
   ignorados, sem os apagados), com um índice temporário: o índice real não muda.
   O export sai com LF, como o checkout do GitHub.
2. Roda ghcr.io/actions/jekyll-build-pages:v1.0.13, a imagem da action usada
   pelo workflow pages-build-deployment, com o mesmo comando do entrypoint.
   Se o `docker pull` falhar, baixa a imagem pela API do registro, confere os
   digests e usa `docker load`.
3. Grava SAIDA/site (o artefato publicado) e SAIDA/build.log.

Depois: PAGES_SITE_DIR=SAIDA/site python -m pytest (ver tests/README.md).
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "actions/jekyll-build-pages"
TAG = "v1.0.13"
IMAGE = f"ghcr.io/{REPOSITORY}:{TAG}"
NWO = "fharmacajr-a11y/www-regularizeconsultorias-com-br"
MANIFEST_TYPES = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))


def git(*args, env=None, binary=False):
    completed = subprocess.run(["git", *args], cwd=ROOT, env=env, capture_output=True, check=True)
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def snapshot(destination):
    """Exporta a árvore que seria commitada, sem tocar no índice real."""
    with tempfile.TemporaryDirectory() as folder:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(folder) / "index"))
        git("read-tree", "HEAD", env=env)
        git("-c", "core.autocrlf=true", "add", "-A", env=env)
        tree = git("write-tree", env=env)
    archive = git("-c", "core.autocrlf=false", "archive", "--format=tar", tree, binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(destination, filter="data")
    return tree


def registry_get(url, token, accept=None):
    headers = {"Authorization": f"Bearer {token}"}
    if accept:
        headers["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300) as response:
        return response.read(), response.headers.get("Content-Type", "").split(";")[0]


def download_image(target):
    """Grava em `target` um tar para `docker load`, conferindo cada digest."""
    base = "https://ghcr.io"
    with urllib.request.urlopen(f"{base}/token?scope=repository:{REPOSITORY}:pull&service=ghcr.io", timeout=60) as response:
        token = json.load(response)["token"]
    manifest_bytes, manifest_type = registry_get(f"{base}/v2/{REPOSITORY}/manifests/{TAG}", token, MANIFEST_TYPES)
    manifest = json.loads(manifest_bytes)
    if "manifests" in manifest:
        entry = next(item for item in manifest["manifests"]
                     if item.get("platform", {}).get("os") == "linux" and item["platform"].get("architecture") == "amd64")
        manifest_bytes, manifest_type = registry_get(f"{base}/v2/{REPOSITORY}/manifests/{entry['digest']}", token, MANIFEST_TYPES)
        manifest = json.loads(manifest_bytes)
    manifest_digest = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    blobs = {manifest_digest: manifest_bytes}
    for descriptor in [manifest["config"], *manifest["layers"]]:
        data, _ = registry_get(f"{base}/v2/{REPOSITORY}/blobs/{descriptor['digest']}", token)
        if "sha256:" + hashlib.sha256(data).hexdigest() != descriptor["digest"]:
            raise SystemExit(f"digest divergente em {descriptor['digest']}")
        blobs[descriptor["digest"]] = data
    path = lambda digest: "blobs/sha256/" + digest.split(":", 1)[1]
    files = {
        "oci-layout": json.dumps({"imageLayoutVersion": "1.0.0"}).encode(),
        "index.json": json.dumps({"schemaVersion": 2, "manifests": [{
            "mediaType": manifest_type, "digest": manifest_digest, "size": len(manifest_bytes),
            "annotations": {"io.containerd.image.name": IMAGE, "org.opencontainers.image.ref.name": TAG},
        }]}).encode(),
        "manifest.json": json.dumps([{
            "Config": path(manifest["config"]["digest"]),
            "RepoTags": [IMAGE],
            "Layers": [path(layer["digest"]) for layer in manifest["layers"]],
        }]).encode(),
        **{path(digest): data for digest, data in blobs.items()},
    }
    with tarfile.open(target, "w") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    print(f"imagem baixada do registro: {manifest_digest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("saida", type=Path)
    parser.add_argument("--wsl", metavar="DISTRO", help="Docker dentro desta distribuição do WSL")
    args = parser.parse_args()

    output = args.saida.resolve()
    if output == ROOT or ROOT in output.parents:
        raise SystemExit("A saída precisa ficar fora do repositório.")
    shutil.rmtree(output, ignore_errors=True)
    (output / "src").mkdir(parents=True)

    # -e executa sem o shell do WSL, que consumiria as barras invertidas dos caminhos.
    prefix = ["wsl.exe", "-d", args.wsl, "-e"] if args.wsl else []
    docker = lambda *command, **options: subprocess.run([*prefix, "docker", *command], **options)
    host_path = (lambda path: subprocess.run([*prefix, "wslpath", "-a", str(path)], capture_output=True, text=True, check=True).stdout.strip()) if args.wsl else str

    tree = snapshot(output / "src")
    print(f"árvore {tree}: {sum(1 for item in (output / 'src').rglob('*') if item.is_file())} arquivos")

    if docker("image", "inspect", IMAGE, capture_output=True).returncode != 0:
        if docker("pull", IMAGE).returncode != 0:
            download_image(output / "image.tar")
            docker("load", "-i", host_path(output / "image.tar"), check=True)
            (output / "image.tar").unlink()
    image_id = docker("image", "inspect", IMAGE, "--format", "{{.Id}}", capture_output=True, text=True, check=True).stdout.strip()
    print(f"imagem {IMAGE} {image_id}")

    environment = {
        "GITHUB_WORKSPACE": "/github/workspace", "INPUT_SOURCE": "src", "INPUT_DESTINATION": "site",
        "INPUT_VERBOSE": "true", "INPUT_FUTURE": "false", "INPUT_BUILD_REVISION": tree,
        "GITHUB_REPOSITORY": NWO, "GITHUB_API_URL": "https://api.github.com",
    }
    variables = [item for key, value in environment.items() for item in ("-e", f"{key}={value}")]
    with open(output / "build.log", "w", encoding="utf-8") as log:
        result = docker("run", "--rm", "-v", f"{host_path(output)}:/github/workspace", *variables, IMAGE,
                        stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print((output / "build.log").read_text(encoding="utf-8")[-3000:])
        raise SystemExit(f"build falhou (código {result.returncode})")
    print(f"site gerado em {output / 'site'}: {sum(1 for item in (output / 'site').rglob('*') if item.is_file())} arquivos")


if __name__ == "__main__":
    sys.exit(main())
