
import subprocess
from pathlib import Path

def generate_epub(input_md, output_epub, pandoc_path="pandoc"):
    try:
        subprocess.run([pandoc_path, str(input_md), "-o", str(output_epub)], check=True)
        print(f"[export] EPUB created: {output_epub}")
    except FileNotFoundError:
        print("❌ Pandoc not found. Specify full path if needed.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Pandoc error: {e}")
