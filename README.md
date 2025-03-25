# AI Voice Interaction Application Guide

## Overview
This is an advanced AI voice interaction application built using Streamlit, Google's Gemini API, and PyAudio. It provides a flexible, real-time conversational interface with multiple features designed to mimic natural human conversation.

## Key Features

### 1. Multilingual Interaction
- Supports multiple interaction modes through simple prompting
- Can change language and conversation style dynamically by modifying the system instruction
- Supports both text and audio input/output

### 2. Adaptive Configuration
- Dynamic voice selection
- Configurable system instructions
- Switchable response modes (AUDIO/TEXT)

### 3. Robust Error Handling
- Automatic client reinitialization
- Multiple API key rotation
- Graceful error recovery
- Continuous conversation support

### 4. Real-time Communication
- Listens to user speech in real-time
- Supports text and audio input
- Provides immediate audio or text responses
- Handles interruptions smoothly

## Technical Architecture

### Components
1. **GeminiLive.py (Backend)**
   - Manages audio streaming
   - Handles Gemini API interactions
   - Implements error handling and client management
   - Supports asynchronous operations

2. **ui.py (Frontend)**
   - Streamlit-based user interface
   - Manages session controls
   - Provides configuration options

### Audio Processing
- Uses PyAudio for audio input/output
- Supports 16kHz input and 24kHz output sampling rates
- Handles audio chunks in real-time

## Prerequisites
- Python 3.8+
- Required libraries:
  - streamlit
  - google-generativeai
  - pyaudio
  - python-dotenv
  - asyncio

## Performance Evaluation

### Multilingual Capability
**Quality Assessment**: Excellent
- Supports multiple languages with high fidelity
- Natural language switching through system instruction modification
- Maintains conversational coherence across language changes
- Leverages Gemini's advanced language understanding

**Language Performance Highlights**:
- Smooth transitions between languages
- Preserves conversational context
- Adapts to linguistic nuances
- Suitable for professional and casual interactions

### Conversation Continuity
**Prolonged Conversation Analysis**:
- Sustained conversation capability: ✓ Confirmed
- Context retention: High
- Session stability: Robust
- Conversation flow: Natural and human-like

## Setup Instructions

### 1. Environment Configuration
Create a `.env` file with your Gemini API keys:
```
GEMINI_API_KEYS="key1,key2,key3"
```

### 2. Installation
```bash
pip install streamlit google-genai pyaudio python-dotenv
```

## Usage Guide

### Launching the Application
```bash
streamlit run ui.py
```

### Configuration Options

#### Voice Selection
Choose from available voices:
- Aoede
- Charon
- Fenrir
- Kore
- Puck

#### Response Modes
- AUDIO: Generates spoken responses
- TEXT: Provides text-based responses

#### System Instruction
Customize AI's personality and behavior by modifying the system instruction.

### Multilingual Interaction
To change language or conversation style, modify the system instruction:
- For Spanish: `Responde en español como un asistente amigable.`
- For French: `Réponds en français avec un ton chaleureux.`

### Conversation Tips
- Use headphones for best audio experience
- Press Enter to send text messages
- Start/Stop session as needed
- Experiment with different voices and system instructions

## Advanced Features

### Continuous Conversation
- Automatically reinitializes client on timeouts
- Supports prolonged interactions
- Gracefully handles connection issues

### Interruption Handling
- Can stop mid-response
- Supports context switching
- Maintains conversation state

## Troubleshooting
- Ensure stable internet connection
- Check API key configuration
- Verify audio device permissions
- Update dependencies regularly

## Security and Privacy
- Uses multiple API keys for reliability
- Supports configurable system instructions
- No persistent data storage

## Limitations
- Requires active internet connection
- Audio quality depends on input device
- Language support based on Gemini API capabilities