import pathlib
import re
import subprocess


def get_duration_seconds(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def extract_keyframes(
    video_path: str,
    output_dir: str,
    scene_threshold: float = 0.4,
    fixed_interval_seconds: float = 3.0,
    min_gap_seconds: float = 2.0,
) -> list[tuple[float, str]]:
    duration = get_duration_seconds(video_path)
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Gather candidates from two independent sources.
    candidates = {0.0}  # always include the opening frame

    t = 0.0
    while t < duration:
        candidates.add(round(t, 3))
        t += fixed_interval_seconds

    scene_cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"select='gt(scene,{scene_threshold})',showinfo",
        "-vsync", "vfr", "-f", "null", "-",
    ]
    result = subprocess.run(scene_cmd, capture_output=True, text=True)
    scene_timestamps = [float(m) for m in re.findall(r"pts_time:([\d.]+)", result.stderr)]
    candidates.update(round(ts, 3) for ts in scene_timestamps)

    # 2. Deduplicate: enforce a minimum gap between any two kept timestamps.
    # Prioritize scene-change candidates over routine interval ones when close together.
    scene_set = set(round(ts, 3) for ts in scene_timestamps)
    sorted_candidates = sorted(candidates, key=lambda ts: (ts not in scene_set, ts))
    kept_timestamps = []
    for ts in sorted_candidates:
        if not any(abs(ts - kept) < min_gap_seconds for kept in kept_timestamps):
            kept_timestamps.append(ts)
    kept_timestamps.sort()

    # 3. Now actually extract an image at each kept timestamp.
    keyframes = []
    for i, ts in enumerate(kept_timestamps):
        frame_path = output_path / f"frame_{i:04d}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-frames:v", "1", str(frame_path)],
            capture_output=True,
        )
        keyframes.append((ts, str(frame_path)))

    return keyframes