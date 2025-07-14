"""
Orchestration for ocr_pipeline
Example usage:

    from ocr_pipeline.runner import PipelineRunner
    
    runner = PipelineRunner(project_root="projects/my_project", lang="es")
    
    runner.run(
        input_file="projects/my_project/OCR Text/example_ocr.txt",
        page_break_pattern=r"\s*### MY PAGE BREAK TOKEN ###\s*",
        api_key=api_key,
        translate=True,
        generate_epub=True,
        generate_audio=True,
        max_workers=25
    )
"""

import glob
from pathlib import Path
from ocr_pipeline import classify as ocr_classify, clean as ocr_clean, preprocess, transform, combine, export
from ocr_pipeline.utils import DEFAULT_PAGE_BREAK_PATTERN

class PipelineRunner:
    def __init__(self, project_root, lang="en", config=None):
        self.project_root = Path(project_root)
        self.lang = lang
        self.config = config or {}
        self.paths = self._build_paths()

    def _build_paths(self):
        return {
            "ocr_text": self.project_root / "ocr_text",
            "ocr_chunks": self.project_root / "ocr_chunks",
            "classified_chunks": self.project_root / "classified_chunks",
            "cleaned_chunks": self.project_root / "cleaned_chunks",
            "translated_chunks": self.project_root / "translated_chunks" / self.lang,
            "epub_output": self.project_root / "epub" / self.lang,
            "audiobook_chunks": self.project_root / "audiobook_chunks" / self.lang,
            "audiobook_narration": self.project_root / f"narration_{self.lang}.md"
        }

    def run(
        self,
        input_file,
        page_break_pattern=r"\s*--- PAGE BREAK ---\s*",
        *,
        classify=True,
        clean=True,
        translate=True,
        generate_epub=True,
        generate_audio=True,
        max_workers=25,
    ): 
        print("🔍 Splitting OCR text...")
        preprocess.split_ocr_text(
            input_file=input_file,
            output_folder=self.paths["ocr_chunks"],
            pattern=page_break_pattern,
        )

        if classify:
            print("📂 Classifying chunks...")
            ocr_classify.classify_chunks(
                input_dir=self.paths["ocr_chunks"],
                output_dir=self.paths["classified_chunks"],
            )

        if clean:
            print("🧼 Cleaning body chunks...")
            body_prompt = (
                "You are a text-cleaning assistant. Clean this OCRed body text: fix line breaks, remove headers, "
                "preserve paragraph structure, and output clean Markdown. Place footnotes at the end of each section."
            )
            ocr_clean.clean_chunks(
                input_dir=self.paths["classified_chunks"] / "body",
                output_dir=self.paths["cleaned_chunks"] / "body",
                prompt=body_prompt,
                max_workers=max_workers
            )

        if translate:
            print(f"🌐 Translating body chunks to {self.lang}...")
            transform.translate_chunks(
                input_dir=self.paths["cleaned_chunks"] / "body",
                output_dir=self.paths["translated_chunks"],
                target_language=self._language_name(),
                max_workers=max_workers
            )

        if generate_epub:
            print("📘 Generating EPUB...")
            combine.combine_all(
                input_dirs=[self.paths["translated_chunks"]],
                output_file=self.paths["epub_output"] / f"{self.project_root.name}_{self.lang}.md",
            )
            export.generate_epub(
                input_md=self.paths["epub_output"] / f"{self.project_root.name}_{self.lang}.md",
                output_epub=self.paths["epub_output"] / f"{self.project_root.name}_{self.lang}.epub",
            )

        if generate_audio:
            print("🎧 Rewriting for audiobook...")
            transform.rewrite_for_audio_chunks(
                input_dir=self.paths["translated_chunks"],
                output_dir=self.paths["audiobook_chunks"],
                max_workers=max_workers
            )
            print("📚 Combining audiobook narration...")
            combine.combine_all(
                input_dirs=[self.paths["audiobook_chunks"]],
                output_file=self.paths["audiobook_narration"]
            )


    @staticmethod
    def run_batch(
        root_dir,
        input_folder=None,
        input_files=None,
        lang="en",
        config=None,
        page_break_pattern=DEFAULT_PAGE_BREAK_PATTERN,
        *,
        classify=True,
        clean=True,
        translate=True,
        generate_epub=True,
        generate_audio=True,
        max_workers=25,
        force=False
    ):
        assert input_folder or input_files, "Must provide either input_folder or input_files"
        root_dir = Path(root_dir)
        config = config or {}
    
        if input_folder:
            input_files = sorted(glob.glob(str(Path(input_folder) / "*.txt")))
    
        for file_path in input_files:
            input_path = Path(file_path)
            project_name = input_path.stem.replace("_ocr", "")
            project_dir = root_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
    
            runner = PipelineRunner(
                project_root=project_dir,
                lang=lang,
                config=config,
            )
    
            # Define what counts as "processed"
            narration_file = runner.paths["audiobook_narration"]
            if narration_file.exists() and not force:
                print(f"⏭️  Skipping {project_name} (already processed)")
                continue
    
            print(f"\n🚀 Starting pipeline for {project_name}...")
            runner.run(
                input_file=input_path,
                page_break_pattern=page_break_pattern,
                classify=classify,
                clean=clean,
                translate=translate,
                generate_epub=generate_epub,
                generate_audio=generate_audio,
                max_workers=max_workers,
            )
    
    def _language_name(self):
        # Convert "en" → "English", "es" → "Spanish", etc.
        return {
            "en": "English",
            "es": "Spanish",
            "ca": "Catalan",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "la": "Latin",
        }.get(self.lang, self.lang)
