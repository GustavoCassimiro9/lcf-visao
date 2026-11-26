#!/usr/bin/env bash
# Roda o detector com a camera CSI do Raspberry Pi. O LED acende depois de 5 s
# com os olhos abertos e apaga depois de 10 s com os olhos fechados.
#   ./rodar_pi.sh              roda o detector
#   ./rodar_pi.sh testar-led   so pisca o LED 5 vezes, para conferir a ligacao
# Para usar outro pino no LED: LED_GPIO=27 ./rodar_pi.sh
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "Ambiente virtual nao encontrado. Rode antes o instalar_pi.sh."
    exit 1
fi

# Logo depois do instalar_pi.sh o usuario ja esta no grupo gpio, mas a sessao
# aberta ainda nao sabe disso. O sg roda com o grupo sem precisar reiniciar.
if ! id -nG | grep -qw gpio && getent group gpio | cut -d: -f4 | tr ',' '\n' | grep -qx "$(id -un)"; then
    exec sg gpio -c "$(printf '%q ' "$0" "$@")"
fi

if [ "${1:-}" = "testar-led" ]; then
    exec .venv/bin/python led.py
fi
exec .venv/bin/python olho_aberto_fechado.py csi
