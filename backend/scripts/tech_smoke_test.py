import sys
import os
import time
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def run_script(script_name):
    t0 = time.time()
    print(f"\n--- Running {script_name} ---")
    res = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    t1 = time.time()
    
    if res.returncode == 0:
        print(res.stdout)
        print(f"[PASS] {script_name} ({t1-t0:.2f}s)")
    else:
        print(res.stderr)
        print(f"[FAIL] {script_name}")

def tech_smoke_test():
    print("======================================")
    print(" TECHNOLOGY STACK END-TO-END SMOKE TEST ")
    print("======================================")
    
    scripts = [
        "test_db.py",
        "test_storage.py",
        "test_celery.py",
        "test_audio_ffmpeg.py",
        "test_ai_stt_diarization.py",
        "test_llm_structured.py"
    ]
    
    for s in scripts:
        script_path = os.path.join(os.path.dirname(__file__), s)
        run_script(script_path)

if __name__ == "__main__":
    tech_smoke_test()
