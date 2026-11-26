"""
LED na protoboard que acende quando os olhos ficam abertos.

Acende depois de 5 s seguidos de olhos abertos e apaga depois de 10 s seguidos
de olhos fechados (ou sem rosto na imagem). Os tempos ficam logo abaixo.

Material: 1 LED, 1 resistor de 220 a 330 ohms e 2 jumpers femea-macho
(a ponta femea vai no pino do Raspberry, a macho na protoboard).

Ligacao (numeracao fisica dos pinos do Raspberry Pi):
    pino 11 (GPIO17) -> resistor -> perna LONGA do LED (+)
    pino 9  (GND)    -> perna CURTA do LED (-)

Para conferir a ligacao, rode este arquivo sozinho e o LED pisca 5 vezes:
    ./rodar_pi.sh testar-led
"""
import os
import time

# Numeracao BCM (a do "GPIO17"), nao a do pino fisico.
# Para usar outro pino sem mexer no codigo: LED_GPIO=27 ./rodar_pi.sh
PINO_LED = int(os.environ.get("LED_GPIO", "17"))

# Atrasos do LED, em segundos
ATRASO_LIGAR = 5.0      # olhos abertos por 5 s seguidos -> acende
ATRASO_DESLIGAR = 10.0  # olhos fechados (ou sem rosto) por 10 s seguidos -> apaga
# Interrupcoes mais curtas que isto nao zeram a contagem. Sem essa folga, as
# piscadas normais (a cada 3 ou 4 s) zerariam os 5 s e o LED nunca acenderia.
TOLERANCIA = 1.0


def criar_led():
    """Devolve o LED, ou None quando nao da para usar o GPIO (no PC, por exemplo)."""
    try:
        from gpiozero import LED
    except ImportError:
        print("gpiozero nao instalado: rodando sem o LED.")
        return None
    try:
        return LED(PINO_LED)
    except Exception as erro:  # fora do Raspberry, sem permissao no GPIO, pino ocupado...
        print(f"Nao foi possivel usar o LED no GPIO{PINO_LED}: {erro}")
        return None


class ControleLed:
    """Decide quando o LED acende ou apaga, com os atrasos acima.

    O led pode ser None (sem GPIO, no PC): o estado e acompanhado do mesmo jeito.
    """

    def __init__(self, led):
        self.led = led
        self.aceso = False
        self._mudando_desde = None       # desde quando os olhos pedem a troca do LED
        self._interrompido_desde = None  # desde quando essa troca foi interrompida

    def atualizar(self, olhos_abertos, agora):
        """Recebe o estado dos olhos neste quadro. Devolve True se o LED trocou."""
        if olhos_abertos != self.aceso:
            self._interrompido_desde = None
            if self._mudando_desde is None:
                self._mudando_desde = agora
            elif agora - self._mudando_desde >= self._atraso():
                self._trocar()
                return True
        elif self._mudando_desde is not None:
            # Os olhos voltaram ao estado do LED: so cancela a troca se durar mais
            # que a tolerancia (uma piscada, por exemplo, nao cancela)
            if self._interrompido_desde is None:
                self._interrompido_desde = agora
            elif agora - self._interrompido_desde > TOLERANCIA:
                self._mudando_desde = self._interrompido_desde = None
        return False

    def faltam(self, agora):
        """Segundos ate o LED trocar, ou None se nao ha troca em andamento."""
        if self._mudando_desde is None:
            return None
        return max(0.0, self._atraso() - (agora - self._mudando_desde))

    def _atraso(self):
        return ATRASO_DESLIGAR if self.aceso else ATRASO_LIGAR

    def _trocar(self):
        self.aceso = not self.aceso
        self._mudando_desde = self._interrompido_desde = None
        if self.led is not None:
            if self.aceso:
                self.led.on()
            else:
                self.led.off()


def piscar(vezes=5):
    led = criar_led()
    if led is None:
        raise SystemExit(1)
    print(f"Piscando o LED no GPIO{PINO_LED} {vezes} vezes...")
    for _ in range(vezes):
        led.on()
        time.sleep(0.5)
        led.off()
        time.sleep(0.5)
    led.close()
    print("Se o LED nao piscou, confira a ligacao e se a perna longa esta do lado do resistor.")


if __name__ == "__main__":
    piscar()
