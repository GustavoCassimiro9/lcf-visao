"""
Detecta pela webcam se os olhos estao abertos ou fechados.

Usa o Face Landmarker do MediaPipe para achar os pontos do rosto e calcula
o EAR (Eye Aspect Ratio), que e a razao entre a altura e a largura do olho:
    olho aberto  -> EAR alto  (em torno de 0.25 a 0.35)
    olho fechado -> EAR baixo (abaixo de 0.20)

No Raspberry Pi, um LED ligado no GPIO17 acende com os olhos abertos e apaga
com os olhos fechados ou sem rosto na imagem (a ligacao esta em led.py).

Uso:
    python olho_aberto_fechado.py                               # webcam do PC
    python olho_aberto_fechado.py http://192.168.0.10:8080/video  # celular
    python3 olho_aberto_fechado.py csi                            # camera CSI do Raspberry Pi

Pressione 'q' ou ESC para sair. Sem tela (por SSH, por exemplo) roda sem a
janela, mostrando o estado so no LED e no terminal; nesse caso saia com Ctrl+C.
"""
import os
import subprocess
import sys
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

from led import criar_led

PASTA = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(PASTA, "face_landmarker.task")
URL_MODELO = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# Indices dos pontos de cada olho na malha de 478 pontos do MediaPipe,
# na ordem p1..p6 usada no calculo do EAR:
#   p1 e p4 = cantos do olho
#   p2 e p3 = palpebra de cima, p6 e p5 = palpebra de baixo
OLHO_1 = [33, 160, 158, 133, 153, 144]
OLHO_2 = [362, 385, 387, 263, 373, 380]

# Abaixo deste valor o olho e considerado fechado.
# Sorrir aperta o olho e o EAR cai para ~0.20, por isso o limiar fica um pouco abaixo.
# Se errar com voce, olhe o EAR mostrado na tela e ajuste.
LIMIAR_EAR = 0.18

# Resolucao da captura. 640x480 e suficiente e mais leve que HD.
LARGURA_CAPTURA, ALTURA_CAPTURA = 640, 480

# Largura da imagem enviada ao MediaPipe. Reduzir deixa mais rapido em
# computadores fracos (como o Raspberry Pi 3). A tela continua em 640x480.
# Se o rosto nao for detectado de longe, aumente (ou use 640 para nao reduzir).
LARGURA_DETECCAO = 320


