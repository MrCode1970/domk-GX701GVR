#!/usr/bin/env python3
"""
Простой прокси Anthropic -> OpenAI-совместимый API
Для использования с OpenClaw без OpenRouter
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import anthropic
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
PORT = int(os.getenv("PROXY_PORT", 8000))
HOST = os.getenv("PROXY_HOST", "127.0.0.1")

if not ANTHROPIC_API_KEY:
    print("❌ Ошибка: Не установлен ANTHROPIC_API_KEY")
    print("Установи его в .env файле или экспортируй переменную")
    exit(1)

# Инициализируем клиент Anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Обрабатываем POST запросы (как к OpenAI чату)"""
        if self.path != "/v1/chat/completions":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error(400, "Empty body")
            return

        try:
            # Читаем тело запроса
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))

            # Извлекаем параметры (формат OpenAI)
            model = data.get('model', 'claude-3-haiku-20240307')
            messages = data.get('messages', [])
            temperature = data.get('temperature', 0.7)
            max_tokens = data.get('max_tokens', 1024)
            stream = data.get('stream', False)

            # Преобразуем в формат Anthropic
            # Убираем системные сообщения если есть (Anthropic обрабатывает их иначе)
            system_msg = ""
            user_messages = []
            for msg in messages:
                if msg.get('role') == 'system':
                    system_msg = msg.get('content', '')
                else:
                    user_messages.append(msg)

            # Формируем запрос к Anthropic
            anthropic_messages = []
            for msg in user_messages:
                role = msg.get('role')
                if role == 'assistant':
                    anthropic_role = 'assistant'
                elif role == 'user':
                    anthropic_role = 'user'
                else:
                    continue  # пропускаем неизвестные роли
                anthropic_messages.append({
                    "role": anthropic_role,
                    "content": msg.get('content', '')
                })

            # Делаем запрос к Anthropic
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_msg if system_msg else None,
                messages=anthropic_messages,
                stream=stream
            )

            if stream:
                # Для потокового режима (упрощённый)
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                
                for chunk in response:
                    if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                        delta = chunk.delta
                        if hasattr(delta, 'text'):
                            # Форматируем как SSE (Server-Sent Events)
                            chunk_data = {
                                "choices": [{
                                    "delta": {"content": delta.text},
                                    "index": 0,
                                    "finish_reason": None
                                }]
                            }
                            self.wfile.write(f"data: {json.dumps(chunk_data)}\n\n".encode('utf-8'))
                self.wfile.write(b"data: [DONE]\n\n")
            else:
                # Обычный ответ
                response_dict = {
                    "id": f"chatcmpl-{response.id}",
                    "object": "chat.completion",
                    "created": response.created_at,
                    "model": response.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response.content[0].text if response.content else ""
                        },
                        "finish_reason": response.stop_reason
                    }],
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_dict).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
        finally:
            self.wfile.flush()

    def log_message(self, format, *args):
        # Отключаем логи по умолчанию (можно включить для отладки)
        pass

def run_server():
    server = HTTPServer((HOST, PORT), ProxyHandler)
    print(f"🚀 Anthropic Proxy запущен на http://{HOST}:{PORT}")
    print(f"🔑 Используется ключ: {ANTHROPIC_API_KEY[:10]}...")
    print(f"🤖 Модель по умолчанию: claude-3-haiku-20240307")
    print(f"📝 Для OpenClaw используй: http://{HOST}:{PORT}/v1")
    print("Нажми Ctrl+C для остановки")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Остановка прокси...")
        server.server_close()

if __name__ == "__main__":
    run_server()