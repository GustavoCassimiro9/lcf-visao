#!/usr/bin/env bash
# Roda o detector com a camera CSI do Raspberry Pi.
cd "$(dirname "$0")"
exec .venv/bin/python olho_aberto_fechado.py csi
