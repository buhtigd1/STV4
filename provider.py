import requests
import re
from datetime import datetime

SOURCE_URL = "https://raw.githubusercontent.com/tongxunlu/super/main/live.m3u"

OUTPUT_FILE = "stv4.m3u"
LOG_FILE    = "stv4.log"

HEADER = '#EXTM3U url-tvg=""'

PRIORITY = [
    "sky premier legue",   # typo preserved
    "sky sports pl",
    "sky sport nz",
    "sky sport aq",
    "sky sports football",
    "sky premier",
    "tnt sports 1",
    "tnt sports 3",
    "tnt sports aq",
    "tnt sports 1 aq",
    "premier sports 1",
    "premier sports 2",
    "peacock",
    "peacock fhd aq",
    "fubo sports",
    "fubo sports aq",
    "hub premier 1",
    "usa network",
    "bein sports",
    "bein sports 1",
    "bein sports 2",
    "bein sports 3",
    "paramount+ aq",
    "paramount+ es aq",
    "paramount+ pt aq",
    "espn eng",
    "espn deportes",
    "fancode",
    "fancode aq"
]

def download(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"❌ Failed: {url}\n{e}")
        return None

def parse_m3u(content):
    if not content:
        return []
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

def clean_extinf(line):
    line = re.sub(r'\s*group-title="[^"]+"', '', line, flags=re.IGNORECASE)
    line = re.sub(r'\s*tvg-name="[^"]+"', '', line, flags=re.IGNORECASE)
    return line

def sort_entries(entries):
    counts = {k: 0 for k in PRIORITY}
    others_count = 0

    def priority_index(block):
        line = block[0].lower()
        for idx, keyword in enumerate(PRIORITY):
            if keyword in line:
                counts[keyword] += 1
                return idx
        nonlocal others_count
        others_count += 1
        return len(PRIORITY)

    sorted_entries = sorted(entries, key=priority_index)
    return sorted_entries, counts, others_count

def main():
    log_entries = [f"Run started at {datetime.now().isoformat()}"]

    print("Downloading playlist...")
    source = download(SOURCE_URL)
    if source is None:
        return

    print("Parsing playlist...")
    entries = parse_m3u(source)

    print("Sorting channels...")
    ordered_entries, counts, others_count = sort_entries(entries)

    print(f"Total channels found: {len(entries)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        for block in ordered_entries:
            for idx, line in enumerate(block):
                if idx == 0:
                    line = clean_extinf(line)
                f.write(line + "\n")

    with open(LOG_FILE, "w", encoding="utf-8") as logf:
        for entry in log_entries:
            logf.write(entry + "\n")
        logf.write(f"✅ Done: saved to {OUTPUT_FILE}\n")
        logf.write("Channels sorted by priority list\n")
        for keyword, count in counts.items():
            logf.write(f"{keyword}: {count} channels\n")
        logf.write(f"others: {others_count} channels\n")

    print(f"✅ Done: saved to {OUTPUT_FILE}, log written to {LOG_FILE}")

if __name__ == "__main__":
    main()
