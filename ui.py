import streamlit as st
import asyncio
import threading
from GeminiLive import AudioLoop
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncRunner:
    def __init__(self):
        self.loop = None
        self.thread = None
        self.running = False
        self.audio_loop = None

    def start(self, voice, system_instruction, response_mode):
        # Stop any existing session
        self.stop()
        
        try:
            # Create a new event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Create AudioLoop with specific configuration
            self.audio_loop = AudioLoop()
            
            # Set configuration directly in the AudioLoop
            self.audio_loop.voice = voice
            self.audio_loop.system_instruction = system_instruction
            self.audio_loop.response_mode = response_mode
            
            # Start the thread
            self.thread = threading.Thread(
                target=self.run_async, 
                daemon=True
            )
            self.thread.start()
            
            self.running = True
            logger.info("Session started successfully")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            self.stop()

    def run_async(self):
        try:
            self.loop.run_until_complete(self.audio_loop.run())
        except Exception as e:
            logger.error(f"Error in async run: {e}")
        finally:
            self.running = False

    def stop(self):
        try:
            # Cancel all tasks
            if self.loop and not self.loop.is_closed():
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
                
                # Stop the loop
                self.loop.call_soon_threadsafe(self.loop.stop)
                
            # Wait for thread to terminate
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2)
            
            # Reset state
            self.running = False
            self.audio_loop = None
            self.loop = None
            
            logger.info("Session stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping session: {e}")


# Streamlit UI
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.title("🎙️ AI Voice Interaction")

# Initialize session state
if 'runner' not in st.session_state:
    st.session_state.runner = AsyncRunner()
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Session Status Indicator
st.markdown('<div class="session-status">', unsafe_allow_html=True)
if hasattr(st.session_state.runner, 'running'):
    status_text = "Session Active" if st.session_state.runner.running else "Session Inactive"
    st.markdown(f'<div>{status_text}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Voice and configuration options
col1, col2 = st.columns(2)
with col1:
    selected_voice = st.selectbox("🗣️ Voice:", 
        ["Aoede", "Charon", "Fenrir", "Kore", "Puck"],
        help="Choose the voice for the AI assistant"
    )
with col2:
    response_mode = st.selectbox("📡 Response Mode:", 
        ["AUDIO", "TEXT"],
        help="Select how the AI will respond"
    )

# System instruction input
system_instruction = st.text_area(
    "🤖 System Instruction:", 
    value="You are a helpful assistant and answer in a friendly tone.",
    help="Customize the AI's personality and behavior"
)

# Control buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Start Session"):
        # Stop any existing session first
        st.session_state.runner.stop()
        
        # Start a new session with current configuration
        st.session_state.runner.start(
            voice=selected_voice, 
            system_instruction=system_instruction, 
            response_mode=response_mode
        )
        st.success("Session started - use headphones!")

with col2:
    if st.button("🛑 Stop Session"):
        st.session_state.runner.stop()
        st.warning("Session stopped")

# Text input for sending messages
def send_message():
    user_input = st.session_state.user_input.strip()
    if user_input and st.session_state.runner.running:
        runner = st.session_state.runner
        if hasattr(runner, "audio_loop"):
            asyncio.run_coroutine_threadsafe(
                runner.audio_loop.send_external_text(user_input), 
                runner.loop
            )
            st.session_state.messages.append(user_input)

        st.session_state.user_input = ""  # Clear input

st.text_input(
    "💬 Type your message (press Enter to send):", 
    key="user_input", 
    on_change=send_message
)

# Display messages with enhanced styling
st.markdown('<div class="message-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    st.markdown(f'<div style="margin-bottom: 10px; padding: 10px; background-color: #f1f3f5; border-radius: 8px;">🗨️ {msg}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)