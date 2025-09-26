import base64
import queue
import threading
import time
from typing import Dict, Optional

import requests
from requests.exceptions import ConnectionError

from config import WPP_HOST_PORT, WPP_SECRET_KEY

API_URL = WPP_HOST_PORT+"/api"
SESSION_NAME = "weddingsession"
WPP_MESSAGE_INTERVAL_SECONDS = 5
HEADERS = {
    "Content-Type": "application/json"
}

class WppApi:
    def __init__(self, token=None):
        self.token = token
        self.queue = queue.Queue()
        self.lock_queue = False

        if not self.token:
            self.token = self._generate_token()
        
        if not self._check_session():
            print("Sessão não está ativa, iniciando uma nova sessão...")
            self._start_session()

        self.last_sent_message_timestamp = time.monotonic() - WPP_MESSAGE_INTERVAL_SECONDS
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self.queue_consumer, daemon=True)
        self.worker_thread.start()

    def _get_headers(self, auth: bool = True):
        headers = HEADERS.copy()

        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif auth:
            print("Token não fornecido, não será possível autenticar.")

        return headers

    def _generate_token(self):
        response = requests.post(
            f"{API_URL}/{SESSION_NAME}/{WPP_SECRET_KEY}/generate-token", 
            json={"session": SESSION_NAME},
            headers=self._get_headers(auth=False)
        )

        if response.status_code == 201:
            print("Token gerado com sucesso!")
            data = response.json()
            return data.get("token")

        print("Erro ao gerar o token:", response.status_code, response.text)        
        return None

    def _start_session(self):
        response = requests.post(
            f"{API_URL}/{SESSION_NAME}/start-session", 
            headers=self._get_headers()
        )

        session_check_status = requests.get(
            f"{API_URL}/{SESSION_NAME}/check-connection-session", 
            headers=self._get_headers()
        )

        while session_check_status.json()['message'] != "Connected":
            print("Aguardando conexão com o WhatsApp...")
            time.sleep(2)
            session_check_status = requests.get(
                f"{API_URL}/{SESSION_NAME}/check-connection-session", 
                headers=self._get_headers()
            )
        
        print("Sessão iniciada com sucesso!")

    def _check_session(self):
        response = requests.get(
            f"{API_URL}/{SESSION_NAME}/check-connection-session", 
            headers=self._get_headers())

        if response.status_code == 200 and response.json().get("message") == "Connected":
            return True
        else:
            return False

        if self.last_sent_message_timestamp is None:
            return False

        now = time.time()        
        if now - self.last_sent_message_timestamp < WPP_MESSAGE_INTERVAL_SECONDS:
            print("A mensagem deve ser inserida na fila para evitar bloqueio.")
            return True
        
        return False

    def _queue_message(self, phone_number: str, message: str):
        if self.lock_queue:
            print("Fila bloqueada, não é possível adicionar mensagens.")
            return

        self.queue.put((phone_number, message))
        print(f"Mensagem para {phone_number} adicionada à fila. Total na fila: {self.queue.qsize()}")
    
    def _queue_image(self, image_base64: str, phone_number: str, caption: str = ''):
        if self.lock_queue:
            print("Fila bloqueada, não é possível adicionar mensagens.")
            return

        self.queue.put((image_base64, phone_number, caption))
        print(f"Imagem para {phone_number} adicionada à fila. Total na fila: {self.queue.qsize()}")

    def send_message(self, phone_number: str, message: str):
        self._queue_message(phone_number, message)

    def send_image(self, phone_number: str, image_path: str, caption: str =''):
        converted_image = None
        with open(image_path, 'rb') as image:
            converted_image = base64.b64encode(image.read()).decode('utf-8')

        self._queue_image(converted_image, phone_number, caption)

    def _send_queued_message(self, phone_number: str, message: str) -> bool:
        payload = {
            "phone": phone_number,
            "message": message
        }

        response = requests.post(
            f"{API_URL}/{SESSION_NAME}/send-message", 
            json=payload, 
            headers=self._get_headers()
        )

        if response.status_code == 201:
            print("Mensagem enviada com sucesso!")
            self.last_sent_message_timestamp = time.monotonic()
            return True

        print(response.status_code)
        print(response.content)
        return False

    def _send_queued_image(self, image_base64: str, phone_number: str, caption: str) -> bool:
        payload = {
            "phone": phone_number,
            "caption": caption,
            "base64": f"data:image/png;base64,{image_base64}"
        }

        print(f"Enviando imagem para {phone_number} com legenda: {caption}. Imagem: {image_base64[:30]}...")

        response = requests.post(
            f"{API_URL}/{SESSION_NAME}/send-image", 
            json=payload, 
            headers=self._get_headers()
        )

        if response.status_code == 201:
            print("Imagem enviada com sucesso!")
            self.last_sent_message_timestamp = time.monotonic()
            return True
        
        print("Erro ao enviar imagem:", response.status_code, response.content)
        return False

    def queue_consumer(self):
        while not self._stop_event.is_set():
            try:
                image_base64 = None
                data = self.queue.get(timeout=1)
                if len(data) == 2:
                    phone_number, message = data
                else:
                    image_base64, phone_number, message = data
            except queue.Empty:
                continue

            with self._lock:
                elapsed = time.monotonic() - self.last_sent_message_timestamp
                if elapsed < WPP_MESSAGE_INTERVAL_SECONDS:
                    wait_time = WPP_MESSAGE_INTERVAL_SECONDS - elapsed
                    print(f"Aguardando {wait_time:.2f} segundos para enviar a próxima mensagem...")
                    time.sleep(wait_time)

                if image_base64:
                    self._send_queued_image(image_base64, phone_number, message)
                else:
                    self._send_queued_message(phone_number, message)

                self.last_sent_message_timestamp = time.monotonic()
                if self.lock_queue and self.queue.empty():
                    print("Fila bloqueada, não processando mais mensagens.")
                    self._stop_event.set()

    def wait_for_completion(self):
        self.lock_queue = True
        self.worker_thread.join()

    def is_contact(self, phone: str) -> bool:
        response = requests.get(
            f"{API_URL}/{SESSION_NAME}/profile/{phone}", 
            headers=self._get_headers()
        )

        data = response.json()
        if response.status_code == 200 and data['response']:
            return True
        
        return False

with open("token.txt", 'r') as f:
    token = f.read().strip()

try:
    wppapi = WppApi(token)
except ConnectionError as e:
    print("Não foi possível conectar à API do WhatsApp. Verifique se o servidor está ativo.")
    exit(1)


if __name__ == "__main__":
    wppapi.wait_for_completion()
