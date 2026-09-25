#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv --without-pip .venv
CMAKE_ARGS="-DCMAKE_PREFIX_PATH=$PWD/.tools/root/usr" python3 -m pip --python .venv install -r requirements.txt
