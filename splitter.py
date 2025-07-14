"""Splitter is necessary to divide our Markdown into chunks that can be translated"""

from pathlib import Path
import re

def split_long_chunks(input_dir, output_dir, max_words=1200):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z“\"])')  # split on sentence boundaries

    for chunk_path in sorted(input_dir.glob("*.txt")):
        text = chunk_path.read_text(encoding="utf-8").strip()
        sentences = sentence_end.split(text)

        # Split sentences into batches by word count
        batches = []
        current_batch = []
        current_count = 0

        for sentence in sentences:
            word_count = len(sentence.split())
            if current_count + word_count > max_words and current_batch:
                batches.append(" ".join(current_batch).strip())
                current_batch = [sentence]
                current_count = word_count
            else:
                current_batch.append(sentence)
                current_count += word_count

        if current_batch:
            batches.append(" ".join(current_batch).strip())

        if len(batches) == 1:
            (output_dir / chunk_path.name).write_text(batches[0], encoding="utf-8")
        else:
            print(f"[split] {chunk_path.name} into {len(batches)} parts")
            for i, batch in enumerate(batches, 1):
                part_name = chunk_path.stem + f"_part{i:02}.txt"
                (output_dir / part_name).write_text(batch, encoding="utf-8")
