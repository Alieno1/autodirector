import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

def build_pdf(filename="Auto_Director_Interview_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#1E293B")    # Slate 800
    ACCENT = colors.HexColor("#2563EB")     # Royal Blue
    SECONDARY = colors.HexColor("#475569")  # Slate 600
    BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
    BORDER_CLR = colors.HexColor("#CBD5E1") # Slate 300
    HIGHLIGHT = colors.HexColor("#EFF6FF")  # Blue 50

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=ACCENT,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY,
        spaceAfter=6
    )

    pitch_style = ParagraphStyle(
        'PitchText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14.5,
        textColor=PRIMARY,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=PRIMARY
    )

    qa_q = ParagraphStyle(
        'QA_Q',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=ACCENT,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True
    )

    qa_a = ParagraphStyle(
        'QA_A',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY,
        spaceAfter=8
    )

    story = []

    # Title & Subtitle Header
    story.append(Paragraph("🎬 Auto-Director: Interview Preparation Guide", title_style))
    story.append(Paragraph("Comprehensive Project Breakdown, File-by-File Analysis & Technical Q&A", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=12))

    # Section 1: Executive Summary / Elevator Pitch
    story.append(Paragraph("1. Executive Summary (Elevator Pitch)", h1_style))
    pitch_html = (
        "<b>\"Auto-Director is an autonomous, agentic multi-tier AI micro-drama video generator.</b> "
        "It converts raw story text (in English, Hindi, or Hinglish) into fully animated, voice-narrated, "
        "subtitle-aligned 9:16 vertical short-form videos (YouTube Shorts / Instagram Reels / TikTok).<br/><br/>"
        "It features a <b>5-agent modular pipeline</b> with an <b>audio-driven timing architecture</b>, "
        "<b>multi-tier resilience fallbacks</b> (ElevenLabs &rarr; gTTS &rarr; espeak for voice; Gemini &rarr; Pollinations &rarr; Stock &rarr; PIL for visuals), "
        "and custom <b>Devanagari font resolution</b> with 40x faster Pillow-based subtitle rendering.\""
    )
    
    pitch_table = Table([[Paragraph(pitch_html, pitch_style)]], colWidths=[530])
    pitch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HIGHLIGHT),
        ('BOX', (0,0), (-1,-1), 1, ACCENT),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(pitch_table)
    story.append(Spacer(1, 10))

    # Section 2: Architecture & 5-Agent Flow
    story.append(Paragraph("2. System Architecture & 5-Agent Pipeline", h1_style))
    
    flow_data = [
        [Paragraph("<b>Agent</b>", h2_style), Paragraph("<b>Primary Provider & Fallbacks</b>", h2_style), Paragraph("<b>Key Output / Responsibility</b>", h2_style)],
        [
            Paragraph("<b>1. Scriptwriter</b>", body_style),
            Paragraph("Gemini 2.5 Flash &rarr;<br/>Offline Regex Splitter", body_style),
            Paragraph("Parses story into 4-8 scenes (narration, visual prompt, mood).", body_style)
        ],
        [
            Paragraph("<b>2. Voice</b>", body_style),
            Paragraph("ElevenLabs &rarr;<br/>gTTS &rarr; espeak-ng", body_style),
            Paragraph("Synthesizes parallel audio per scene. <b>Calculates exact audio duration.</b>", body_style)
        ],
        [
            Paragraph("<b>3. Visual</b>", body_style),
            Paragraph("Gemini 3.1 Flash &rarr;<br/>Pollinations &rarr; Stock &rarr; PIL Cards", body_style),
            Paragraph("Generates 9:16 vertical visual stills with MD5 prompt caching.", body_style)
        ],
        [
            Paragraph("<b>4. Subtitles</b>", body_style),
            Paragraph("Proportional Character Split &rarr;<br/>OpenAI Whisper", body_style),
            Paragraph("Computes word-level start/end timestamps per caption chunk.", body_style)
        ],
        [
            Paragraph("<b>5. Director</b>", body_style),
            Paragraph("MoviePy + PIL Engine +<br/>FFmpeg H.264 Muxer", body_style),
            Paragraph("Renders Ken Burns zoom, burned-in subtitles, and final MP4 export.", body_style)
        ]
    ]

    t_flow = Table(flow_data, colWidths=[110, 160, 260])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 12))

    # Section 3: File-by-File Breakdown
    story.append(Paragraph("3. Detailed File-by-File Breakdown", h1_style))

    files_info = [
        ("main.py", "CLI Entry Point & Orchestrator", 
         "Built with Typer & Rich. Runs the 5 agents sequentially, measures per-stage latency, handles user interruptions (KeyboardInterrupt), and displays rich terminal progress bars."),
        
        ("config.py", "Central Pydantic Configuration", 
         "Uses pydantic-settings to validate environment variables (.env) at startup. Dynamically computes operating mode (active_mode: LIVE vs DEMO) based on available API keys."),
        
        ("models.py", "Domain Data Models (DTOs)", 
         "Defines Caption and Scene dataclasses. Scene incrementally holds data as it flows through agents. Includes safe dictionary deserialization (Scene.from_dict) without mutating caller data."),
        
        ("agents/scriptwriter_agent.py", "Agent 1: Scriptwriter", 
         "Prompts Gemini for structured JSON scene breakdown. Falls back to deterministic rule-based sentence splitting (_offline_split) if network calls fail."),
        
        ("agents/voice_agent.py", "Agent 2: Voice Actor", 
         "Synthesizes narration audio concurrently via ThreadPoolExecutor. Tries ElevenLabs, then gTTS, then espeak-ng. Measures actual waveform duration from .wav file (critical for downstream timing)."),
        
        ("agents/visual_agent.py", "Agent 3: Cinematographer", 
         "Generates vertical 9:16 images concurrently. Employs 4-tier fallback: Gemini Image Gen -> Pollinations Turbo -> Stock Photos -> PIL Mood Gradients. Uses MD5 hash caching for prompts."),
        
        ("agents/subtitle_agent.py", "Agent 4: Subtitle Sync Engineer", 
         "Calculates 3-word caption timings. Uses character-length proportional timing by default, or OpenAI Whisper forced alignment (USE_WHISPER=true) for real word-level timestamps."),
        
        ("agents/director_agent.py", "Agent 5: Video Renderer", 
         "Applies Ken Burns scaling zoom (_ken_burns_clip). Renders subtitle overlays with dynamic Devanagari/Latin font resolution (_resolve_font) using Pillow. Guarantees resource cleanup with try...finally clip closing."),
        
        ("core/retry.py", "Resilience Decorator", 
         "Custom @retry_api_call decorator using tenacity for exponential backoff. Intelligent exception predicate filters out non-transient HTTP 4xx errors (e.g. 401 Unauthorized, 402 Payment Required)."),
        
        ("core/exceptions.py", "Typed Error Hierarchy", 
         "Custom pipeline exception tree inheriting from AutoDirectorError (e.g. ScriptwriterError, VoiceError, VisualError, DirectorError) for explicit stage-specific error handling."),
        
        ("core/logger.py", "Rich Terminal Logger", 
         "Configures unified logging output across all modules with colorized levels.")
    ]

    file_table_data = [[Paragraph("<b>File Path</b>", h2_style), Paragraph("<b>Role & Key Implementation Details</b>", h2_style)]]
    for fname, role, desc in files_info:
        file_table_data.append([
            Paragraph(f"<b>{fname}</b><br/><font color='{SECONDARY.hexval()}'>{role}</font>", body_style),
            Paragraph(desc, body_style)
        ])

    t_files = Table(file_table_data, colWidths=[160, 370])
    t_files.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_files)
    story.append(Spacer(1, 12))

    # Section 4: Data Structures & CS Concepts
    story.append(Paragraph("4. Data Structures, Algorithms & CS Concepts Used", h1_style))
    dsa_data = [
        [Paragraph("<b>Concept / Category</b>", h2_style), Paragraph("<b>Implementation & Usage in Code</b>", h2_style)],
        [
            Paragraph("<b>Typed State Machine (DTOs)</b>", body_style),
            Paragraph("Custom <b>Scene</b> & <b>Caption</b> dataclasses (<code>models.py</code>). Validation helpers (<code>is_voice_ready</code>, <code>is_render_ready</code>) enforce clean state transitions across agents.", body_style)
        ],
        [
            Paragraph("<b>Multithreading & Concurrency</b>", body_style),
            Paragraph("<code>ThreadPoolExecutor</code> in <code>voice_agent.py</code> and <code>visual_agent.py</code> processes scene tasks concurrently (<code>max_workers=4</code>), accelerating execution by ~6x.", body_style)
        ],
        [
            Paragraph("<b>Proportional Timing Algorithm</b>", body_style),
            Paragraph("Math-based linear duration allocation in <code>subtitle_agent.py</code>: <i>T_chunk = T_scene * (Chars_chunk / Chars_total)</i> when Whisper is unavailable.", body_style)
        ],
        [
            Paragraph("<b>Mathematical Animation Scale</b>", body_style),
            Paragraph("Time-dependent continuous zoom function in <code>director_agent.py</code>: <i>S(t) = S_base * (1 + k * t/T)</i> for smooth Ken Burns pan/zoom motion.", body_style)
        ],
        [
            Paragraph("<b>Prompt Memoization (Caching)</b>", body_style),
            Paragraph("Hash-map disk caching with MD5 hashes of visual prompts (<code>visual_agent.py</code>) to bypass duplicate AI image generation API calls.", body_style)
        ],
        [
            Paragraph("<b>Exponential Backoff Retries</b>", body_style),
            Paragraph("Decorator pattern in <code>core/retry.py</code> using Tenacity. Retries transient 429/5xx status codes while skipping non-retryable 4xx errors.", body_style)
        ],
        [
            Paragraph("<b>Unicode Script Inspection</b>", body_style),
            Paragraph("O(N) character range inspection (<code>0x0900-0x097F</code>) in <code>director_agent.py</code> for dynamic font path assignment (Devanagari vs Latin).", body_style)
        ]
    ]

    t_dsa = Table(dsa_data, colWidths=[170, 360])
    t_dsa.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_dsa)
    story.append(Spacer(1, 12))

    # Section 5: Key Engineering Highlights
    story.append(Paragraph("5. Key Engineering Highlights & Architectural Decisions", h1_style))
    highlights = [
        "<b>Audio-Driven Timing Architecture:</b> Scene lengths are strictly driven by the actual waveform duration of the synthesized audio (AudioFileClip.duration). Subtitles and Ken Burns animation timings are bound to this value for 100% lip/sound sync.",
        "<b>Multi-Tier Fallback Resilience:</b> Zero hard failure points. If external APIs fail or rate limit, the system gracefully degrades down the provider chain (e.g. ElevenLabs -> gTTS -> espeak-ng) without crashing.",
        "<b>Pillow-Based Subtitle Engine:</b> Avoids ImageMagick dependency bottlenecks by pre-rendering captions to transparent PNGs with PIL (stroke_width=3, stroke_fill=black, rounded pill background). Yields 40x faster rendering speed.",
        "<b>Multilingual Font Resolution:</b> Inspects text for Unicode Devanagari range (0x0900 - 0x097F) to select NotoSansDevanagari vs. DejaVuSans, eliminating font box ('tofu') rendering bugs.",
        "<b>Strict Clip Lifecycle Cleanup:</b> MoviePy clips are managed inside try...finally blocks, ensuring clip.close() is called on all video/audio handles to prevent FFmpeg process leaks."
    ]

    for h in highlights:
        story.append(Paragraph(f"• {h}", body_style))
    story.append(Spacer(1, 10))

    # Section 6: Top Interview Q&A
    story.append(Paragraph("6. Top Technical Interview Q&A Cheatsheet", h1_style))

    qa_list = [
        ("Q1: How do you ensure audio and video remain perfectly synchronized?",
         "<b>Answer:</b> We use an Audio-Driven Timing Architecture. We never assume a fixed scene duration. VoiceAgent synthesizes audio first and extracts the exact duration from the audio waveform. All video clip lengths, Ken Burns scaling progress, and caption timestamp chunks are calculated dynamically based on this exact duration."),

        ("Q2: How does the system handle external API rate limits or outages?",
         "<b>Answer:</b> Each agent encapsulates a multi-tier fallback mechanism wrapped with exponential backoff retries via Tenacity. If a primary service like ElevenLabs or Gemini fails or returns 429, the system logs a warning and gracefully falls back to local/free alternatives like gTTS, espeak-ng, Pollinations Turbo, or PIL gradient cards."),

        ("Q3: Why did you build custom PIL subtitle rendering instead of using MoviePy's TextClip?",
         "<b>Answer:</b> MoviePy's default TextClip relies on ImageMagick binaries, which are slow, platform-dependent, and struggle with Hindi Devanagari font wrapping. By rendering captions onto transparent PNGs in memory using Pillow, we achieved 40x faster rendering, perfect rounded pill contrast overlays, and cross-platform reliability."),

        ("Q4: How do you support multilingual stories (English vs. Hindi)?",
         "<b>Answer:</b> We implement dynamic font resolution in DirectorAgent. It scans subtitle text for Devanagari Unicode characters (0x0900-0x097F). If found, it automatically assigns NotoSansDevanagari.ttf; otherwise, it uses DejaVuSans-Bold.ttf. Additionally, ScriptwriterAgent ensures image prompts are always generated in English for AI models while narration matches the input language."),

        ("Q5: How do you prevent resource and process leaks during video rendering?",
         "<b>Answer:</b> Video compositing spawns multiple underlying FFmpeg subprocesses. We encapsulate the entire compositing loop in DirectorAgent with a strict try...finally block that explicitly calls .close() on all image, audio, and composite clips even if rendering fails midway.")
    ]

    for q, a in qa_list:
        qa_block = [
            Paragraph(q, qa_q),
            Paragraph(a, qa_a)
        ]
        story.append(KeepTogether(qa_block))

    doc.build(story)
    print(f"PDF successfully built at: {os.path.abspath(filename)}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "Auto_Director_Interview_Guide.pdf"
    build_pdf(out_file)
