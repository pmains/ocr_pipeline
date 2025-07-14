import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
import glob
from tqdm import tqdm


from ocr_pipeline.utils import call_gpt, get_api_key, get_poppler_path, get_tesseract_path

API_KEY = get_api_key()
pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()


def translate_chunk(chunk_path, out_path, target_language, light=False):
    """Translate text chunks to the target language, with optional light prompt."""
    if out_path.exists():
        return chunk_path.name, "skip", None

    try:
        raw_text = chunk_path.read_text(encoding="utf-8")
        if light:
            prompt = (
                f"Translate the following bibliography or index into {target_language}. "
                "Preserve structure, fix OCR errors, do not merge or reformat entries. Output as a Markdown list."
            )
        else:
            prompt = f"Translate the following text into {target_language}. Preserve Markdown formatting."
        translated = call_gpt(raw_text, prompt)
        out_path.write_text(translated, encoding="utf-8")
        return chunk_path.name, "translated", None
    except Exception as e:
        return chunk_path.name, "error", str(e)

def translate_chunks(input_dir, output_dir, target_language="English", max_workers=25, light=False):
    """Translate text chunks in parallel, using standard or light prompt."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_paths = sorted(input_dir.glob("*.txt"))
    tasks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for chunk_path in chunk_paths:
            out_path = output_dir / chunk_path.name
            task = executor.submit(translate_chunk, chunk_path, out_path, target_language, light)
            tasks.append(task)

        for future in tqdm(as_completed(tasks), total=len(tasks), desc="Translating chunks"):
            name, status, error = future.result()
            if status == "error":
                print(f"[error] {name}: {error}")


def rewrite_chunk_for_audio(chunk_path, out_path):
    """Rewrite a single audio chunk in a sense that lends itself to audiobook narration"""

    if out_path.exists():
        return chunk_path.name, "skip", None

    try:
        raw_text = chunk_path.read_text(encoding="utf-8")
        prompt = (
            "You are preparing this text for audiobook narration. "
            "Remove all footnotes, citation markers, bibliographic references, and lists of tables or contents. "
            "Convert it into clean, natural, spoken prose."
        )
        cleaned = call_gpt(raw_text, prompt)
        out_path.write_text(cleaned, encoding="utf-8")
        return chunk_path.name, "rewritten", None
    except Exception as e:
        return chunk_path.name, "error", str(e)

def rewrite_for_audio_chunks(input_dir, output_dir, max_workers=25):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunk_paths = sorted(input_dir.glob("*.txt"))
    tasks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for chunk_path in chunk_paths:
            out_path = output_dir / chunk_path.name
            task = executor.submit(rewrite_chunk_for_audio, chunk_path, out_path)
            tasks.append(task)

        for future in tqdm(as_completed(tasks), total=len(tasks), desc="Rewriting for audio"):
            name, status, error = future.result()
            if status == "error":
                print(f"[error] {name}: {error}")


def ocr_chunks(input_dir, output_dir, lang="eng"):
    """Run OCR on all images in input_dir and save as text files in output_dir."""

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(input_dir.glob("*.png"))  # or "*.jpg", adjust as needed
    for img_path in tqdm(image_paths, desc="Running OCR"):
        text = pytesseract.image_to_string(Image.open(img_path), lang=lang)
        out_path = output_dir / (img_path.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")


def convert_with_progress(pdf_path, poppler_path=None, dpi=300, batch_size=10):
    # Get page count
    print("Starting ...")
    info = pdfinfo_from_path(pdf_path, poppler_path=poppler_path)
    total_pages = info["Pages"]
    print(f"✅ Loaded {total_pages} pages.")

    all_images = []

    # Process in batches with progress bar
    with tqdm(total=total_pages, desc="Converting PDF pages") as pbar:
        for i in range(0, total_pages, batch_size):
            first = i + 1
            last = min(i + batch_size, total_pages)
            batch = convert_from_path(
                pdf_path,
                dpi=dpi,
                first_page=first,
                last_page=last,
                poppler_path=poppler_path
            )
            all_images.extend(batch)
            pbar.update(len(batch))

    return all_images


def ocr_images_with_progress(images, lang="eng"):
    """Run OCR on a list of PIL images with a progress bar. Returns list of texts."""
    texts = []
    for image in tqdm(images, desc="Running OCR"):
        text = pytesseract.image_to_string(image, lang=lang)
        texts.append(text)
    return texts


def batch_ocr_pdfs(pdf_input_folder, txt_output_folder, lang='lat+cat'):
    """Batch process PDFs in a folder, converting them to text files using OCR."""

    os.makedirs(txt_output_folder, exist_ok=True)
    pdf_files = glob.glob(os.path.join(pdf_input_folder, "*.pdf"))

    unprocessed_pdfs = []
    for pdf_path in pdf_files:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        txt_path = os.path.join(txt_output_folder, f"{base_name}_ocr.txt")
        if not os.path.exists(txt_path):
            unprocessed_pdfs.append(pdf_path)

    print(f"📂 Found {len(unprocessed_pdfs)} unprocessed PDFs.")

    for pdf_path in unprocessed_pdfs:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_txt = os.path.join(txt_output_folder, f"{base_name}_ocr.txt")

        print(f"\n🔍 Processing {base_name}")
        images = convert_with_progress(pdf_path, poppler_path=str(get_poppler_path()))
        texts = ocr_images_with_progress(images, lang=lang)

        with open(output_txt, "w", encoding="utf-8") as f:
            f.write("\n\n--- PAGE BREAK ---\n\n".join(texts))

        print(f"✅ Saved to {output_txt}")
