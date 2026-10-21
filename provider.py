import requests
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCE_URL = "https://raw.githubusercontent.com/tongxunlu/super/main/live.m3u"

OUTPUT_FILE = "stv4.m3u"
LOG_FILE = "stv4.log"

HEADER = '#EXTM3U url-tvg=""'

MAX_WORKERS = 100
CHECK_TIMEOUT = 5

PRIORITY = [
    "sky premier legue",
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
    "fancode aq",
    "formula 1",
    "apple tv hdr",
    "driver tracker",
    "driver data",
    "tsn 1 fhd",
    "sky sports",
    "sky f1 it"
]


def download(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Failed downloading source:\n{e}")
        return None


def parse_m3u(content):
    if not content:
        return []

    lines = content.splitlines()
    entries = []
    i = 0

    while i < len(lines):

        if lines[i].strip().startswith("#EXTINF"):

            block = [lines[i].strip()]
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

    line = re.sub(
        r'\s*group-title="[^"]*"',
        '',
        line,
        flags=re.IGNORECASE
    )

    line = re.sub(
        r'\s*tvg-name="[^"]*"',
        '',
        line,
        flags=re.IGNORECASE
    )

    # Remove:
    # Arsenal vs Chelsea -
    # Hull City v Man United -
    # Team A versus Team B -
    line = re.sub(
        r'([^,]*?\b(?:vs|v|versus)\b[^-]*-\s*)',
        '',
        line,
        flags=re.IGNORECASE
    )

    line = re.sub(r"\s+", " ", line).strip()

    return line


def sort_entries(entries):

    counts = {k: 0 for k in PRIORITY}
    others_count = 0

    def get_priority(block):

        nonlocal others_count

        text = block[0].lower()

        for idx, keyword in enumerate(PRIORITY):

            if keyword in text:
                counts[keyword] += 1
                return idx

        others_count += 1
        return len(PRIORITY)

    sorted_entries = sorted(entries, key=get_priority)

    return sorted_entries, counts, others_count


def check_stream(url, timeout=CHECK_TIMEOUT):

    try:

        r = requests.get(
            url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if r.status_code not in (200, 206):
            return False

        if ".m3u8" in url.lower():

            try:
                text = r.text[:5000]

                if "#EXTM3U" not in text and "#EXT-X-" not in text:
                    return False

            except Exception:
                pass

        return True

    except Exception:
        return False


def check_block(block):

    url = block[-1].strip()

    if not url.startswith(("http://", "https://")):
        return ("SKIP", block)

    if check_stream(url):
        return ("OK", block)

    return ("DEAD", block)


def main():

    started = datetime.now()

    print("Downloading playlist...")
    source = download(SOURCE_URL)

    if not source:
        return

    print("Parsing...")
    entries = parse_m3u(source)

    print(f"Found {len(entries)} channels")

    print("Sorting...")
    ordered_entries, counts, others_count = sort_entries(entries)

    print(
        f"Checking links using {MAX_WORKERS} threads..."
    )

    working_entries = []
    dead_entries = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = [
            executor.submit(check_block, block)
            for block in ordered_entries
        ]

        checked = 0

        for future in as_completed(futures):

            status, block = future.result()

            checked += 1

            if checked % 50 == 0:
                print(
                    f"Checked {checked}/{len(ordered_entries)}"
                )

            if status in ("OK", "SKIP"):
                working_entries.append(block)
            else:
                dead_entries.append(block)

    print(
        f"Working: {len(working_entries)} | Dead: {len(dead_entries)}"
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(HEADER + "\n")

        for block in working_entries:

            for idx, line in enumerate(block):

                if idx == 0:
                    line = clean_extinf(line)

                f.write(line + "\n")

    with open(
        LOG_FILE,
        "w",
        encoding="utf-8"
    ) as log:

        log.write(
            f"Run started: {started.isoformat()}\n"
        )

        log.write(
            f"Run finished: {datetime.now().isoformat()}\n\n"
        )

        log.write(
            f"Total channels: {len(entries)}\n"
        )

        log.write(
            f"Working channels: {len(working_entries)}\n"
        )

        log.write(
            f"Dead channels: {len(dead_entries)}\n"
        )

        log.write(
            f"Others: {others_count}\n\n"
        )

        for keyword, count in counts.items():
            log.write(
                f"{keyword}: {count}\n"
            )

        log.write("\n=== DEAD LINKS ===\n")

        for block in dead_entries:
            log.write(block[-1] + "\n")

    print(f"Done: {OUTPUT_FILE}")
    print(f"Log : {LOG_FILE}")


if __name__ == "__main__":
    main()
