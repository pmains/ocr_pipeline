from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from ocr_pipeline.utils import call_gpt

def clean_chunk(chunk_path, out_path, prompt, overwrite):
    if out_path.exists() and not overwrite:
        return chunk_path.name, "skip", None

    try:
        raw_text = chunk_path.read_text(encoding="utf-8")
        cleaned = call_gpt(raw_text, prompt)
        out_path.write_text(cleaned, encoding="utf-8")
        return chunk_path.name, "cleaned", None
    except Exception as e:
        return chunk_path.name, "error", str(e)

def clean_chunks(input_dir, output_dir, prompt, desc="Cleaning Chunks", overwrite=False, max_workers=25):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_paths = sorted(input_dir.glob("*.txt"))

    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for chunk_path in chunk_paths:
            out_path = output_dir / chunk_path.name
            task = executor.submit(clean_chunk, chunk_path, out_path, prompt, overwrite)
            tasks.append(task)

        for future in tqdm(as_completed(tasks), total=len(tasks), desc=desc):
            name, status, error = future.result()
            if status == "error":
                print(f"[error] {name}: {error}")
