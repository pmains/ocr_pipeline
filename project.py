from pathlib import Path
from ocr_pipeline import preprocess, classify, clean, combine, export, transform
from ocr_pipeline.utils import LANG_CODE_TO_NAME

class Project:
    """
    Manages the OCR-to-EPUB/audio pipeline for a single project, supporting multiple languages.
    Handles directory structure, file paths, and all pipeline steps.
    """

    def __init__(self, name, default_lang=None):
        """
        Initialize a Project instance.

        Args:
            name (str): The project name.
            default_lang (str, optional): Default language code for the project.
        """
        self.name = name
        self.default_lang = default_lang

    def get_root(self, lang=None):
        """
        Get the root directory for the project and language.

        Args:
            lang (str, optional): Language code. Uses default_lang if not provided.

        Returns:
            Path: Path to the root directory for the given language.

        Raises:
            ValueError: If no language is specified.
        """
        lang = lang or self.default_lang
        if not lang:
            raise ValueError("Language must be specified")
        return Path("projects") / self.name / lang

    def get_path(self, key, lang=None):
        """
        Get the path for a specific file or directory in the project.

        Args:
            key (str): One of the predefined keys (e.g., 'ocr_chunks').
            lang (str, optional): Language code.

        Returns:
            Path: Path to the requested file or directory.
        """
        root = self.get_root(lang)
        paths = {
            "ocr_text": root / "ocr_text.txt",
            "ocr_chunks": root / "ocr_chunks",
            "classified_chunks": root / "classified_chunks",
            "cleaned_chunks": root / "cleaned_chunks",
            "translated_chunks": root / "translated_chunks",
            "combined_md": root / f"{self.name}_combined.md",
            "final_epub": root / f"{self.name}.epub",
            "audiobook_chunks": root / "audiobook_chunks",
            "audiobook_narration": root / f"{self.name}_narration.md",
        }
        return paths[key]

    def ensure_dirs(self, lang=None):
        """
        Ensure all necessary directories exist for a given language.

        Args:
            lang (str, optional): Language code.
        """
        for key in ["ocr_chunks", "classified_chunks", "cleaned_chunks", "translated_chunks", "audiobook_chunks"]:
            self.get_path(key, lang).mkdir(parents=True, exist_ok=True)

    def split_ocr_text(self, input_file, lang=None, page_break_pattern=None):
        """
        Split the raw OCR text into smaller chunks for processing.

        Args:
            input_file (str or Path): Path to the OCR text file.
            lang (str, optional): Language code.
            page_break_pattern (str, optional): Regex pattern for page breaks.
        """
        self.ensure_dirs(lang)
        preprocess.split_ocr_text(
            input_file=input_file,
            output_folder=self.get_path("ocr_chunks", lang),
            pattern=page_break_pattern,
        )

    def classify_chunks(self, lang=None):
        """
        Classify OCR chunks into document sections (e.g., body, bibliography).

        Args:
            lang (str, optional): Language code.
        """
        classify.classify_chunks(
            input_dir=self.get_path("ocr_chunks", lang),
            output_dir=self.get_path("classified_chunks", lang),
        )

    def clean_chunks(self, lang=None):
        """
        Clean classified chunks using prompts for different document sections.

        Args:
            lang (str, optional): Language code.
        """
        # Prompt for cleaning main body text
        body_prompt = (
            "You are a text-cleaning assistant. Clean this OCRed body text: fix line breaks, remove headers, "
            "preserve paragraph structure, and output clean Markdown. "
            "Preserve all chapter headings as '# [chapter title]' and all section titles as '## [section title]', "
            "using the original text for each heading. Place footnotes at the end of each section. "
            "If the input is empty, meaningless, or contains no usable content, output only this token: --- EMPTY ---"
        )
        clean.clean_chunks(
            input_dir=self.get_path("classified_chunks", lang) / "body",
            output_dir=self.get_path("cleaned_chunks", lang) / "body",
            prompt=body_prompt,
            desc="Cleaning body",
        )
        # Prompt for bibliography and index sections
        light_prompt = (
            "You are a light-formatting assistant. This is a bibliography or index. Preserve structure, fix OCR errors, "
            "but do not merge or reformat entries. Output as a Markdown list."
        )
        for section in ["bibliography", "index"]:
            clean.clean_chunks(
                input_dir=self.get_path("classified_chunks", lang) / section,
                output_dir=self.get_path("cleaned_chunks", lang) / section,
                prompt=light_prompt,
                desc=f"Cleaning {section}",
            )

    def combine_markdown(self, lang=None):
        """
        Combine cleaned chunks into a single Markdown file in the correct order.

        Args:
            lang (str, optional): Language code.
        """
        combine.combine_all(
            [
                self.get_path("cleaned_chunks", lang) / "toc",
                self.get_path("cleaned_chunks", lang) / "body",
                self.get_path("cleaned_chunks", lang) / "bibliography",
                self.get_path("cleaned_chunks", lang) / "index",
            ],
            self.get_path("combined_md", lang),
        )

    def generate_epub(self, lang=None):
        """
        Generate an EPUB file from the combined Markdown.

        Args:
            lang (str, optional): Language code.
        """
        export.generate_epub(
            self.get_path("combined_md", lang),
            self.get_path("final_epub", lang),
        )

        def translate(self, source_lang, target_lang):
            """
            Translate cleaned chunks (body, bibliography, index) from source_lang to target_lang.
            """
            if source_lang == target_lang:
                raise ValueError("Source and target languages must be different")

            target_language_name = LANG_CODE_TO_NAME.get(target_lang, None)
            if not target_language_name:
                raise ValueError(f"Unsupported target language: {target_lang}")

            self.ensure_dirs(target_lang)

            # Body translation (standard prompt)
            transform.translate_chunks(
                input_dir=self.get_path("cleaned_chunks", source_lang) / "body",
                output_dir=self.get_path("cleaned_chunks", target_lang) / "body",
                target_language=target_language_name,
                light=False,
            )

            # Bibliography and index translation (light prompt)
            for section in ["bibliography", "index"]:
                transform.translate_chunks(
                    input_dir=self.get_path("cleaned_chunks", source_lang) / section,
                    output_dir=self.get_path("cleaned_chunks", target_lang) / section,
                    target_language=target_language_name,
                    light=True,
                )

    def rewrite_for_audio(self, lang=None):
        """
        Rewrite translated body chunks for audio narration and combine them.

        Args:
            lang (str, optional): Language code.
        """
        transform.rewrite_for_audio_chunks(
            input_dir=self.get_path("cleaned_chunks", lang) / "body",
            output_dir=self.get_path("audiobook_chunks", lang),
        )
        combine.combine_all(
            [self.get_path("audiobook_chunks", lang)],
            self.get_path("audiobook_narration", lang),
        )

    def run(self, input_file, lang=None, page_break_pattern=None):
        """
        Run the full pipeline: split, classify, clean, combine, and export to EPUB.

        Args:
            input_file (str or Path): Path to the OCR text file.
            lang (str, optional): Language code.
            page_break_pattern (str, optional): Regex pattern for page breaks.
        """
        lang = lang or self.default_lang
        self.split_ocr_text(input_file, lang, page_break_pattern)
        self.classify_chunks(lang)
        self.clean_chunks(lang)
        self.combine_markdown(lang)
        self.generate_epub(lang)