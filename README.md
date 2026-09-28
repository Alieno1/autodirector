# 🎬 Auto-Director: Agentic Workflow for AI Micro-Drama Generation

**Auto-Director** is a production-grade, multi-agent AI pipeline designed to convert raw text stories (in English or Hindi) into fully animated, voice-narrated, subtitle-aligned 9:16 vertical micro-dramas (YouTube Shorts, Instagram Reels, TikTok) dynamically through a beautiful Streamlit UI.

---

## 🌟 Key Features

- 🖥️ **Vibrant Streamlit UI:** A fully animated, dark cyberpunk-themed web interface for entering scripts, analyzing lengths, and watching generated video output directly in your browser.
- ⏱️ **Intelligent 90s Optimization:** Built-in OpenRouter processors analyze text length. If a story goes over the ~130-word limit (90 seconds), it automatically generates condensed alternative plots on the fly for the user to choose from.
- 🤖 **5-Agent Autonomous Pipeline:** Modular, provider-agnostic agents handling scriptwriting, voice narration, visual generation, subtitle alignment, and final video assembly.
- 🎥 **True AI Text-to-Video:** Replaced static images with cinematic 5-second video clips rendered fully through **Replicate (MiniMax video-01)**.
- ⚡ **Multi-Tier Fallback Resilience:**
  - **Voice:** ElevenLabs → gTTS → `espeak-ng`
  - **Visuals:** Replicate (MiniMax video) → Pollinations Turbo (AI Image) → Stock Photos → PIL Gradient Cards
- 🌐 **Multilingual Support:** Dynamic font resolution supporting Latin (English) and Devanagari (Hindi) scripts natively without character box ("tofu") artifacts. The LLM auto-translates cinematic prompts to English while preserving narration.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────┐
                       │     Streamlit Web UI    │
                       └────────────┬────────────┘
                                    │ (Story text < 130 words)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [1] ScriptwriterAgent (OpenRouter / meta-llama/llama-3.1-8b-instruct)   │
│     • Parses story into structured scenes (narration, visual prompt, mood)│
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [2] VoiceAgent (ElevenLabs ➔ gTTS ➔ espeak-ng)                          │
│     • Synthesizes parallel scene narration and computes exact audio duration│
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [3] VideoAgent (Replicate Minimax ➔ Pollinations Turbo ➔ Stock Photos)  │
│     • Generates stunning 9:16 vertical video clips or fallback static images│
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [4] SubtitleAgent (Word Bounding & Proportional Time Allocation)         │
│     • Calculates word-level start/end timestamps per narration phrase   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [5] DirectorAgent (MoviePy 2.x + Native PIL Engine + FFmpeg H.264)      │
│     • Assembles video loops, applies Ken Burns to still fail-backs,     │
│       burns in subtitles, and syncs massive audio-video files safely.   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ Output: 9:16 Vertical   │
                       │ Micro-Drama (.mp4)      │
                       └─────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. System Requirements

Install Linux system dependencies (`ffmpeg` for encoding and `espeak-ng` for offline TTS):

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg espeak-ng
```

### 2. Environment Setup

Clone the repository and set up a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. API Key Configuration

Copy the example environment file or manually create a `.env` in the root folder with the following:

```env
OPENROUTER_API_KEY="sk-or-your-key..."
REPLICATE_API_TOKEN="r8_your_token..."

# Optional:
ELEVENLABS_API_KEY="sk_your_key_here..."
```

---

## 💻 Running the Application

Forget the CLI—everything is gracefully handled via the **Streamlit Web UI**.

```bash
./.venv/bin/streamlit run app.py
```
This boots up a local web server at `localhost:8501`. 
1. The UI will securely auto-load your `.env` keys.
2. Enter a story in English, Hindi, or Hinglish.
3. Click "Generate Video", let the 5-Agent pipeline run, and view the final MP4 embedded directly the browser!

---

## 📂 Project Structure

```
autodirector/
├── app.py                    # The Main Streamlit UI 
├── config.py                 # Pipeline configuration & API key management
├── models.py                 # Pydantic data models (Scene, Caption, etc.)
├── agents/
│   ├── scriptwriter_agent.py # OpenRouter Story parsing & scene breakdown
│   ├── voice_agent.py        # Voice synthesis (ElevenLabs / gTTS / espeak)
│   ├── visual_agent.py       # Cinematic Video Generation (Replicate / Fallbacks)
│   ├── subtitle_agent.py     # Subtitle word timing alignment
│   └── director_agent.py     # MoviePy 2.x video assembly & styling
├── .streamlit/
│   └── config.toml           # Vibrant Animated cyberpunk Streamlit styling
├── core/
│   ├── logger.py             # UI + Terminal logging handlers
│   ├── retry.py              # Exponential backoff & HTTP status filter
│   └── exceptions.py         # Custom pipeline exceptions
├── assets/                   # TrueType fonts (DejaVuSans-Bold, NotoSansDevanagari)
├── output/                   # Final rendered MP4 output directory
└── temp/                     # Internal sandbox for holding AI clips
```

## 🛡️ Architecture Design Decisions

1. **MoviePy 2.x Refactor:** Handled the major API breaks in MoviePy 2.2 (`moviepy.video.fx.all` deprecated to `.with_effects([vfx.Loop()])`) for stable video integration.
2. **Dynamic UI Streaming:** Bypassed standard un-copyable UI text blocks and used `st.code()` with custom python-logging wrappers so users can comfortably monitor and copy pipeline errors as it runs.
3. **Provider-Agnostic Resilience:** If Replicate limits are exhausted, the app silently routes to fetch AI Images from Pollinations. The Director Agent naturally detects MP4 versus PNG to apply Pan-and-Zoom effects appropriately without crashing.
