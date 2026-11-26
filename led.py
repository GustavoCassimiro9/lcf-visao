"""
LED na protoboard que acende quando os olhos estao abertos.

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
