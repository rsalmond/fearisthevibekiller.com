import io
from pathlib import Path
from typing import List

import ffmpeg
import imagehash
from PIL import Image


def get_frame_at_timestamp(video_path: str, timestamp: float) -> Image.Image:
    """Return a single frame image at a given timestamp."""
    out, _ = (
        ffmpeg.input(video_path, ss=timestamp)
        .output("pipe:", vframes=1, format="image2", vcodec="mjpeg")
        .run(capture_stdout=True, capture_stderr=True)
    )
    return Image.open(io.BytesIO(out))


def get_video_duration(video_path: str) -> float:
    """Return the duration of a video in seconds."""
    probe = ffmpeg.probe(video_path)
    return float(probe["format"]["duration"])


def is_static_video(
    video_path: str,
    start_time: float = 1.0,
    late_offset: float = 2.0,
    hash_threshold: int = 5,
) -> bool:
    """Detect whether a video is mostly static based on frame hashes."""
    duration = get_video_duration(video_path)
    middle_time = duration / 2
    end_time = max(0, duration - late_offset)

    frames = [
        get_frame_at_timestamp(video_path, start_time),
        get_frame_at_timestamp(video_path, middle_time),
        get_frame_at_timestamp(video_path, end_time),
    ]

    hashes = [imagehash.average_hash(img) for img in frames]
    distances = [
        hashes[0] - hashes[1],
        hashes[0] - hashes[2],
        hashes[1] - hashes[2],
    ]

    return all(distance < hash_threshold for distance in distances)


def extract_static_frame(video_path: Path, output_dir: Path) -> List[Path]:
    """Extract a representative frame if the video appears static."""
    if not video_path.exists() or not video_path.is_file():
        return []

    if not is_static_video(video_path.as_posix()):
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{video_path.stem}_frame.jpg"
    if output_file.exists():
        return [output_file]

    frame = get_frame_at_timestamp(video_path.as_posix(), 1)
    frame.save(output_file.as_posix())
    return [output_file]
