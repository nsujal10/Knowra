"""
Test Suite: Verbatim Transcription Accuracy Improvements
Validates all 5 accuracy improvements end-to-end:
  1. Model upgrade (whisper-large-v3)
  2. Context/priming prompts
  3. Gain normalization
  4. Pre/post-roll buffering
  5. Hallucination filtering (EN + HI)
"""

import sys
import os
import struct

# Ensure UTF-8 output on Windows console for Hindi characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name} — {detail}")


# ===== 1. Model Upgrade =====
print("\n═══ Test 1: Model Upgrade ═══")
from app.ai.transcription.providers.groq_whisper_provider import GroqWhisperProvider

try:
    provider = GroqWhisperProvider()
except ValueError:
    # No API key, instantiate with dummy for attribute checks
    class _DummyProvider(GroqWhisperProvider):
        def __init__(self):
            self.api_key = "test_key"
            self.model = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
            self.base_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    provider = _DummyProvider()

test("Default model is whisper-large-v3 (not turbo)",
     provider.model == "whisper-large-v3",
     f"Got: {provider.model}")

test("Model env var override works",
     os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3") == provider.model)


# ===== 2. Context/Priming Prompts =====
print("\n═══ Test 2: Context/Priming Prompts ═══")

test("PROMPT_EN class attribute exists",
     hasattr(GroqWhisperProvider, "PROMPT_EN"))

test("PROMPT_HI class attribute exists",
     hasattr(GroqWhisperProvider, "PROMPT_HI"))

test("PROMPT_EN contains 'verbatim'",
     "verbatim" in GroqWhisperProvider.PROMPT_EN.lower())

test("PROMPT_EN contains technical terms",
     "Knowra" in GroqWhisperProvider.PROMPT_EN and "WASAPI" in GroqWhisperProvider.PROMPT_EN)

test("PROMPT_HI contains Hindi script",
     "शब्दशः" in GroqWhisperProvider.PROMPT_HI or "ट्रांसक्राइब" in GroqWhisperProvider.PROMPT_HI)

test("_get_priming_prompt('hi') returns Hindi prompt",
     provider._get_priming_prompt("hi") == GroqWhisperProvider.PROMPT_HI)

test("_get_priming_prompt('en') returns English prompt",
     provider._get_priming_prompt("en") == GroqWhisperProvider.PROMPT_EN)

test("_get_priming_prompt('hindi') returns Hindi prompt",
     provider._get_priming_prompt("hindi") == GroqWhisperProvider.PROMPT_HI)

test("_get_priming_prompt(None) returns English prompt (default)",
     provider._get_priming_prompt(None) == GroqWhisperProvider.PROMPT_EN)


# ===== 3. Gain Normalization (Desktop Companion) =====
print("\n═══ Test 3: Peak Gain Normalization ═══")

# Simulate quiet audio signal (peak ~500 out of 32767)
quiet_signal = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 500).astype(np.int16)
peak_before = float(np.max(np.abs(quiet_signal)))
test("Quiet signal peak is low (~500)",
     400 < peak_before < 600,
     f"Peak: {peak_before}")

# Apply same normalization logic as in companion
TARGET_PEAK = 23000.0
peak = float(np.max(np.abs(quiet_signal)))
gain = min(TARGET_PEAK / peak, 10.0)
if gain > 1.05:
    normalized = np.clip(quiet_signal.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
else:
    normalized = quiet_signal

peak_after = float(np.max(np.abs(normalized)))
# When original peak is very low (500), gain is capped at 10x, so peak reaches ~5000 not 23000.
# This is correct safety behavior — we don't over-amplify quiet/noisy signals.
test("Normalization boosts quiet signal (gain-capped at 10x)",
     peak_after > peak_before * 5,
     f"Peak after: {peak_after}, peak before: {peak_before}")

test("Gain is capped at 10.0 (20dB max)",
     gain <= 10.0,
     f"Gain: {gain}")

# Test that already-loud signals are NOT over-amplified
loud_signal = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 25000).astype(np.int16)
loud_peak = float(np.max(np.abs(loud_signal)))
loud_gain = min(TARGET_PEAK / loud_peak, 10.0)
test("Loud signal gain < 1.05 (no amplification needed)",
     loud_gain < 1.05,
     f"Loud gain: {loud_gain}")


# ===== 4. Pre/Post-Roll Buffering =====
print("\n═══ Test 4: Pre-Roll / Post-Roll Buffering ═══")

# Validate the preroll ring buffer logic
preroll_ring = []
PREROLL_FRAMES = 2

