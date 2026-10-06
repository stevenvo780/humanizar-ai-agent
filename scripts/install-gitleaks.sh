#!/usr/bin/env bash
set -euo pipefail
LUMEN_GITLEAKS_VERSION='8.30.1'
LUMEN_GITLEAKS_DESTINATION="${1:?Specify a destination directory}"
LUMEN_GITLEAKS_TEMP=$(mktemp -d)
trap 'rm -rf -- "$LUMEN_GITLEAKS_TEMP"' EXIT
case "$(uname -m)" in
  x86_64) LUMEN_GITLEAKS_ARCH=x64 ;;
  aarch64|arm64) LUMEN_GITLEAKS_ARCH=arm64 ;;
  *) echo 'Unsupported architecture for the Linux CI scanner.' >&2; exit 1 ;;
esac
LUMEN_GITLEAKS_ARCHIVE="gitleaks_${LUMEN_GITLEAKS_VERSION}_linux_${LUMEN_GITLEAKS_ARCH}.tar.gz"
LUMEN_GITLEAKS_BASE="https://github.com/gitleaks/gitleaks/releases/download/v${LUMEN_GITLEAKS_VERSION}"
curl --fail --silent --show-error --location "$LUMEN_GITLEAKS_BASE/$LUMEN_GITLEAKS_ARCHIVE" -o "$LUMEN_GITLEAKS_TEMP/$LUMEN_GITLEAKS_ARCHIVE"
curl --fail --silent --show-error --location "$LUMEN_GITLEAKS_BASE/gitleaks_${LUMEN_GITLEAKS_VERSION}_checksums.txt" -o "$LUMEN_GITLEAKS_TEMP/checksums.txt"
python3 - "$LUMEN_GITLEAKS_TEMP" "$LUMEN_GITLEAKS_ARCHIVE" "$LUMEN_GITLEAKS_DESTINATION" <<'PY'
import hashlib
import sys
import tarfile
from pathlib import Path
temporary, name, destination = sys.argv[1:]
root = Path(temporary)
expected = next(line.split()[0] for line in (root / 'checksums.txt').read_text().splitlines()
                if line.split()[-1] == name)
archive = root / name
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('Gitleaks checksum mismatch.')
with tarfile.open(archive) as bundle:
    binary = bundle.extractfile(bundle.getmember('gitleaks'))
    if binary is None:
        raise SystemExit('Gitleaks binary missing.')
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    executable = target / 'gitleaks'
    executable.write_bytes(binary.read())
    executable.chmod(0o755)
print('Gitleaks verified and installed.')
PY
