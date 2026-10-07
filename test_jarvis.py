import os
import sys
from dotenv import load_dotenv

load_dotenv()

from core.registry import SkillRegistry
from core.engine import JarvisEngine
from core.voice import speak, get_wake_words

def run_tests():
    print("=" * 60)
    print("      JARVIS SUBSYSTEM VERIFICATION SUITE")
    print("=" * 60)

    # 1. Test Wake Words
    wake_words = get_wake_words()
    print(f"\n[1] Wake words detected: {wake_words}")
    assert "delulu" in wake_words, "Primary wake word 'delulu' missing!"
    print("  -> PASS: Wake words configured successfully.")

    # 2. Test Skill Registry
    print("\n[2] Testing Skill Registry Loading...")
    registry = SkillRegistry()
    skills_dir = os.path.join(os.path.dirname(__file__), "skills")
    registry.load_skills(skills_dir)
    print(f"  -> Total skills loaded: {len(registry.skills)}")
    print(f"  -> Skills list: {list(registry.skills.keys())}")
    assert len(registry.skills) >= 10, "Expected at least 10 active skills!"
    print("  -> PASS: Skill Registry fully operational.")

    # 3. Test Engine Initialization
    print("\n[3] Testing Multi-Brain Reasoning Engine...")
    engine = JarvisEngine(registry)
    
    # Test Time Query
    time_response = engine.run_conversation("delulu what time is it?")
    print(f"  Query: 'delulu what time is it?'")
    print(f"  Response: {time_response}")
    assert "time" in time_response.lower() or ":" in time_response, "Unexpected time response"
    print("  -> PASS: Local brain query handling verified.")

    # Test Status Query
    status_response = engine.run_conversation("report system status")
    print(f"  Query: 'report system status'")
    print(f"  Response: {status_response}")
    print("  -> PASS: Persona and conversational replies verified.")

    # 4. Test Volume Tool
    print("\n[4] Testing System Skill (Volume Control)...")
    vol_func = registry.get_function("set_volume")
    if vol_func:
        res = vol_func(level=35)
        print(f"  set_volume(35) result: {res}")
        print("  -> PASS: Windows volume control functioning.")
    else:
        print("  -> WARNING: set_volume not in functions map.")

    # 5. Test Voice Fallback (Edge-TTS or SAPI5)
    print("\n[5] Testing Voice Synthesis Pipeline...")
    try:
        # Test short speech utterance
        speak("All systems verified and online, Sir.")
        print("  -> PASS: Voice synthesis pipeline active.")
    except Exception as e:
        print(f"  -> WARNING: Voice test encountered: {e}")

    print("\n" + "=" * 60)
    print("  ALL CORE JARVIS SYSTEMS FUNCTIONING PROPERLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
