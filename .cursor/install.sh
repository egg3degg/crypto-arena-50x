#!/usr/bin/env bash
set -euo pipefail

cd /workspace

python3 -m pip install --user -r requirements.txt

# Login-shell installs land in ~/.local/bin; expose common CLIs on the default PATH.
for bin in pytest uvicorn fastapi; do
  if [[ -x "${HOME}/.local/bin/${bin}" ]]; then
    sudo ln -sf "${HOME}/.local/bin/${bin}" "/usr/local/bin/${bin}"
  fi
done

# Pytest imports use the legacy `crypto_arena.*` package layout; shim from flat repo root.
mkdir -p crypto_arena
if [[ ! -f crypto_arena/__init__.py ]]; then
  echo '"""Compatibility package for pytest and legacy import paths."""' > crypto_arena/__init__.py
fi
for pkg in core config strategies research learning notifications; do
  ln -sfn "../${pkg}" "crypto_arena/${pkg}"
done

# Pytest does not always add /workspace to sys.path; pin it for agents and CI.
SITE_PACKAGES="$(python3 -c 'import site; print(site.getusersitepackages())')"
echo '/workspace' > "${SITE_PACKAGES}/crypto_arena_workspace.pth"
