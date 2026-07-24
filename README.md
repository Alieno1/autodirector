# 🎬 Auto-Director: Agentic Workflow for AI Micro-Drama Generation

**Auto-Director** is a production-grade, multi-agent AI pipeline designed to convert raw text stories (in English or Hindi) into fully animated, voice-narrated, subtitle-aligned 9:16 vertical micro-dramas (YouTube Shorts, Instagram Reels, TikTok).

---

## 🌟 Key Features

- 🤖 **5-Agent Autonomous Pipeline:** Modular, provider-agnostic agents handling scriptwriting, voice narration, visual generation, subtitle alignment, and final video assembly.
- 🌐 **Multilingual Support:** Dynamic font resolution supporting Latin (English) and Devanagari (Hindi) scripts without character box ("tofu") artifacts.
- ⚡ **Multi-Tier Fallback Resilience:**
  - **Voice:** ElevenLabs → gTTS → `espeak-ng`
  - **Visuals:** Gemini Flash 3.1 → Pollinations Turbo → Stock Photos → PIL Gradient Cards
- 🎥 **Kinetic Motion & Captions:** Ken Burns pan/zoom effects, custom subtitle word wrapping, and rounded contrast pill overlays.
- ⚙️ **Optimized FFmpeg Muxing:** Strips unneeded alpha masks (`final.mask = None`) to guarantee 100% reliable, fast H.264 MP4 container encoding.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────┐
                       │     Raw Story Input     │
                       └────────────┬────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ [1] ScriptwriterAgent (Gemini 2.5 Flash / Offline Rule Splitter)       │
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
│ [3] VisualAgent (Gemini 3.1 ➔ Pollinations Turbo ➔ Stock Photos ➔ PIL) │
│     • Generates 9:16 vertical scene imagery with intelligent caching    │
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
│ [5] DirectorAgent (MoviePy + Native PIL Engine + FFmpeg H.264)         │
│     • Renders Ken Burns pan/zoom, burned-in subtitles, audio-video sync│
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

---

## 💻 Running the Pipeline

### Demo Mode (Offline & Zero API Cost)
Runs immediately using offline TTS (`espeak-ng`/`gTTS`) and PIL image cards:

```bash
python3 main.py sample_input/my_story_english.txt -o demo_story.mp4
```

### Live Mode (Full AI Fidelity)
Set your API keys (or save them in a `.env` file) to enable real ElevenLabs voice narration and Gemini AI image generation:

```bash
export GEMINI_API_KEY="your_gemini_key"
export ELEVENLABS_API_KEY="your_elevenlabs_key"

python3 main.py sample_input/my_story_english.txt -o live_story.mp4
```

### CLI Command Options

```bash
python3 main.py [STORY_FILE] [OPTIONS]

Options:
  -o, --output TEXT     Filename for the final MP4 (saved to output/ directory).
  -v, --verbose         Enable DEBUG-level logging.
  --help                Show usage information.
```

---

## 📂 Project Structure

```
autodirector/
├── main.py                   # Orchestration CLI & Progress Tracker
├── config.py                 # Pipeline configuration & API key management
├── models.py                 # Pydantic data models (Scene, Caption, etc.)
├── agents/
│   ├── scriptwriter_agent.py # Story parsing & scene breakdown
│   ├── voice_agent.py        # Voice synthesis (ElevenLabs / gTTS / espeak)
│   ├── visual_agent.py       # Image generation (Gemini / Pollinations / Stock)
│   ├── subtitle_agent.py     # Subtitle word timing alignment
│   └── director_agent.py     # MoviePy animation, PIL caption overlay & video assembly
├── core/
│   ├── logger.py             # Rich logger configuration
│   ├── retry.py              # Exponential backoff & HTTP status filter
│   └── exceptions.py         # Custom pipeline exceptions
├── assets/                   # TrueType fonts (DejaVuSans-Bold, NotoSansDevanagari)
├── sample_input/             # Sample story files (my_story_english.txt, my_story_hindi.txt)
├── output/                   # Rendered MP4 output directory
└── tests/                    # Comprehensive unit & integration tests
```

---

## 🧪 Testing & Verification

Run the automated unit test suite with `pytest`:

```bash
python3 -m pytest
```

---

## 🛡️ Architecture Design Decisions

1. **Audio-Driven Timing:** Video duration and subtitle timings are derived from actual synthesized waveform durations (`AudioFileClip.duration`), ensuring 100% audio-visual synchronization.
2. **Provider-Agnostic Resilience:** Every agent encapsulates provider logic. If a primary service fails (e.g. ElevenLabs rate limits), it seamlessly falls back down the chain without crashing the run.
3. **High-Performance Subtitle Engine:** Uses Pillow native `stroke_width` and `stroke_fill` attributes for crisp 49x faster text outline rendering.
