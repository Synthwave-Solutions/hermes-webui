#!/usr/bin/env python3
"""Install pinned, verified password-manager CLIs into the user's PATH.

Linux ARM64 deployment helper. No accounts are connected and no credentials
are read. Existing commands are preserved; remove an old binary deliberately
before using this helper to replace it.
"""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

OP_VERSION = "2.41.1"
OP_SIGNER = "3FEF9748469ADBE15DA7CA80AC2D62742012EA22"
BW_VERSION = "2026.10.1"
BW_SHA256 = "79ecb3293fb259660961c949d3e32fdab8682b2bcff0f6764ce38a411ca1ac5d"


def download(url, target):
    with urllib.request.urlopen(url, timeout=60) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def install(name, work, destination):
    if shutil.which(name) or (destination / name).exists():
        print(f"{name}: existing installation preserved")
        return
    archive = work / (name + ".zip")
    if name == "op":
        download(f"https://cache.agilebits.com/dist/1P/op2/pkg/v{OP_VERSION}/op_linux_arm64_v{OP_VERSION}.zip", archive)
    else:
        download(f"https://github.com/bitwarden/clients/releases/download/cli-v{BW_VERSION}/bw-linux-arm64-{BW_VERSION}.zip", archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != BW_SHA256:
            raise RuntimeError("Bitwarden download checksum mismatch")
    with zipfile.ZipFile(archive) as source:
        (work / name).write_bytes(source.read(name))
        if name == "op":
            (work / "op.sig").write_bytes(source.read("op.sig"))
    if name == "op":
        key = work / "vendor.asc"
        download("https://downloads.1password.com/linux/keys/1password.asc", key)
        gnupg = work / "gnupg"
        gnupg.mkdir(mode=0o700)
        common = ["gpg", "--batch", "--homedir", str(gnupg)]
        subprocess.run([*common, "--import", str(key)], check=True, capture_output=True)
        verified = subprocess.run([*common, "--status-fd=1", "--verify", str(work / "op.sig"), str(work / "op")],
                                  check=True, capture_output=True, text=True)
        if not any(line.startswith("[GNUPG:] VALIDSIG ") and OP_SIGNER in line.split()
                   for line in verified.stdout.splitlines()):
            raise RuntimeError("Unexpected 1Password signature")
    destination.mkdir(parents=True, exist_ok=True)
    fd, pending = tempfile.mkstemp(prefix=f".{name}-", dir=destination)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write((work / name).read_bytes())
        os.chmod(pending, 0o755)
        os.replace(pending, destination / name)
    finally:
        Path(pending).unlink(missing_ok=True)
    env = {"HOME": str(work), "PATH": str(destination) + os.pathsep + os.environ.get("PATH", "")}
    version = subprocess.check_output([str(destination / name), "--version"], env=env, text=True, timeout=30).strip()
    print(f"{name}: installed {version}")


def main():
    if platform.system() != "Linux" or platform.machine() not in {"aarch64", "arm64"}:
        raise SystemExit("This deployment helper supports Linux ARM64. Use the vendor installer on other platforms.")
    destination = Path.home() / ".local/bin"
    with tempfile.TemporaryDirectory(prefix="synthpulse-vault-cli-") as directory:
        for name in ("op", "bw"):
            install(name, Path(directory), destination)


if __name__ == "__main__":
    main()
