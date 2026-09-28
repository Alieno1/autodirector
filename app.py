import streamlit as st
import os
import sys
import threading
from io import StringIO
import time
import requests
import json

# Ensure we can import from core components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from agents.scriptwriter_agent import ScriptwriterAgent
from agents.voice_agent import VoiceAgent
from agents.visual_agent import VisualAgent
from agents.subtitle_agent import SubtitleAgent
from agents.director_agent import DirectorAgent

st.set_page_config(page_title="Auto-Director AI", page_icon="🎬", layout="wide")

# --- Light Mode Toggle ---
light_mode = st.sidebar.toggle("☀️ Light Mode")

# Inject vibrant animated CSS
if light_mode:
    bg_style = """
    .stApp, [data-testid="stSidebar"] {
        background: linear-gradient(-45deg, #f0f4f8, #e8f0fe, #d2e3fc, #f0f4f8) !important;
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText, [data-testid="stMarkdownContainer"] p {
        color: #1a1a1a !important;
        text-shadow: none !important;
    }
    /* Light Mode Form Elements */
    /* Universal Form Recolor for Light Mode (Hyper-redundant) */
    .stTextInput > div > div, .stTextArea > div > div, .stSelectbox > div > div,
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"],
    input, textarea, .stSelectbox [role="combobox"], [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    ::placeholder {
        color: #555555 !important;
        opacity: 1 !important;
    }
    
    /* Force ALL Header and Sidebar SVGs to Pitch Black */
    header svg, [data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg, [data-testid="stToolbar"] svg {
        filter: none !important;
        fill: #000000 !important;
        stroke: #000000 !important;
        color: #000000 !important;
    }
    
    /* Ensure the container doesn't block visibility */
    [data-testid="collapsedControl"], header, [data-testid="stToolbar"] {
        color: #000000 !important;
        opacity: 1 !important;
    }
    
    /* Fix Toggle Switch */
    div[data-testid="stWidgetLabel"] + div[data-baseweb="checkbox"] > div,
    div[role="switch"] > div, .stCheckbox [role="switch"] > div, .stCheckbox div[data-baseweb="checkbox"] > div {
        background-color: #000000 !important;
    }
    
    /* Glowing Buttons Light Mode (Bright Cyan/Blue) */
    div.stButton > button {
        background: linear-gradient(90deg, #4fc3f7, #29b6f6) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(41, 182, 246, 0.4);
        transition: all 0.3s ease 0s;
    }
    div.stButton > button:hover {
        box-shadow: 0 4px 25px rgba(41, 182, 246, 0.7);
        transform: translateY(-2px);
    }
    """
else:
    bg_style = """
    .stApp, [data-testid="stSidebar"] {
        background: linear-gradient(-45deg, #120a1f, #1c1130, #2c0b38, #0e0524) !important;
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    h1, h2, h3 {
        text-shadow: 0 2px 10px rgba(255, 0, 127, 0.3);
    }
    /* Glowing Buttons Dark Mode (Neon Purple/Pink) */
    div.stButton > button {
        background: linear-gradient(90deg, #ff007f, #7f00ff) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 0, 127, 0.4);
        transition: all 0.3s ease 0s;
    }
    div.stButton > button:hover {
        box-shadow: 0 4px 25px rgba(255, 0, 127, 0.7);
        transform: translateY(-2px);
    }
    """

st.markdown(f"""
<style>
/* Animated Gradient Background for the main container */
{bg_style}
@keyframes gradientBG {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
</style>
""", unsafe_allow_html=True)

st.title("🎬 Auto-Director AI: Text to Micro-Drama")
st.markdown("Transform your stories into fully rendered 9:16 vertical videos using AI.")

# --- API Keys Sidebar ---
with st.sidebar:
    st.header("⚙️ API Configuration")
    
    openrouter_key = st.text_input("OpenRouter API Key (LLM)", value="", type="password", placeholder="Enter your own key to override...")
    replicate_key = st.text_input("Replicate API Key (Video/Audio)", value="", type="password", placeholder="Enter your own key to override...")
    elevenlabs_key = st.text_input("ElevenLabs API Key (TTS) Optional", value="", type="password", placeholder="Enter your own key to override...")
    
    st.markdown("---")
    st.info("Keys are updated dynamically.")

