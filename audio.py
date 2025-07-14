"""
Audio generation using AWS Polly long-form narration.

Requires:
    - boto3 (`pip install boto3`)
    - AWS credentials configured
    - An S3 bucket for Polly output

Example usage:
    from ocr_pipeline import audio
    audio.generate_audio_from_chunks(
        input_dir="projects/my_project/audiobook_chunks/en",
        output_dir="projects/my_project/audio/en",
        s3_bucket="my-polly-output-bucket",
        voice_id="Joanna",
        lang="en"
    )
"""

import time
from pathlib import Path
import boto3

def synthesize_speech_aws_polly(text, output_path, s3_bucket, voice_id="Ruth", lang="en"):
    """
    Synthesize speech using AWS Polly long-form narration.

    Args:
        text (str): Text to synthesize.
        output_path (Path): Local path to save the audio file.
        s3_bucket (str): S3 bucket for Polly output.
        voice_id (str): Polly voice ID.
        lang (str): Language code.
    """
    polly = boto3.client("polly")
    s3_key = f"polly_output/{output_path.name}"

    # Start long-form synthesis task
    response = polly.start_speech_synthesis_task(
        OutputS3BucketName=s3_bucket,
        OutputS3KeyPrefix="polly_output/",
        Text=text,
        VoiceId=voice_id,
        LanguageCode=lang,
        OutputFormat="mp3"
    )
    task_id = response["SynthesisTask"]["TaskId"]

    # Poll for task completion
    while True:
        status = polly.get_speech_synthesis_task(TaskId=task_id)
        task_status = status["SynthesisTask"]["TaskStatus"]
        if task_status in ["completed", "failed"]:
            break
        time.sleep(5)

    if task_status == "completed":
        s3_uri = status["SynthesisTask"]["OutputUri"]
        # Download from S3
        s3 = boto3.client("s3")
        s3.download_file(s3_bucket, s3_key + ".mp3", str(output_path))
    else:
        raise RuntimeError(f"Polly synthesis failed: {status}")

def generate_audio_from_chunks(input_dir, output_dir, s3_bucket, voice_id="Joanna", lang="en"):
    """
    Generate audio files from text chunks using AWS Polly.

    Args:
        input_dir (str or Path): Directory with text/Markdown files.
        output_dir (str or Path): Directory to save audio files.
        s3_bucket (str): S3 bucket for Polly output.
        voice_id (str): Polly voice ID.
        lang (str): Language code.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for chunk_file in sorted(input_dir.glob("*.txt")):
        with open(chunk_file, "r", encoding="utf-8") as f:
            text = f.read()
        audio_file = output_dir / (chunk_file.stem + ".mp3")
        print(f"🔊 Generating audio for {chunk_file.name} -> {audio_file.name}")
        synthesize_speech_aws_polly(
            text, audio_file, s3_bucket=s3_bucket, voice_id=voice_id, lang=lang
        )