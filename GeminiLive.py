import asyncio
import os
import traceback
import pyaudio
from dotenv import load_dotenv
from google import genai
from google.genai import types
import logging
from collections import deque
import random

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_VOICE = "Puck"
DEFAULT_SYSTEM_INST = "You are a helpful assistant and answer in a friendly tone."
DEFAULT_RESPONSE_MODE = "AUDIO"

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MODEL = "models/gemini-2.0-flash-exp"
MAX_RETRIES = 3
RETRY_DELAY = 2

pya = pyaudio.PyAudio()

class KeyManager:
    def __init__(self):
        self._keys = self._load_api_keys()
        self._key_queue = deque()
        self._initialize_queue()

    def _load_api_keys(self):
        """Load and validate Gemini API keys"""
        load_dotenv()
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        if not keys_str:
            logger.error("GEMINI_API_KEYS environment variable not set")
            raise ValueError("API keys configuration error")

        keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        if not keys:
            logger.error("No valid Gemini API keys found")
            raise ValueError("No valid API keys")

        return keys

    def _initialize_queue(self):
        """Initialize the key queue with randomized order"""
        keys_copy = self._keys.copy()
        random.shuffle(keys_copy)
        self._key_queue = deque(keys_copy)

    def get_next_key(self):
        """Get the next API key in the rotation"""
        if not self._key_queue:
            self._initialize_queue()
        return self._key_queue.popleft()

class AudioLoop:
    def __init__(self):
        self.key_manager = KeyManager()
        self.reset_state()

    def reset_state(self):
        """Completely reset all state variables."""
        # Cancel any existing tasks
        if hasattr(self, '_config_task'):
            try:
                self._config_task.cancel()
            except Exception:
                pass

        # Close any existing audio streams
        if hasattr(self, 'audio_stream') and self.audio_stream:
            try:
                self.audio_stream.close()
            except Exception:
                pass

        # Initialize/reset all state variables
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=5)
        self.external_input_queue = asyncio.Queue()
        self.config_update_queue = asyncio.Queue()
        
        # Use default configuration
        self.voice = DEFAULT_VOICE
        self.system_instruction = DEFAULT_SYSTEM_INST
        self.response_mode = DEFAULT_RESPONSE_MODE
        
        self.session = None
        self.client = None
        self.audio_stream = None
        self.is_running = False
        self._config_task = None

    async def initialize_client(self):
        """Create a new client instance with error handling and retry logic."""
        retries = 0
        last_error = None
        
        while retries < MAX_RETRIES:
            try:
                api_key = self.key_manager.get_next_key()
                self.client = genai.Client(
                    api_key=api_key, 
                    http_options={"api_version": "v1alpha"}
                )
                logger.info("Gemini client initialized successfully")
                return
            except Exception as e:
                last_error = e
                retries += 1
                logger.warning(f"Failed to initialize Gemini client (attempt {retries}/{MAX_RETRIES}): {e}")
                if retries < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
        
        logger.error(f"Failed to initialize client after {MAX_RETRIES} attempts")
        raise last_error

    async def configure_session(self):
        """Dynamic configuration update handler."""
        try:
            while True:
                new_config = await self.config_update_queue.get()
                
                # Update configuration safely
                self.voice = new_config.get("voice", self.voice)
                self.system_instruction = new_config.get("system_instruction", self.system_instruction)
                self.response_mode = new_config.get("response_mode", self.response_mode)
                
                logger.info(f"Updated config: Voice={self.voice}, Mode={self.response_mode}")
                
        except asyncio.CancelledError:
            logger.info("Configuration update task cancelled")
        except Exception as e:
            logger.error(f"Configuration update error: {e}")

    async def send_text(self):
        """Sends text input from UI with added cancellation handling."""
        try:
            while True:
                text = await self.external_input_queue.get()
                if text.lower() == "q":
                    break
                await self.session.send(input=text or ".", end_of_turn=True)
        except asyncio.CancelledError:
            logger.info("Send text task cancelled")
        except Exception as e:
            logger.error(f"Error in send_text: {e}")

    async def send_external_text(self, text):
        """Allows UI to send messages."""
        await self.external_input_queue.put(text)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        """Background task to reads from the websocket and write pcm chunks to the output queue"""
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            # Ensure clean client initialization
            await self.initialize_client()
            
            # Start configuration update task
            self._config_task = asyncio.create_task(self.configure_session())
            
            while True:
                try:
                    config = {
                        "response_modalities": [self.response_mode],
                        "system_instruction": types.Content(
                            parts=[types.Part(text=self.system_instruction)]
                        ),
                    }
                    
                    if self.response_mode == "AUDIO":
                        config["speech_config"] = types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.voice
                                )
                            )
                        )

                    async with (
                        self.client.aio.live.connect(model=MODEL, config=config) as session,
                        asyncio.TaskGroup() as tg,
                    ):
                        self.session = session
                        self.is_running = True

                        # Create tasks
                        send_text_task = tg.create_task(self.send_text())
                        tg.create_task(self.send_realtime())
                        tg.create_task(self.listen_audio())
                        tg.create_task(self.receive_audio())
                        tg.create_task(self.play_audio())

                        await send_text_task
                
                except Exception as e:
                    logger.error(f"Session error: {e}")
                    logger.info("Attempting to reinitialize client...")
                    await self.initialize_client()  # Try with a new key
                    await asyncio.sleep(RETRY_DELAY)  # Brief delay before retry

        except asyncio.CancelledError:
            logger.info("Session cancelled gracefully")
        except Exception as e:
            logger.error(f"Unexpected error in run method: {e}")
            traceback.print_exc()
        finally:
            # Comprehensive cleanup
            if self._config_task:
                self._config_task.cancel()
            self.reset_state()

if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())