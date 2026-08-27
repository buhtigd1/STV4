import requests
import re
from datetime import datetime

SOURCE_URL = "https://raw.githubusercontent.com/tongxunlu/super/main/live.m3u"

OUTPUT_FILE = "stv4.m3u"
LOG_FILE    = "stv4.log"

HEADER = '#EXTM3U url-tvg=""'

def download(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        return f"❌ Failed: {url}\n{e}"

def parse_m3u(content):
    lines = content.splitlines()
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            block = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                block.append(next_line)
                if not next_line.startswith("#"):
                    break
                j += 1
            entries.append(block)
            i = j
        else:
            i += 1
    return entries

def main():
    log_entries = [f"Run started at {datetime.now().isoformat()}"]

    print("Downloading playlist...")
    source = download(SOURCE_URL)

    print("Parsing playlist...")
    entries = parse_m3u(source)

    # Separate EPL channels first
    epl_blocks = []
    other_blocks = []
    for block in entries:
        if "[english premier league]" in block[0].lower():
            epl_blocks.append(block)
        else:
            other_blocks.append(block)

    ordered_entries = epl_blocks + other_blocks

    print(f"Total channels found: {len(entries)}")
    print(f"EPL channels prioritized: {len(epl_blocks)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        for block in ordered_entries:
            for idx, line in enumerate(block):
                if idx == 0:
                    line = clean_extinf(line)
                f.write(line + "\n")

    # Always write a log file
    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        for entry in log_entries:
            logf.write(entry + "\n")
        logf.write(f"✅ Done: saved to {OUTPUT_FILE}\n")
        logf.write(f"EPL channels placed on top: {len(epl_blocks)}\n")

    print(f"✅ Done: saved to {OUTPUT_FILE}, log written to {LOG_FILE}")

if __name__ == "__main__":
    main()
