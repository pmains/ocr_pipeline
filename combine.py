import re
from pathlib import Path

def remove_redundant_headers(pages):
    combined = []
    seen_headings = set()
    header_re = re.compile(r'^(#+)\s+(.*)')

    for page in pages:
        lines = page.splitlines()
        for line in lines:
            m = header_re.match(line)
            if m:
                title = m.group(2).strip().lower()
                if title in seen_headings:
                    continue
                seen_headings.add(title)
            combined.append(line)
        combined.append('')
    return '\n'.join(combined)

def combine_all(input_dirs, output_file):
    output_file = Path(output_file)
    pages = []
    for input_dir in input_dirs:
        for f in sorted(Path(input_dir).glob("*.txt")):
            page_text = f.read_text(encoding="utf-8")
            if "--- EMPTY ---" in page_text:
                continue
            pages.append(page_text)
    combined_text = remove_redundant_headers(pages)
    with output_file.open("w", encoding="utf-8") as out:
        out.write(combined_text)
    print(f"[combine] Wrote {output_file}")