import pytesseract
from PIL import Image
from pathlib import Path
from tqdm import tqdm
from ocr_pipeline.utils import get_tesseract_path

pytesseract.pytesseract.tesseract_cmd = str(get_tesseract_path())

def ocr_images_with_progress(images, lang="eng", psm=6):
    """Run OCR on a list of PIL images with a progress bar. Returns list of texts."""
    texts = []
    config = f'--psm {psm}'
    for image in tqdm(images, desc="OCR'ing images"):
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        texts.append(text)
    return texts

def ocr_chunks(input_dir, output_dir, lang="eng", psm=6):
    """Run OCR on all images in input_dir and save as text files in output_dir."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for img_path in tqdm(sorted(input_dir.glob("*.png")), desc="Running OCR"):
        text = pytesseract.image_to_string(Image.open(img_path), lang=lang, config=f'--psm {psm}')
        out_path = output_dir / (img_path.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")