def get_story_alternatives(story_text: str):
    """Call OpenRouter to generate 2 alternatives under 130 words for stories that are too long."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://localhost:8501", 
        "X-Title": "Auto-Director", 
    }
    prompt = (
        "The user provided a story that is too long for a 90-second video. "
        "A 90-second video can ideally fit ~130 words of narration. "
        "Please provide EXACTLY two alternative shortened versions of their storyline "
        "that captures the main essence but keeps the word count strictly under 130. "
        "Return ONLY JSON in this format: { \"options\": [\"Option 1 text...\", \"Option 2 text...\"] }"
    )
    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": story_text}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 200:
        data = resp.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(data).get("options", [])
        except:
            pass
    return []

# --- Session State Management ---
if "story_analyzed" not in st.session_state:
    st.session_state.story_analyzed = False
if "story_options" not in st.session_state:
    st.session_state.story_options = []
if "processing_started" not in st.session_state:
    st.session_state.processing_started = False
if "final_story_to_process" not in st.session_state:
    st.session_state.final_story_to_process = ""


# --- Main App ---
st.markdown("### 🎛️ Render Settings")
quality = st.selectbox("Video Quality (Prevent Cloud RAM Crashes)", ["High (1080p - 30FPS)", "Medium (720p - 24FPS)", "Low (480p - 24FPS)"], index=1)
if quality.startswith("High"):
    settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT, settings.FPS = 1080, 1920, 30
elif quality.startswith("Medium"):
    settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT, settings.FPS = 720, 1280, 24
else:
    settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT, settings.FPS = 480, 854, 24

st.markdown("---")
story_input = st.text_area("📖 Enter your Story or Script", height=150, placeholder="Write a short dramatic story here...")

word_count = len(story_input.split())
st.caption(f"Estimated Word Count: {word_count} (Ideal: < 130 words for a 90s video)")

col1, col2 = st.columns([1, 1])

if st.button("🚀 Generate Video", use_container_width=True, type="primary"):
    if not story_input.strip():
        st.error("Please enter a story first.")
    # Check if openrouter key exists either in the text box or settings
    elif not settings.OPENROUTER_API_KEY and not openrouter_key:
        st.error("Please configure the OpenRouter API Key in the sidebar.")
    else:
        if openrouter_key: settings.OPENROUTER_API_KEY = openrouter_key
        
        if word_count > 130:
            with st.spinner("Analyzing story length..."):
                st.session_state.story_options = get_story_alternatives(story_input)
                st.session_state.story_analyzed = True
                st.warning("Your story is quite long and might exceed 90 seconds! We generated some optimized versions for you.")
        else:
            # Story is perfectly sized, begin immediately
            st.session_state.final_story_to_process = story_input
            st.session_state.story_analyzed = False
            st.session_state.processing_started = True
                        
if st.session_state.story_analyzed and len(st.session_state.story_options) > 0:
    st.markdown("### 💡 Recommended Optimized Storylines (Under 90s)")
    
    choice = st.radio(
        "Choose a storyline to generate your video:",
        options=["Use My Original Story (We will try to force it to fit cleanly)"] + st.session_state.story_options
    )
    
    if st.button("✅ Confirm Choice and Start Generation", use_container_width=True, type="primary"):
        if choice == "Use My Original Story (We will try to force it to fit cleanly)":
            st.session_state.final_story_to_process = story_input
        else:
            st.session_state.final_story_to_process = choice
        st.session_state.processing_started = True

class StreamlitLogger:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.logs = []
        
    def info(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except:
            formatted = msg
        self.logs.append(f"🟢 INFO: {formatted}")
        self.placeholder.code("\n".join(self.logs[-10:]), language="shell")
        
    def debug(self, msg, *args):
        pass 
        
    def warning(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except:
            formatted = msg
        self.logs.append(f"🟠 WARN: {formatted}")
        self.placeholder.code("\n".join(self.logs[-10:]), language="shell")

    def error(self, msg, *args):
        try:
            formatted = msg % args if args else msg
        except:
            formatted = msg
        self.logs.append(f"🔴 ERR: {formatted}")
        self.placeholder.code("\n".join(self.logs[-10:]), language="shell")

# Execution Block
if st.session_state.processing_started and st.session_state.final_story_to_process:
    if openrouter_key: settings.OPENROUTER_API_KEY = openrouter_key
    if replicate_key: settings.REPLICATE_API_TOKEN = replicate_key
    if elevenlabs_key: settings.ELEVENLABS_API_KEY = elevenlabs_key

    st.markdown("---")
    st.subheader("⚙️ Processing Pipeline")
    log_placeholder = st.empty()
    st_logger = StreamlitLogger(log_placeholder)
    
    import core.logger
    original_get_logger = core.logger.get_logger
    core.logger.get_logger = lambda name: st_logger
    
    progress_bar = st.progress(0)
    
    try:
        with st.spinner("Agent 1: Scriptwriter is analyzing the story..."):
            script_agent = ScriptwriterAgent()
            scenes = script_agent.run(st.session_state.final_story_to_process)
            progress_bar.progress(20)
            
        with st.spinner("Agent 2: Voice is synthesizing narration..."):
            voice_agent = VoiceAgent()
            scenes = voice_agent.run(scenes)
            progress_bar.progress(40)
            
        with st.spinner("Agent 3: Visual Agent generating AI clips..."):
            visual_agent = VisualAgent() 
            scenes = visual_agent.run(scenes)
            progress_bar.progress(60)
            
        with st.spinner("Agent 4: Subtitle alignment..."):
            subtitle_agent = SubtitleAgent()
            scenes = subtitle_agent.run(scenes)
            progress_bar.progress(80)
            
        with st.spinner("Agent 5: Director is assembling the final cut..."):
            director = DirectorAgent()
            mp4_path = director.run(scenes, output_filename=f"ui_output_{int(time.time())}.mp4")
            progress_bar.progress(100)
            
        st.success("✅ Video successfully generated!")
        st.subheader("🎥 Your Micro-Drama")
        st.video(mp4_path)
        
    except Exception as e:
        st.error(f"Pipeline Failed: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        
    finally:
        core.logger.get_logger = original_get_logger
        st.session_state.processing_started = False
