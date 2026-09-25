#!/usr/bin/env bash
# Use the locally extracted Ubuntu ARM64 package, without a system install.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
loader_root="$repo_dir/build/fpga_tools/root"
if [[ ! -x "$loader_root/usr/bin/openFPGALoader" ]]; then
    echo "Local openFPGALoader is missing; see docs/FPGA_BRINGUP.md." >&2
    exit 1
fi
export LD_LIBRARY_PATH="$loader_root/usr/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$loader_root/usr/bin/openFPGALoader" "$@"
