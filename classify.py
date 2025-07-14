from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from ocr_pipeline.utils import call_gpt

PROMPT = (
    "You are a classification assistant. Given a page of OCRed text, classify it into one of the "
    "following types: 'body', 'toc', 'bibliography', 'index'. Respond with only the label."
)

def classify_with_gpt(text):
    """ Classify a chunk of text using our GPT model."""
    response = call_gpt(text[:2000], PROMPT)
    return response.strip().lower()

def classify_chunk(chunk_path, output_dir):
    """ Classify a single OCRed text chunk into body, toc, bibliography, or index."""

    text = chunk_path.read_text(encoding="utf-8")[:2000]
    try:
        label = classify_with_gpt(text)
        if label not in ['body', 'toc', 'bibliography', 'index']:
            label = 'body'
    except Exception as e:
        print(f"Error classifying {chunk_path.name}: {e}")
        label = 'body'
    target = output_dir / label / chunk_path.name
    target.write_text(text, encoding="utf-8")

def classify_chunks(input_dir, output_dir, max_workers=8):
    """ Classify OCRed text chunks into categories like body, toc, bibliography, and index."""

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    for cat in ['body', 'toc', 'bibliography', 'index']:
        (output_dir / cat).mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.txt"))
    print(f"Classifying {len(files)} chunks from {input_dir} to {output_dir}...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(lambda f: classify_chunk(f, output_dir), files),
            total=len(files),
            desc="Classifying",
        ))
