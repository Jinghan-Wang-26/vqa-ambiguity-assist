import os
import re
import shutil
import subprocess
import tempfile
import uuid
from difflib import SequenceMatcher
from typing import Any

from .pipeline import _chat_with_image_text, build_inventory
from .schemas import Inventory
from .utils import image_file_to_data_url

_video_sessions: dict[str, dict] = {}


def _extract_time_seconds(text: str) -> float | None:
    s = text.lower()
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds)\b", s)
    if m:
        return float(m.group(1))
    m = re.search(r"\b(\d+):(\d{2})\b", s)  # mm:ss
    if m:
        return float(int(m.group(1)) * 60 + int(m.group(2)))
    return None


def _best_match_name(
    query: str, candidates: list[str]
) -> tuple[str | None, float]:
    """Return best candidate and similarity score."""
    q = query.lower().strip()
    best = None
    best_score = 0.0
    for c in candidates:
        s = SequenceMatcher(None, q, c.lower()).ratio()
        if s > best_score:
            best, best_score = c, s
    return best, best_score


def _infer_target_object(
    question: str, all_object_names: list[str]
) -> str | None:
    """Heuristic: pick the object name that appears in question (substring),
    else fuzzy-match against all_object_names.
    """
    q = question.lower()
    # direct substring match first
    for name in sorted(set(all_object_names), key=len, reverse=True):
        if name and name.lower() in q:
            return name

    # fuzzy match on keywords near the end (often "keyboard", "mug", etc.)
    # take last ~6 words as focus phrase
    tail = " ".join(question.split()[-6:])
    cand, score = _best_match_name(tail, list(set(all_object_names)))
    if cand and score >= 0.62:  # tuneable
        return cand

    return None


def _chat_with_image_text_local(
    system: str, user: str, image_data_url: str, temperature: float = 0.2
) -> str:
    # reuse pipeline client/MODEL (your repo already has them since image works)
    from .pipeline import MODEL, client

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def _focused_answer(
    image_data_url: str, question: str, target: str, t: float
) -> str:
    system = (
        "You are an accessibility assistant for video VQA. "
        "Answer ONLY using what is visible in the provided frame. "
        "If asked for location, use the 3x3 grid: top-left, top, top-right, left, center, right, "
        "bottom-left, bottom, bottom-right. If uncertain, say 'unknown'."
    )
    user = (
        f"Video time (approx): {t:.1f}s\n"
        f"Question: {question}\n"
        f"Target object: {target}\n\n"
        "Provide a focused answer about the target object at this moment."
    )
    return _chat_with_image_text_local(
        system, user, image_data_url, temperature=0.2
    )


def _run(cmd: list[str]) -> None:
    p = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{' '.join(cmd)}\n\nstderr:\n{p.stderr[:1000]}"
        )


def _require_ffmpeg() -> None:
    """Fail fast with a helpful message instead of a 500 traceback."""
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg/ffprobe not found on PATH. Install ffmpeg to enable video support.\n"
            "Ubuntu/WSL: sudo apt-get update && sudo apt-get install -y ffmpeg\n"
            "macOS: brew install ffmpeg\n"
            "Windows: winget install Gyan.FFmpeg (then add to PATH)"
        )


def extract_frames(
    video_path: str, out_dir: str, seconds: list[float]
) -> list[str]:
    """Extract one frame at each timestamp in `seconds`.

    Robustness:
    - Try fast seek (-ss before -i)
    - If output missing, retry accurate seek (-ss after -i)
    - Verify file exists; if still missing, raise a helpful error
    """
    paths: list[str] = []
    for i, t in enumerate(seconds):
        out = os.path.join(out_dir, f"frame_{i:02d}_{t:.1f}.jpg")

        # 1) Fast seek
        p1 = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(t),
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-q:v",
                "3",
                out,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if not os.path.exists(out) or os.path.getsize(out) == 0:
            # 2) Retry: accurate seek (place -ss after -i)
            p2 = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video_path,
                    "-ss",
                    str(t),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    out,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if not os.path.exists(out) or os.path.getsize(out) == 0:
                err = (p2.stderr or p1.stderr or "")[:1500]
                raise RuntimeError(
                    f"Failed to extract frame at t={t:.2f}s.\n"
                    f"Video: {video_path}\n"
                    f"Output expected: {out}\n\n"
                    f"ffmpeg stderr:\n{err}"
                )

        paths.append(out)

    return paths


def probe_duration(video_path: str) -> float:
    """Ffprobe duration in seconds."""
    _require_ffmpeg()
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        return float(p.stdout.strip())
    except Exception:
        return 0.0


