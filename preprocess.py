
from pathlib import Path
import re

from ocr_pipeline.utils import DEFAULT_PAGE_BREAK_PATTERN

def split_ocr_text(input_file, output_folder, pattern=None):
    if pattern is None:
        pattern = DEFAULT_PAGE_BREAK_PATTERN
    
    input_path = Path(input_file)
    output_dir = Path(output_folder)
    output_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    chunks = re.split(pattern, text, flags=re.IGNORECASE)

    for i, chunk in enumerate(chunks, 1):
        out_file = output_dir / f"page_{i:04}.txt"
        out_file.write_text(chunk.strip(), encoding="utf-8")
    print(f"[preprocess] Split into {len(chunks)} chunks.")