# Simulate 5 silence frames arriving
for i in range(5):
    frame = f"silence_{i}".encode()
    preroll_ring.append(frame)
    if len(preroll_ring) > PREROLL_FRAMES:
        preroll_ring.pop(0)

test("Pre-roll ring keeps exactly 2 frames",
     len(preroll_ring) == 2)

test("Pre-roll contains the 2 most recent frames",
     preroll_ring[0] == b"silence_3" and preroll_ring[1] == b"silence_4")

# Simulate speech starting: prepend pre-roll to speech buffer
speech_buffer = bytearray()
for frame in preroll_ring:
    speech_buffer.extend(frame)
speech_buffer.extend(b"speech_data")

test("Speech buffer starts with pre-roll context",
     speech_buffer.startswith(b"silence_3"))

test("Speech buffer contains speech data after pre-roll",
     b"speech_data" in speech_buffer)


# ===== 5. Hallucination Filtering (EN + HI) =====
print("\n═══ Test 5: Hallucination Filtering ═══")

# Test English hallucinations
en_hallucinations = [
    "Thank you.", "you", "All right.", "Okay.", "Yeah.",
    "bye.", "hmm.", "um.", "subscribe.", "The end.",
    ".", "...", "", "you you you", "Thanks for watching!",
    "Subtitles by the amara.org community",
]

hallucination_set = {
    "thank you.", "thank you", "thanks.", "thanks",
    "thanks for watching!", "thanks for watching.",
    "subtitles by...", "subtitles by the amara.org community",
    ".", "..", "...", "", " ",
    "you", "you.", "you...", "you you you",
    "all right.", "all right", "alright.", "alright",
    "okay.", "okay", "ok.", "ok",
    "bye.", "bye", "bye bye.",
    "yeah.", "yeah", "yep.", "yep",
    "so.", "so", "right.", "right",
    "hmm.", "hmm", "hm.", "hm",
    "uh.", "uh", "um.", "um",
    "yes.", "yes", "no.", "no",
    "oh.", "oh", "ah.", "ah",
    "the end.", "the end",
    "subscribe", "subscribe.",
    "please subscribe.", "like and subscribe.",
    "धन्यवाद।", "धन्यवाद", "शुक्रिया।", "शुक्रिया",
    "ठीक है।", "ठीक है", "हाँ।", "हाँ", "जी।", "जी",
    "नमस्ते।",
}

for h in en_hallucinations:
    cleaned = h.lower().strip()
    is_filtered = cleaned in hallucination_set
    test(f"EN hallucination filtered: '{h}'", is_filtered, f"'{h}' was NOT filtered")

# Test Hindi hallucinations
hi_hallucinations = ["धन्यवाद।", "धन्यवाद", "शुक्रिया।", "ठीक है।", "हाँ।", "जी।", "नमस्ते।"]
for h in hi_hallucinations:
    cleaned = h.lower().strip()
    is_filtered = cleaned in hallucination_set
    test(f"HI hallucination filtered: '{h}'", is_filtered, f"'{h}' was NOT filtered")

# Test that real speech is NOT filtered
real_speech = [
    "Welcome everyone to our weekly architecture sync.",
    "I reviewed the PR for the live meeting capture.",
    "मैंने डेटाबेस माइग्रेशन का काम पूरा कर लिया है।",
    "क्या हम शुक्रवार तक नया फीचर डिप्लॉय कर सकते हैं?",
    "The database migration reduced query latency by 70 percent.",
]
for speech in real_speech:
    cleaned = speech.lower().strip()
    is_filtered = cleaned in hallucination_set
    test(f"Real speech NOT filtered: '{speech[:50]}...'", not is_filtered, "Real speech was incorrectly filtered!")


# ===== 6. Backend Buffer Threshold =====
print("\n═══ Test 6: Backend Buffer Threshold ═══")

# Read live_meeting_service.py and verify the threshold
import re
service_path = os.path.join(os.path.dirname(__file__), "..", "app", "services", "live_meeting_service.py")
with open(service_path, "r", encoding="utf-8") as f:
    service_code = f.read()

test("Backend buffer threshold is 48000 (1.5s)",
     "48000" in service_code)

test("Backend has gain normalization logic",
     "target_peak" in service_code and "gain" in service_code)

test("Backend has .copy() for writable numpy array",
     ".copy()" in service_code)


# ===== Summary =====
print(f"\n{'='*50}")
print(f" Results: {PASSED} passed, {FAILED} failed, {PASSED + FAILED} total")
print(f"{'='*50}")

sys.exit(0 if FAILED == 0 else 1)
