#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  stylus/tools/wasm-inspect.sh --probe [--require-language-server]
  stylus/tools/wasm-inspect.sh --wasm <path.wasm> [--out-dir <dir>] [--no-optimize]

Required inspection tools:
  WABT:     wasm-validate, wasm-objdump, wasm2wat
  Binaryen: wasm-opt

Optional editor/static-analysis tool:
  wasm-language-tools executable: wat_server

Required Stylus deployability tool:
  OffchainLabs cargo-stylus executable: cargo-stylus

The script never installs tools and never fetches source. Operators must provide
audited/pinned binaries on PATH.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
default_wasm="$repo_root/stylus/target/wasm32-unknown-unknown/release/degenbot_stylus_core.wasm"
wasm_path="$default_wasm"
out_dir=""
mode="inspect"
optimize=1
require_language_server=0

required_tools=(wasm-validate wasm-objdump wasm2wat wasm-opt cargo-stylus)
language_server_tool="wat_server"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --probe)
      mode="probe"
      shift
      ;;
    --wasm)
      [[ $# -ge 2 ]] || {
        printf 'missing value for --wasm\n' >&2
        exit 64
      }
      wasm_path="$2"
      mode="inspect"
      shift 2
      ;;
    --out-dir)
      [[ $# -ge 2 ]] || {
        printf 'missing value for --out-dir\n' >&2
        exit 64
      }
      out_dir="$2"
      shift 2
      ;;
    --no-optimize)
      optimize=0
      shift
      ;;
    --require-language-server)
      require_language_server=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

have_tool() {
  command -v "$1" >/dev/null 2>&1
}

require_tool() {
  local tool="$1"

  if ! have_tool "$tool"; then
    printf 'missing required tool on PATH: %s\n' "$tool" >&2
    exit 69
  fi
}

probe_tools() {
  local tool

  for tool in "${required_tools[@]}"; do
    require_tool "$tool"
    printf 'ok: %s\n' "$tool"
  done

  if have_tool "$language_server_tool"; then
    printf 'ok: %s\n' "$language_server_tool"
  elif [[ "$require_language_server" -eq 1 ]]; then
    printf 'missing required tool on PATH: %s\n' "$language_server_tool" >&2
    exit 69
  else
    printf 'optional-missing: %s\n' "$language_server_tool"
  fi
}

if [[ "$mode" == "probe" ]]; then
  probe_tools
  exit 0
fi

probe_tools >/dev/null

if [[ ! -f "$wasm_path" ]]; then
  printf 'wasm file not found: %s\n' "$wasm_path" >&2
  printf 'build first: cargo build --manifest-path stylus/core/Cargo.toml --release --target wasm32-unknown-unknown\n' >&2
  exit 66
fi

if [[ -z "$out_dir" ]]; then
  out_dir="$(dirname "$wasm_path")/inspect"
fi
mkdir -p "$out_dir"

base_name="$(basename "$wasm_path" .wasm)"
wat_path="$out_dir/$base_name.wat"
opt_path="$out_dir/$base_name.opt.wasm"
sections_path="$out_dir/$base_name.sections.txt"

wasm-validate "$wasm_path"
wasm-objdump -h "$wasm_path" >"$sections_path"
wasm2wat "$wasm_path" -o "$wat_path"

if [[ "$optimize" -eq 1 ]]; then
  wasm-opt "$wasm_path" -O3 --enable-bulk-memory -o "$opt_path"
fi

printf 'validated: %s\n' "$wasm_path"
printf 'sections:  %s\n' "$sections_path"
printf 'wat:       %s\n' "$wat_path"
if [[ "$optimize" -eq 1 ]]; then
  printf 'optimized: %s\n' "$opt_path"
fi
