#!/usr/bin/env bash
# Instala o projeto do zero no Raspberry Pi.
#
# Rode com:
#   curl -fsSL https://raw.githubusercontent.com/GustavoCassimiro9/lcf-visao/main/instalar_pi.sh | bash
#
# O que ele faz:
#   1. instala os pacotes do sistema
#   2. apaga a pasta ~/lcf-visao antiga
#   3. clona o projeto de novo
#   4. cria o ambiente virtual com Python 3.12 (a mediapipe que roda no Pi 3
#      nao tem versao para o Python 3.13 do sistema) e instala as dependencias
set -e

PASTA="$HOME/lcf-visao"
REPO="https://github.com/GustavoCassimiro9/lcf-visao.git"

echo
echo "==> 1/4 Instalando pacotes do sistema (pode pedir sua senha)"
sudo apt update
sudo apt install -y git curl rpicam-apps libgl1 libglib2.0-0

echo
echo "==> 2/4 Apagando o projeto antigo em $PASTA"
cd "$HOME"
rm -rf "$PASTA"

echo
echo "==> 3/4 Clonando o projeto"
git clone "$REPO" "$PASTA"
cd "$PASTA"

echo
echo "==> 4/4 Criando o ambiente virtual com Python 3.12 (demora alguns minutos)"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

echo
echo "Testando a camera:"
rpicam-hello --list-cameras || true

echo
echo "Pronto! Para rodar, na area de trabalho do Pi (nao por SSH):"
echo "    ~/lcf-visao/rodar_pi.sh"
