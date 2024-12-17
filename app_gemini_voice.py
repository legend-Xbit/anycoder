import gradio as gr
from gradio_webrtc import WebRTC, StreamHandler, get_twilio_turn_credentials
import websockets.sync.client
import numpy as np
import json
import base64
import os
from dotenv import load_dotenv

class GeminiConfig:
    def __init__(self):
        load_dotenv()
        self.api_key = self._get_api_key()
        self.host = 'generativelanguage.googleapis.com'
        self.model = 'models/gemini-2.0-flash-exp'
        self.ws_url = f'wss://{self.host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}'

    def _get_api_key(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
        return api_key

class AudioProcessor:
    @staticmethod
    def encode_audio(data, sample_rate):
        encoded = base64.b64encode(data.tobytes()).decode('UTF-8')
        return {
            'realtimeInput': {
                'mediaChunks': [{
                    'mimeType': f'audio/pcm;rate={sample_rate}',
                    'data': encoded,
                }],
            },
        }

    @staticmethod
    def process_audio_response(data):
        audio_data = base64.b64decode(data)
        return np.frombuffer(audio_data, dtype=np.int16)

class GeminiHandler(StreamHandler):
    def __init__(self,
                 expected_layout="mono",
                 output_sample_rate=24000,
                 output_frame_size=480) -> None:
        super().__init__(expected_layout, output_sample_rate, output_frame_size,
                        input_sample_rate=24000)
        self.config = GeminiConfig()
        self.ws = None
        self.all_output_data = None
        self.audio_processor = AudioProcessor()

    def copy(self):
        return GeminiHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size
        )

    def _initialize_websocket(self):
        try:
            self.ws = websockets.sync.client.connect(
                self.config.ws_url,
                timeout=30
            )
            initial_request = {
                'setup': {
                    'model': self.config.model,
                }
            }
            self.ws.send(json.dumps(initial_request))
            setup_response = json.loads(self.ws.recv())
            print(f"Setup response: {setup_response}")
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket connection failed: {str(e)}")
            self.ws = None
        except Exception as e:
            print(f"Setup failed: {str(e)}")
            self.ws = None

    def receive(self, frame: tuple[int, np.ndarray]) -> None:
        try:
            if not self.ws:
                self._initialize_websocket()

            _, array = frame
            array = array.squeeze()
            audio_message = self.audio_processor.encode_audio(array, self.output_sample_rate)
            self.ws.send(json.dumps(audio_message))
        except Exception as e:
            print(f"Error in receive: {str(e)}")
            if self.ws:
                self.ws.close()
            self.ws = None

    def _process_server_content(self, content):
        for part in content.get('parts', []):
            data = part.get('inlineData', {}).get('data', '')
            if data:
                audio_array = self.audio_processor.process_audio_response(data)
                if self.all_output_data is None:
                    self.all_output_data = audio_array
                else:
                    self.all_output_data = np.concatenate((self.all_output_data, audio_array))
                
                while self.all_output_data.shape[-1] >= self.output_frame_size:
                    yield (self.output_sample_rate, 
                          self.all_output_data[:self.output_frame_size].reshape(1, -1))
                    self.all_output_data = self.all_output_data[self.output_frame_size:]

    def generator(self):
        while True:
            if not self.ws:
                print("WebSocket not connected")
                yield None
                continue

            try:
                message = self.ws.recv(timeout=5)
                msg = json.loads(message)
                
                if 'serverContent' in msg:
                    content = msg['serverContent'].get('modelTurn', {})
                    yield from self._process_server_content(content)
            except TimeoutError:
                print("Timeout waiting for server response")
                yield None
            except Exception as e:
                print(f"Error in generator: {str(e)}")
                yield None

    def emit(self) -> tuple[int, np.ndarray] | None:
        if not self.ws:
            return None
        if not hasattr(self, '_generator'):
            self._generator = self.generator()
        try:
            return next(self._generator)
        except StopIteration:
            self.reset()
            return None

    def reset(self) -> None:
        if hasattr(self, '_generator'):
            delattr(self, '_generator')
        self.all_output_data = None

    def shutdown(self) -> None:
        if self.ws:
            self.ws.close()

    def check_connection(self):
        try:
            if not self.ws or self.ws.closed:
                self._initialize_websocket()
            return True
        except Exception as e:
            print(f"Connection check failed: {str(e)}")
            return False

class GeminiVoiceChat:
    def __init__(self):
        load_dotenv()
        self.demo = self._create_interface()

    def _create_interface(self):
        with gr.Blocks() as demo:
            gr.HTML("""
                <div style='text-align: center'>
                    <h1>Gemini 2.0 Voice Chat</h1>
                    <p>Speak with Gemini using real-time audio streaming</p>
                </div>
            """)
            
            webrtc = WebRTC(
                label="Conversation",
                modality="audio",
                mode="send-receive",
                rtc_configuration=get_twilio_turn_credentials()
            )
            
            webrtc.stream(
                GeminiHandler(),
                inputs=[webrtc],
                outputs=[webrtc],
                time_limit=90,
                concurrency_limit=10
            )
        return demo

    def launch(self):
        self.demo.launch(
            server_name="0.0.0.0",
            server_port=int(os.environ.get("PORT", 7860)),
            share=True,
            ssl_verify=False,
            ssl_keyfile=None,
            ssl_certfile=None
        )

# Create and expose the demo instance
def demo():
    chat = GeminiVoiceChat()
    return chat.demo

# This is what will be imported by app.py
demo = demo()