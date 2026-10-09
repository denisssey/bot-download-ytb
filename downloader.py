import asyncio
import json
import os
import uuid
from config import DOWNLOAD_DIR


async def _run(*args: str) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return proc.returncode, out, err


async def get_info(url: str) -> dict:
    code, out, err = await _run(
        "--dump-single-json",
        "--no-playlist",
        "--no-warnings",
        url,
    )
    if code != 0:
        raise RuntimeError(err.decode(errors="ignore")[-400:])
    return json.loads(out.decode())


async def download(url: str, mode: str) -> str:
    uid = uuid.uuid4().hex
    out_tpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    base = ["--no-playlist", "--no-warnings", "--concurrent-fragments", "4"]

    if mode == "audio":
        cmd = [
            *base,
            "-f", "bestaudio/best",
            "-x", "--audio-format", "mp3", "--audio-quality", "128K",
            "-o", out_tpl, url,
        ]
    else:
        height = int(mode)
        fmt = (
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}]+ba/"
            f"b[height<={height}]"
        )
        cmd = [
            *base,
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", out_tpl, url,
        ]

    code, _, err = await _run(*cmd)
    if code != 0:
        raise RuntimeError(err.decode(errors="ignore")[-400:])

    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(uid):
            return os.path.join(DOWNLOAD_DIR, f)
    raise RuntimeError("файл не найден")


def human_size(n: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"