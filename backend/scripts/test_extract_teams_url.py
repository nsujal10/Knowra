import os
import glob
import re

def extract_active_teams_meeting_url():
    # 1. Modern MSTeams 2.1 WebView2 LevelDB
    pattern = os.path.expandvars(r"%LOCALAPPDATA%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\EBWebView\*\IndexedDB\https_teams.microsoft.com_0.indexeddb.leveldb\*.*")
    files = glob.glob(pattern)
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        for f in files[:8]:
            try:
                with open(f, "rb") as fp:
                    content = fp.read().decode("utf-8", errors="ignore")
                    matches = re.findall(r"https://teams\.microsoft\.com/l/meetup-join/[^\s\"\'\\<>\)]+", content)
                    if matches:
                        return matches[0]
            except Exception:
                pass

    # 2. Classic Teams logs
    classic_path = os.path.expandvars(r"%APPDATA%\Microsoft\Teams\logs.txt")
    if os.path.exists(classic_path):
        try:
            with open(classic_path, "rb") as fp:
                content = fp.read().decode("utf-8", errors="ignore")
                matches = re.findall(r"https://teams\.microsoft\.com/l/meetup-join/[^\s\"\'\\<>\)]+", content)
                if matches:
                    return matches[-1]
        except Exception:
            pass

    return None

url = extract_active_teams_meeting_url()
print("Extracted URL:", repr(url))
