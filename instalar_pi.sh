#!/usr/bin/env bash
# Instala (ou reinstala do zero) o projeto no Raspberry Pi, com o LED.
#
# Rode com:
#   curl -fsSL https://raw.githubusercontent.com/GustavoCassimiro9/lcf-visao/main/instalar_pi.sh | bash
#
# O que ele faz:
#   1. desinstala a versao anterior (para o detector e apaga ~/lcf-visao com o ambiente virtual)
#   2. instala os pacotes do sistema
#   3. clona o projeto de novo
#   4. cria o ambiente virtual com Python 3.12 (a mediapipe que roda no Pi 3
#      nao tem versao para o Python 3.13 do sistema) e instala as dependencias,
#      incluindo a gpiozero para controlar o LED
#   5. libera o GPIO para o seu usuario
#   6. mostra como ligar o LED na protoboard e pisca ele para testar
#
# Pode rodar quantas vezes quiser: cada vez comeca do zero.
set -euo pipefail

PASTA="$HOME/lcf-visao"
REPO="https://github.com/GustavoCassimiro9/lcf-visao.git"
PINO_LED="${LED_GPIO:-17}"
USUARIO="$(id -un)"

echo
echo "==> 1/6 Desinstalando a versao anterior"
# Um detector ainda aberto segura a camera e o pino do LED
pkill -f olho_aberto_fechado.py 2>/dev/null && echo "Detector antigo encerrado." || true
cd "$HOME"
rm -rf "$PASTA"
echo "Pasta $PASTA (com o ambiente virtual antigo) apagada."

# Configuracao antiga no boot usando o mesmo pino brigaria com o LED
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if [ -f "$CONFIG" ] && grep -nE "^[^#]*gpio[a-z_]*=${PINO_LED}([^0-9]|$)" "$CONFIG"; then
    echo "AVISO: a(s) linha(s) acima de $CONFIG usam o GPIO${PINO_LED}, o mesmo do LED."
    echo "       Comente com # (sudo nano $CONFIG) e reinicie o Pi, ou use outro pino com LED_GPIO."
fi

echo
echo "==> 2/6 Instalando pacotes do sistema (pode pedir sua senha)"
sudo apt update
sudo apt install -y git curl rpicam-apps libgl1 libglib2.0-0
# Para compilar a lgpio (acesso ao GPIO) caso nao exista pacote pronto.
# Se falhar, a gpiozero usa o acesso nativo do Pi 3 e o LED funciona igual.
sudo apt install -y build-essential swig liblgpio-dev \
    || echo "AVISO: nao deu para instalar as ferramentas da lgpio; seguindo sem elas."

echo
echo "==> 3/6 Clonando o projeto"
git clone "$REPO" "$PASTA"
cd "$PASTA"
chmod +x instalar_pi.sh rodar_pi.sh

echo
echo "==> 4/6 Criando o ambiente virtual com Python 3.12 (demora alguns minutos)"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python lgpio \
    || echo "AVISO: lgpio nao instalou; a gpiozero vai usar o acesso nativo ao GPIO."

echo
echo "==> 5/6 Liberando o GPIO para o usuario $USUARIO"
if ! getent group gpio >/dev/null; then
    echo "AVISO: o grupo gpio nao existe neste sistema; se o LED nao acender, rode como root."
elif id -nG "$USUARIO" | grep -qw gpio; then
    echo "O usuario $USUARIO ja esta no grupo gpio."
else
    sudo usermod -aG gpio "$USUARIO"
    echo "Usuario $USUARIO adicionado ao grupo gpio (o rodar_pi.sh ja usa isso sem precisar reiniciar)."
fi

echo
echo "==> 6/6 Ligacao do LED"
cat <<TEXTO

  Material: 1 LED, 1 resistor de 220 a 330 ohms (nunca ligue o LED sem ele)
  e 2 jumpers femea-macho (ponta femea no pino do Raspberry, macho na protoboard).

    Raspberry Pi                          Protoboard
    pino 11 (GPIO${PINO_LED}) --jumper--> resistor --> perna LONGA do LED (+)
    pino 9  (GND)    --jumper--------------------> perna CURTA do LED (-)

  Achando os pinos: o pino 1 fica na ponta da barra de pinos oposta as portas
  USB. Os pinos impares ficam na fileira de dentro (virada para o meio da placa):
  contando a partir do pino 1, o pino 9 e o 5o dessa fileira e o pino 11 e o 6o.
  Cuidado para o jumper nao encostar nos pinos 2 e 4 (5V, fileira da beirada).
  O desenho da placa abaixo mostra a mesma coisa.
TEXTO
if [ "$PINO_LED" != "17" ]; then
    echo "  (Voce escolheu LED_GPIO=$PINO_LED: use esse GPIO no lugar do pino 11.)"
fi
.venv/bin/pinout 2>/dev/null || true

echo
# Com "curl | bash" a entrada do script e o proprio curl, entao a resposta vem do terminal
if (exec </dev/tty) 2>/dev/null; then
    read -r -p "Monte o circuito e aperte Enter para testar o LED (ou p + Enter para pular): " resposta </dev/tty
    if [ "$resposta" != "p" ]; then
        LED_GPIO="$PINO_LED" ./rodar_pi.sh testar-led \
            || echo "AVISO: o teste do LED falhou; veja a mensagem acima."
    fi
else
    echo "Sem terminal para confirmar; teste depois com: ~/lcf-visao/rodar_pi.sh testar-led"
fi

echo
echo "Testando a camera:"
rpicam-hello --list-cameras || true

echo
echo "Pronto! Para rodar (o LED acende apos 5 s de olhos abertos e apaga apos 10 s fechados):"
echo "    ~/lcf-visao/rodar_pi.sh              # detector (na area de trabalho abre a janela;"
echo "                                         #  por SSH roda sem janela, saia com Ctrl+C)"
echo "    ~/lcf-visao/rodar_pi.sh testar-led   # so pisca o LED para conferir a ligacao"
