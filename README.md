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

## 🔑 How to Setup Your API Keys

To use Auto-Director at its full potential, you must configure two specific API Keys. You do **not** need a GPU on your computer—these cloud platforms do 100% of the heavy lifting.

1. **OpenRouter (The Brain):** Provides the LLM logic to write your scenes and analyze your story. 
   * Get it here: [openrouter.ai](https://openrouter.ai/)
2. **Replicate (The Video Camera):** Provides access to massive cloud supercomputers running the *MiniMax* Video AI to generate your animated video clips. 
   * Get it here: [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
   * *(Note: Replicate is a paid service costing roughly $0.02 per clip. You MUST add a payment method to your Replicate account, or the app will hit a 'Free Limit' error and fall back to static images).*

### Adding the Keys to the Software:
Create a `.env` file in the root folder of this project and paste your keys:
```env
OPENROUTER_API_KEY="sk-or-v1-your-key-here..."
REPLICATE_API_TOKEN="r8_your_token_here..."
```
Because this file is in `.gitignore`, **your keys will never be uploaded to GitHub.** Alternatively, you can copy/paste your keys directly into the Streamlit Web UI sidebar!

---

## 💻 How to Use the UI (User Manual)

Forget using the terminal! To start the application, simply run:
```bash
./.venv/bin/streamlit run app.py
```
This will pop open a browser window at `http://localhost:8501`. 

### The Workflow:
1. **Enter your Story:** Paste your raw text into the main text box. It can be misspelled, sloppy, in Hindi, or Hinglish—the OpenRouter AI will magically parse and translate it seamlessly!
2. **Press "Generate Video"**: 
   * **If your story is short and perfect (< 130 words):** The pipeline will instantly fire up, skipping all questions, and begin rendering your movie immediately!
   * **If your story is too long (> 130 words):** The UI will intelligently pause. It will display a *"Your story is quite long!"* warning, and OpenRouter will automatically generate two alternate, compressed storylines designed specifically to fit underneath 90 seconds. You can choose one of the recommended storylines, or force the AI to try and squeeze your original long story in anyway, then hit **"Confirm Choice"**.
3. **The Progress Log:** Sit back and scroll down to the bottom log interface. You will see real-time color-coded terminal logs as the 5 agents generate audio, process the Replicate cloud videos, align the subtitles, and stitch the MP4 container securely.
4. **Download your Movie!** Once Agent 5 completes at 100%, the completed movie will pop up explicitly in the browser player for you to watch, share, and download directly. 

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