class CameraRpicam:
    """Le a camera CSI pelo programa rpicam-vid, sem precisar da Picamera2.

    Usado quando a Picamera2 nao esta disponivel (por exemplo, num ambiente
    com uma versao de Python diferente da do sistema). Funciona como o
    cv2.VideoCapture: read() devolve (ok, frame) e release() encerra.
    """

    def __init__(self, largura, altura):
        self.largura, self.altura = largura, altura
        self.tamanho = largura * altura * 3 // 2  # bytes de um quadro YUV420
        self.processo = subprocess.Popen(
            ["rpicam-vid", "-t", "0", "-n", "--codec", "yuv420",
             "--width", str(largura), "--height", str(altura),
             "--framerate", "15", "-o", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def read(self):
        dados = self.processo.stdout.read(self.tamanho)
        if len(dados) < self.tamanho:
            return False, None
        yuv = np.frombuffer(dados, np.uint8).reshape(self.altura * 3 // 2, self.largura)
        return True, cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

    def release(self):
        self.processo.terminate()
        self.processo.wait()


def baixar_modelo():
    if not os.path.exists(MODELO):
        print("Baixando o modelo do MediaPipe (so na primeira vez)...")
        urllib.request.urlretrieve(URL_MODELO, MODELO)


def distancia(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def calcular_ear(pontos):
    p1, p2, p3, p4, p5, p6 = pontos
    altura = distancia(p2, p6) + distancia(p3, p5)
    largura = distancia(p1, p4)
    return altura / (2.0 * largura)


def tem_tela():
    """No Linux so da para abrir a janela numa sessao grafica (nao por SSH)."""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def main():
    baixar_modelo()

    opcoes = vision.FaceLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=MODELO),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )

    # Sem argumento usa a webcam 0. Com argumento pode ser outro numero de
    # camera, o endereco do video do celular (app IP Webcam, DroidCam...)
    # ou "csi" para a camera ligada no conector de camera do Raspberry Pi.
    fonte = sys.argv[1] if len(sys.argv) > 1 else "0"
    usar_csi = False  # True quando a camera e a Picamera2

    if fonte.lower() == "csi":
        try:
            # So importa aqui para o projeto continuar rodando sem a Picamera2
            from picamera2 import Picamera2
        except ImportError:
            print("Picamera2 nao encontrada; usando o rpicam-vid para a camera CSI.")
            camera = CameraRpicam(LARGURA_CAPTURA, ALTURA_CAPTURA)
        else:
            usar_csi = True
            camera = Picamera2()
            # RGB888 entrega os bytes na ordem BGR, a mesma que o OpenCV usa
            config = camera.create_preview_configuration(
                main={"size": (LARGURA_CAPTURA, ALTURA_CAPTURA), "format": "RGB888"}
            )
            camera.configure(config)
            camera.start()
    else:
        if fonte.isdigit():
            fonte = int(fonte)
        camera = cv2.VideoCapture(fonte)
        if not camera.isOpened():
            print(f"Nao foi possivel abrir a camera: {fonte}")
            return
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, LARGURA_CAPTURA)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTURA_CAPTURA)

    mostrar = tem_tela()
    if not mostrar:
        print("Sem tela: rodando sem a janela. Use Ctrl+C para sair.")

    led = criar_led()
    estado_anterior = None

    try:
        with vision.FaceLandmarker.create_from_options(opcoes) as detector:
            inicio = time.monotonic()
            ultimo_ts = -1

            while True:
                if usar_csi:
                    frame = camera.capture_array()
                else:
                    ok, frame = camera.read()
                    if not ok:
                        print("A camera parou de enviar imagens.")
                        break

                frame = cv2.flip(frame, 1)  # espelha a imagem, como um espelho
                altura, largura = frame.shape[:2]

                # Detecta numa copia menor (mais rapido). Os pontos voltam
                # normalizados (0 a 1), entao servem para a imagem original.
                pequeno = frame
                if largura > LARGURA_DETECCAO:
                    escala = LARGURA_DETECCAO / largura
                    pequeno = cv2.resize(frame, (LARGURA_DETECCAO, int(altura * escala)),
                                         interpolation=cv2.INTER_AREA)

                # O MediaPipe espera RGB e um timestamp (ms) sempre crescente
                rgb = cv2.cvtColor(pequeno, cv2.COLOR_BGR2RGB)
                imagem = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts = max(int((time.monotonic() - inicio) * 1000), ultimo_ts + 1)
                ultimo_ts = ts
                resultado = detector.detect_for_video(imagem, ts)

                if resultado.face_landmarks:
                    rosto = resultado.face_landmarks[0]
                    ears = []

                    for indices in (OLHO_1, OLHO_2):
                        # Os pontos vem normalizados (0 a 1); converte para pixels
                        pontos = [(rosto[i].x * largura, rosto[i].y * altura) for i in indices]
                        ears.append(calcular_ear(pontos))
                        for x, y in pontos:
                            cv2.circle(frame, (int(x), int(y)), 2, (0, 255, 255), -1)

                    ear = sum(ears) / len(ears)
                    if ear < LIMIAR_EAR:
                        estado, cor = "OLHOS FECHADOS", (0, 0, 255)
                    else:
                        estado, cor = "OLHOS ABERTOS", (0, 200, 0)

                    cv2.putText(frame, estado, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cor, 3)
                    cv2.putText(frame, f"EAR: {ear:.2f}", (20, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                else:
                    estado = "Nenhum rosto detectado"
                    cv2.putText(frame, estado, (20, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)

                # O LED so acende com os olhos abertos. So mexe nele (e escreve
                # no terminal) quando o estado muda, nao a cada quadro.
                if estado != estado_anterior:
                    estado_anterior = estado
                    aceso = estado == "OLHOS ABERTOS"
                    print(f"{estado} -> LED {'aceso' if aceso else 'apagado'}")
                    if led is not None:
                        if aceso:
                            led.on()
                        else:
                            led.off()

                if mostrar:
                    cv2.imshow("Olhos abertos ou fechados", frame)
                    tecla = cv2.waitKey(1) & 0xFF
                    if tecla in (ord("q"), 27):  # 'q' ou ESC
                        break
    except KeyboardInterrupt:
        pass
    finally:
        # Apaga o LED e libera o pino e a camera, mesmo saindo com Ctrl+C ou erro
        if led is not None:
            led.off()
            led.close()
        if usar_csi:
            camera.stop()
            camera.close()
        else:
            camera.release()
        if mostrar:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