def choose_timestamps(duration: float) -> list[float]:
    """Pick up to 6 timestamps, evenly spaced, but never at/after the end of video."""
    if duration <= 0:
        return [0.0, 0.5, 1.0]

    # Keep a safety margin to avoid seeking beyond the last decodable frame
    safe_end = max(0.0, duration - 0.2)

    k = 6
    if safe_end < 1.5:
        # very short clips
        ts = [0.0, min(0.3, safe_end), min(0.6, safe_end)]
        return sorted(list({round(t, 2) for t in ts}))

    step = safe_end / max(1, (k - 1))
    ts = [i * step for i in range(k)]
    ts = [min(t, safe_end) for t in ts]
    # de-duplicate after rounding
    return sorted(list({round(t, 2) for t in ts}))


def video_onepass(
    video_bytes: bytes,
    question: str,
    cache_key: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    _require_ffmpeg()

    with tempfile.TemporaryDirectory() as td:
        # Keep original suffix when possible to help ffmpeg demuxers.
        suffix = ".mp4"
        if filename and "." in filename:
            ext = os.path.splitext(filename)[1].lower()
            if 1 <= len(ext) <= 10:
                suffix = ext

        video_path = os.path.join(td, f"clip{suffix}")
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        dur = probe_duration(video_path)
        dur = max(0.0, dur)
        ts = choose_timestamps(dur)
        frame_paths = extract_frames(video_path, td, ts)

        # Per-frame inventories
        frames = []
        for t, fp in zip(ts, frame_paths):
            data_url = image_file_to_data_url(fp)
            inv = build_inventory(
                data_url, question, cache_key=(cache_key or "") + f":t={t}"
            )
            frames.append({"t": t, "data_url": data_url, "inventory": inv})

        # Simple temporal merge: count object names over time
        name_to_times: dict[str, list[float]] = {}
        for fr in frames:
            inv: Inventory = fr["inventory"]
            for obj in inv.objects:
                if obj.name:
                    name_to_times.setdefault(obj.name, []).append(fr["t"])

        # Timeline summary
        # collect all object names across frames
        all_names: list[str] = []
        for fr in frames:
            inv: Inventory = fr["inventory"]
            for obj in inv.objects:
                if obj.name:
                    all_names.append(obj.name)

        q_time = _extract_time_seconds(question)
        q_target = _infer_target_object(question, all_names)

        # build compact timeline (top-k)
        timeline_lines = []
        for name, times in sorted(
            name_to_times.items(), key=lambda x: -len(x[1])
        )[:8]:
            tmin, tmax = min(times), max(times)
            timeline_lines.append(
                f"- {name}: ~{tmin:.1f}s–{tmax:.1f}s ({len(times)} frames)"
            )
        more = max(0, len(name_to_times) - 8)

        timeline_summary = (
            "Objects over time (top items):\n"
            + ("\n".join(timeline_lines) if timeline_lines else "- (none)")
            + (f"\n(+{more} more)" if more else "")
        )

        # If question already pins down time + object, answer directly
        if q_time is not None and q_target is not None:
            nearest = min(frames, key=lambda fr: abs(fr["t"] - q_time))
            focused = _focused_answer(
                nearest["data_url"], question, q_target, nearest["t"]
            )

            return {
                "duration": dur,
                "timestamps": ts,
                "mode_used": "focused_onepass",
                "question_time": q_time,
                "target_object": q_target,
                "chosen_time": nearest["t"],
                "answer": focused,
                "timeline_summary": timeline_summary,
            }

        # Otherwise, keep ambiguity-aware summary + ask for clarification
        clarification = (
            "Your question may refer to different moments or objects in the video. "
            "Please specify a time (e.g., “at ~5s”) and the object (e.g., “keyboard”)."
        )

        answer = timeline_summary + "\n\n" + clarification

        return {
            "duration": dur,
            "timestamps": ts,
            "mode_used": "timeline_only",
            "timeline_summary": answer,
            "objects_over_time": name_to_times,
        }


def _focused_answer(
    image_data_url: str,
    question: str,
    target: str,
    cache_key: str | None = None,
) -> str:
    """Ask model to answer question focusing ONLY on the target object."""
    system = (
        "You are an accessibility assistant for video VQA. "
        "Answer concisely and focus on the specified target object only. "
        "If the question is not answerable from the image, say so."
    )
    user = (
        f"Question: {question}\n"
        f"Target object: {target}\n\n"
        "Answer the question focusing ONLY on the target object."
    )

    # 如果你 pipeline.py 有类似的“chat with image text”的函数就用它；
    # 否则你可以在 pipeline.py 里加一个（我下面给你）
    return _chat_with_image_text(system, user, image_data_url, temperature=0.2)


def video_iter_start(
    video_bytes: bytes,
    question: str,
    cache_key: str | None = None,
    filename: str | None = None,
) -> dict:
    _require_ffmpeg()

    with tempfile.TemporaryDirectory() as td:
        # keep suffix
        suffix = ".mp4"
        if filename and "." in filename:
            ext = os.path.splitext(filename)[1].lower()
            if 1 <= len(ext) <= 10:
                suffix = ext

        video_path = os.path.join(td, f"clip{suffix}")
        with open(video_path, "wb") as f:
            f.write(video_bytes)

        dur = probe_duration(video_path)
        ts = choose_timestamps(dur)
        frame_paths = extract_frames(video_path, td, ts)

        # store frame data_urls + inventories in memory (simple + works)
        frames = []
        for t, fp in zip(ts, frame_paths):
            data_url = image_file_to_data_url(fp)
            inv = build_inventory(
                data_url, question, cache_key=(cache_key or "") + f":t={t}"
            )
            frames.append({"t": t, "data_url": data_url, "inventory": inv})

    session_id = str(uuid.uuid4())
    _video_sessions[session_id] = {
        "question": question,
        "duration": dur,
        "timestamps": ts,
        "frames": frames,
        "stage": "time",  # time -> object -> done
        "chosen_t": None,
    }

    # 让用户先选时间段（时间点选项）
    time_opts = [f"~{t:.1f}s" for t in ts]
    inv_brief = "Video sampled frames: " + ", ".join(time_opts)
    clarification = (
        "Which moment in the video do you mean? Choose a timestamp (approx.)."
    )

    return {
        "session_id": session_id,
        "inventory_brief": inv_brief,
        "clarification_question": clarification,
        "options": time_opts,
    }


def video_iter_choose(session_id: str, chosen: str) -> dict:
    st = _video_sessions.get(session_id)
    if not st:
        return {
            "focused_answer": "Session expired or not found. Please start again.",
            "followup_suggestions": [],
            "updated_state": {"error": "session_not_found"},
        }

    stage = st["stage"]
    question = st["question"]
    frames = st["frames"]

    # stage 1: choose time
    if stage == "time":
        # chosen is like "~2.4s"
        try:
            tval = float(chosen.replace("~", "").replace("s", "").strip())
        except Exception:
            tval = None

        # pick nearest
        if tval is None:
            return {
                "focused_answer": "Please choose a timestamp option like “~2.4s”.",
                "followup_suggestions": [],
                "updated_state": {"stage": "time"},
            }

        nearest = min(frames, key=lambda fr: abs(fr["t"] - tval))
        st["chosen_t"] = nearest["t"]
        st["stage"] = "object"

        inv: Inventory = nearest["inventory"]
        obj_opts = []
        for o in inv.objects:
            # 更像 UI 友好：显示 name + location
            loc = getattr(o, "location", "unknown")
            if o.name:
                obj_opts.append(f"{o.name} ({loc})")

        obj_opts = obj_opts[:18]  # 防止太多
        clarification = f"At ~{nearest['t']:.1f}s, which object do you mean?"

        return {
            "focused_answer": f"Selected time: ~{nearest['t']:.1f}s.\n\n{clarification}",
            "followup_suggestions": [],
            "updated_state": {"stage": "object", "t": nearest["t"]},
            "options": obj_opts,
        }

    # stage 2: choose object
    if stage == "object":
        t = st.get("chosen_t")
        fr = min(frames, key=lambda fr: abs(fr["t"] - float(t)))
        data_url = fr["data_url"]

        # chosen is like "mug (center)" -> extract name
        obj_name = chosen.split("(", maxsplit=1)[0].strip()

        ans = _focused_answer(
            data_url,
            question=question,
            target=obj_name,
            cache_key=(session_id + f":t={fr['t']}:{obj_name}"),
        )

        st["stage"] = "done"

        return {
            "focused_answer": ans,
            "followup_suggestions": [
                "Choose another time to compare answers",
                "Ask a follow-up about attributes (color, count, location)",
            ],
            "updated_state": {
                "stage": "done",
                "t": fr["t"],
                "object": obj_name,
            },
        }

    return {
        "focused_answer": "Session already completed. Start again to iterate.",
        "followup_suggestions": [],
        "updated_state": {"stage": "done"},
    }
