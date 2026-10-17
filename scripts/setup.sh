#!/bin/sh
# Small bootstrap only. The Python setup CLI owns all installation decisions.
set -eu
case " $* " in
  *" --client "*) ;;
  *) printf '%s\n' 'Usage: sh scripts/setup.sh install --client <client> --yes' >&2; exit 2 ;;
esac
git_command=$(command -v git) || { printf '%s\n' 'Install Git first.' >&2; exit 1; }
uv_command=$(command -v uv) || { printf '%s\n' 'Install uv first.' >&2; exit 1; }
case "$(uname -s)" in
  Darwin) managed_base="$HOME/Library/Application Support/hercules-mcp" ;;
  *) managed_base="${XDG_DATA_HOME:-$HOME/.local/share}/hercules-mcp" ;;
esac
mkdir -p "$managed_base/releases"
bootstrap_path=$(mktemp -d "$managed_base/releases/bootstrap-XXXXXXXX")
# mktemp chooses a permanent release slot, not a venv we later relocate.
trap 'printf "Bootstrap retained at %s; reuse this environment.\n" "$bootstrap_path" >&2' EXIT
trap 'exit 130' HUP INT TERM
printf 'Preparing setup at %s (source and locked Python dependencies only).\n' "$bootstrap_path" >&2
"$git_command" clone --quiet https://github.com/0xMihirK/hercules-mcp.git "$bootstrap_path"
"$git_command" -C "$bootstrap_path" rev-parse HEAD >&2
"$uv_command" sync --locked --project "$bootstrap_path"
exec "$bootstrap_path/.venv/bin/hercules-setup" "$@"
