"""
Detecta pela webcam se os olhos estao abertos ou fechados.

Usa o Face Landmarker do MediaPipe para achar os pontos do rosto e calcula
o EAR (Eye Aspect Ratio), que e a razao entre a altura e a largura do olho:
    olho aberto  -> EAR alto  (em torno de 0.25 a 0.35)
    olho fechado -> EAR baixo (abaixo de 0.20)

Uso:
    python olho_aberto_fechado.py                               # webcam do PC
    python olho_aberto_fechado.py http://192.168.0.10:8080/video  # celular

Pressione 'q' ou ESC para sair.
"""
import os
import sys
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

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


def main():
    baixar_modelo()

    opcoes = vision.FaceLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=MODELO),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )

    # Sem argumento usa a webcam 0. Com argumento pode ser outro numero de
    # camera ou o endereco do video do celular (app IP Webcam, DroidCam...).
    fonte = sys.argv[1] if len(sys.argv) > 1 else "0"
    if fonte.isdigit():
        fonte = int(fonte)

    camera = cv2.VideoCapture(fonte)
    if not camera.isOpened():
        print(f"Nao foi possivel abrir a camera: {fonte}")
        return

    with vision.FaceLandmarker.create_from_options(opcoes) as detector:
        inicio = time.monotonic()
        ultimo_ts = -1

        while True:
            ok, frame = camera.read()
            if not ok:
                print("A camera parou de enviar imagens.")
                break

            frame = cv2.flip(frame, 1)  # espelha a imagem, como um espelho
            altura, largura = frame.shape[:2]

            # O MediaPipe espera RGB e um timestamp (ms) sempre crescente
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
                    texto, cor = "OLHOS FECHADOS", (0, 0, 255)
                else:
                    texto, cor = "OLHOS ABERTOS", (0, 200, 0)

                cv2.putText(frame, texto, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cor, 3)
                cv2.putText(frame, f"EAR: {ear:.2f}", (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            else:
                cv2.putText(frame, "Nenhum rosto detectado", (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)

            cv2.imshow("Olhos abertos ou fechados", frame)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):  # 'q' ou ESC
                break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
