import speech_recognition as sr
import requests
import json
import pyttsx3
import pygame
import os
import re
import tempfile
from glob import glob

# ==== Função para ajustar proporção da imagem ====
def ajustar_proporcao(rect, largura_disp, altura_disp):
    proporcao = min(largura_disp / rect.width, altura_disp / rect.height)
    nova_largura = int(rect.width * proporcao)
    nova_altura = int(rect.height * proporcao)
    return (nova_largura, nova_altura)

# ==== Configurações da API ====
API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==== Inicialização do Pygame ====
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
largura_tela, altura_tela = screen.get_size()

# ==== Inicializa pyttsx3 com voz masculina ====
engine = pyttsx3.init()
for voice in engine.getProperty('voices'):
    if 'brazil' in voice.name.lower() and 'male' in voice.name.lower():
        engine.setProperty('voice', voice.id)
        break
engine.setProperty('rate', 200)

# ==== Carrega os frames do avatar ouvindo (animação) ====
frame_paths_ouvindo = sorted(glob("frames_ouvindo/*.png"))
frames_ouvindo = []
for fp in frame_paths_ouvindo:
    img = pygame.image.load(fp)
    rect_img = img.get_rect()
    img_redimensionada = pygame.transform.scale(img, ajustar_proporcao(rect_img, largura_tela, altura_tela))
    frames_ouvindo.append(img_redimensionada)

# ==== Carrega os frames da boca falando ====
frame_paths = sorted(glob("frames_falando/*.png"))
frames = []
for fp in frame_paths:
    img = pygame.image.load(fp)
    rect_img = img.get_rect()
    img_redimensionada = pygame.transform.scale(img, ajustar_proporcao(rect_img, largura_tela, altura_tela))
    frames.append(img_redimensionada)

# ==== Histórico da conversa ====
historico_mensagens = [
    {
        "role": "system",
        "content": "seu nome é 'turma 1DC1' e você é um assistente de uma única pessoa e você responde tudo sobre metaverso de forma resumida em português do Brasil com linguagem simpática e acolhedora. Quem estiver falando com você poder ser homem ou mulher, então não fale como se fosse unicamente um dos dois."
    }
]

def limpar_texto(texto):
    return re.sub(r'[^\w\s,.!?áéíóúãõâêôçÁÉÍÓÚÃÕÂÊÔÇ]', '', texto)

def falar_com_pyttsx3(texto):
    global interromper_fala
    interromper_fala = False

    texto_limpo = limpar_texto(texto)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
        nome_arquivo = f.name

    engine.save_to_file(texto_limpo, nome_arquivo)
    engine.runAndWait()

    pygame.mixer.init()
    som = pygame.mixer.Sound(nome_arquivo)
    canal = som.play()

    clock = pygame.time.Clock()
    frame_index = 0
    num_frames = len(frames)

    while canal.get_busy():
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Clique esquerdo
                interromper_fala = True
                canal.stop()

        if interromper_fala:
            break

        screen.fill((0, 0, 0))
        frame = frames[frame_index]
        frame_rect = frame.get_rect(center=(largura_tela // 2, altura_tela // 2))
        screen.blit(frame, frame_rect.topleft)
        pygame.display.flip()

        frame_index = (frame_index + 1) % num_frames
        clock.tick(30)

    pygame.mixer.quit()
    os.remove(nome_arquivo)

def ouvir_microfone():
    clock = pygame.time.Clock()
    frame_index = 0
    num_frames = len(frames_ouvindo)

    r = sr.Recognizer()
    audio = None

    def callback(recognizer, audio_data):
        nonlocal audio
        if audio is None:
            audio = audio_data

    stop_listening = sr.Recognizer().listen_in_background(sr.Microphone(), callback, phrase_time_limit=4)

    while audio is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                exit()

        screen.fill((0, 0, 0))
        frame = frames_ouvindo[frame_index]
        frame_rect = frame.get_rect(center=(largura_tela // 2, altura_tela // 2))
        screen.blit(frame, frame_rect.topleft)
        pygame.display.flip()

        frame_index = (frame_index + 1) % num_frames
        clock.tick(30)

    stop_listening(wait_for_stop=False)

    try:
        texto = r.recognize_google(audio, language='pt-BR')
        print("🗣️ Você disse:", texto)
        return texto
    except sr.UnknownValueError:
        print("❌ Não entendi o que você falou.")
        return None
    except sr.RequestError:
        print("❌ Erro ao se conectar com o serviço de voz.")
        return None

def responder_com_groq(pergunta):
    global historico_mensagens

    historico_mensagens.append({"role": "user", "content": pergunta})

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": historico_mensagens,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        resposta = response.json()['choices'][0]['message']['content'].strip()

        historico_mensagens.append({"role": "assistant", "content": resposta})

        # Limitar histórico para não pesar
        if len(historico_mensagens) > 20:
            historico_mensagens = historico_mensagens[-20:]

        print("🤖 IA:", resposta)
        falar_com_pyttsx3(resposta)
    except requests.exceptions.HTTPError as http_err:
        print("❌ Erro HTTP:", http_err)
        print("Resposta da API:", response.text)
    except Exception as e:
        print("❌ Erro geral:", e)

# ==== Loop principal ====
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            exit()

    pergunta = ouvir_microfone()
    if pergunta:
        if pergunta.lower() == 'parar':
            despedida = "Tudo bem, tchau! Se precisar de mim de novo, é só chamar."
            print("🤖 IA:", despedida)
            falar_com_pyttsx3(despedida)
            break
        responder_com_groq(pergunta)
