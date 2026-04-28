"""ffmpeg orqali media qayta ishlash."""

import os
import asyncio
import logging
import subprocess
from typing import Optional

from config import TEMP_DIR

logger = logging.getLogger(__name__)


async def run_ffmpeg(args: list[str], timeout: int = 600) -> bool:
    """ffmpeg buyrug'ini asinxron bajarish."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
        if process.returncode != 0:
            err = stderr.decode(errors="ignore")[:500]
            logger.error(f"ffmpeg xatosi: {err}")
            raise RuntimeError(f"ffmpeg xatosi: {err}")
        return True
    except asyncio.TimeoutError:
        process.kill()
        raise RuntimeError("ffmpeg jarayoni vaqti tugadi (timeout)!")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg topilmadi! Iltimos ffmpeg o'rnating.")


async def get_media_duration(filepath: str) -> float:
    """Media faylning davomiyligini soniyada olish."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            filepath,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return float(stdout.decode().strip())
    except Exception:
        return 0.0


async def get_video_resolution(filepath: str) -> tuple[int, int]:
    """Video o'lchamlarini olish (width, height)."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0", filepath,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        parts = stdout.decode().strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 0, 0


async def get_audio_info(filepath: str) -> dict:
    """Audio fayl haqida ma'lumot."""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration,bit_rate,format_name:stream=codec_name,channels,sample_rate",
            "-of", "json", filepath,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        import json
        data = json.loads(stdout.decode())
        fmt = data.get("format", {})
        streams = data.get("streams", [{}])
        stream = streams[0] if streams else {}
        return {
            "duration": float(fmt.get("duration", 0)),
            "bit_rate": int(fmt.get("bit_rate", 0)),
            "format_name": fmt.get("format_name", ""),
            "codec": stream.get("codec_name", ""),
            "channels": stream.get("channels", 2),
            "sample_rate": stream.get("sample_rate", "44100"),
        }
    except Exception as e:
        logger.error(f"Audio info xatosi: {e}")
        return {}


# ===== VIDEO TOOLS =====

async def crop_video(input_path: str, output_path: str,
                     start_time: str, end_time: str) -> str:
    """Videoni kesish."""
    await run_ffmpeg([
        "-i", input_path,
        "-ss", start_time, "-to", end_time,
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast", output_path,
    ])
    return output_path


async def extract_audio_from_video(input_path: str, output_path: str,
                                   codec: str = "libmp3lame",
                                   ext: str = "mp3") -> str:
    """Videodan audio ajratish."""
    args = ["-i", input_path, "-vn"]
    if codec == "pcm_s16le":
        args += ["-acodec", codec]
    else:
        args += ["-acodec", codec, "-q:a", "0"]
    args.append(output_path)
    await run_ffmpeg(args)
    return output_path


async def change_video_speed(input_path: str, output_path: str,
                             speed: float) -> str:
    """Video tezligini o'zgartirish."""
    # Video filter
    vf = f"setpts={1/speed}*PTS"
    # Audio filter
    af = f"atempo={speed}" if 0.5 <= speed <= 2.0 else None
    # atempo faqat 0.5-2.0 oraliqda ishlaydi, boshqasida chain kerak
    if speed < 0.5 or speed > 2.0:
        # Chain atempo filters
        af_parts = []
        remaining = speed
        while remaining > 2.0:
            af_parts.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            af_parts.append("atempo=0.5")
            remaining /= 0.5
        af_parts.append(f"atempo={remaining:.4f}")
        af = ",".join(af_parts)

    args = ["-i", input_path, "-vf", vf]
    if af:
        args += ["-af", af]
    args += ["-c:v", "libx264", "-preset", "fast", output_path]
    await run_ffmpeg(args)
    return output_path


async def mute_video(input_path: str, output_path: str) -> str:
    """Videoni ovozsiz qilish."""
    await run_ffmpeg([
        "-i", input_path, "-c:v", "copy", "-an", output_path,
    ])
    return output_path


async def compress_video(input_path: str, output_path: str, crf: int = 23) -> str:
    """Video hajmini siqish."""
    await run_ffmpeg([
        "-i", input_path,
        "-c:v", "libx264", "-crf", str(crf),
        "-preset", "medium", "-c:a", "aac", "-b:a", "128k",
        output_path,
    ])
    return output_path


async def change_resolution(input_path: str, output_path: str,
                            height: int) -> str:
    """Video sifatini o'zgartirish."""
    await run_ffmpeg([
        "-i", input_path,
        "-vf", f"scale=-2:{height}",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy", output_path,
    ])
    return output_path


async def convert_video_format(input_path: str, output_path: str,
                               target_format: str) -> str:
    """Video formatini o'zgartirish."""
    if target_format == "gif":
        await run_ffmpeg([
            "-i", input_path,
            "-vf", "fps=15,scale=480:-1:flags=lanczos",
            "-loop", "0", output_path,
        ])
    else:
        await run_ffmpeg([
            "-i", input_path, "-c:v", "copy", "-c:a", "copy", output_path,
        ])
    return output_path


async def change_aspect_ratio(input_path: str, output_path: str,
                              ratio: str, method: str = "pad") -> str:
    """Tomonlar nisbatini o'zgartirish."""
    ratio_map = {
        "16:9": (16, 9), "9:16": (9, 16), "4:3": (4, 3),
        "1:1": (1, 1), "21:9": (21, 9),
    }
    rw, rh = ratio_map.get(ratio, (16, 9))
    w, h = await get_video_resolution(input_path)
    if w == 0 or h == 0:
        raise RuntimeError("Video o'lchamlari aniqlanmadi!")

    target_w = w
    target_h = int(w * rh / rw)
    if target_h > h:
        target_h = h
        target_w = int(h * rw / rh)
    # Juft sonlarga yaxlitlash
    target_w = target_w - (target_w % 2)
    target_h = target_h - (target_h % 2)

    if method == "pad":
        vf = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
    else:
        vf = f"crop={target_w}:{target_h}"

    await run_ffmpeg([
        "-i", input_path, "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "copy", output_path,
    ])
    return output_path


async def extract_subtitles(input_path: str, output_path: str) -> Optional[str]:
    """Videodan subtitrlarni olish."""
    # Avval subtitrlar bor-yo'qligini tekshirish
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "s",
            "-show_entries", "stream=codec_name,codec_type",
            "-of", "json", input_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        import json
        data = json.loads(stdout.decode())
        streams = data.get("streams", [])
        if not streams:
            return None  # Subtitr topilmadi

        await run_ffmpeg(["-i", input_path, "-map", "0:s:0", output_path])
        return output_path
    except Exception as e:
        logger.error(f"Subtitr ajratish xatosi: {e}")
        return None


async def add_subtitles(video_path: str, subtitle_path: str,
                        output_path: str) -> str:
    """Videoga soft subtitr qo'shish."""
    await run_ffmpeg([
        "-i", video_path, "-i", subtitle_path,
        "-c:v", "copy", "-c:a", "copy",
        "-c:s", "mov_text",
        "-map", "0:v", "-map", "0:a", "-map", "1:0",
        output_path,
    ])
    return output_path


# ===== AUDIO TOOLS =====

async def cut_audio(input_path: str, output_path: str,
                    start_time: str, end_time: str) -> str:
    """Audio kesish."""
    await run_ffmpeg([
        "-i", input_path, "-ss", start_time, "-to", end_time,
        "-c", "copy", output_path,
    ])
    return output_path


async def change_audio_speed(input_path: str, output_path: str,
                             speed: float) -> str:
    """Audio tezligini o'zgartirish."""
    af_parts = []
    remaining = speed
    while remaining > 2.0:
        af_parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        af_parts.append("atempo=0.5")
        remaining /= 0.5
    af_parts.append(f"atempo={remaining:.4f}")
    af = ",".join(af_parts)

    await run_ffmpeg(["-i", input_path, "-af", af, output_path])
    return output_path


async def change_audio_volume(input_path: str, output_path: str,
                              mode: str) -> str:
    """Ovoz balandligini o'zgartirish."""
    if mode == "2x_up":
        af = "volume=2.0"
    elif mode == "2x_down":
        af = "volume=0.5"
    else:  # normalize
        af = "loudnorm=I=-16:TP=-1.5:LRA=11"
    await run_ffmpeg(["-i", input_path, "-af", af, output_path])
    return output_path


async def compress_audio(input_path: str, output_path: str,
                         bitrate: str = "128k", mono: bool = False) -> str:
    """Audio siqish."""
    args = ["-i", input_path]
    if mono:
        args += ["-ac", "1"]
    args += ["-b:a", bitrate, output_path]
    await run_ffmpeg(args)
    return output_path


async def convert_audio_format(input_path: str, output_path: str,
                               codec: str) -> str:
    """Audio formatini o'zgartirish."""
    if codec == "pcm_s16le":
        args = ["-i", input_path, "-acodec", codec, output_path]
    else:
        args = ["-i", input_path, "-acodec", codec, "-q:a", "0", output_path]
    await run_ffmpeg(args)
    return output_path


async def merge_audios(input1: str, input2: str, output_path: str) -> str:
    """Ikki audioni birlashtirish."""
    await run_ffmpeg([
        "-i", input1, "-i", input2,
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[outa]",
        "-map", "[outa]", output_path,
    ])
    return output_path


async def apply_voice_effect(input_path: str, output_path: str,
                             effect: str) -> str:
    """Ovoz effektlarini qo'llash."""
    effects = {
        "f2m": "asetrate=44100*0.75,aresample=44100,atempo=1.333",
        "m2f": "asetrate=44100*1.35,aresample=44100,atempo=0.741",
        "baby": "asetrate=44100*1.8,aresample=44100,atempo=0.556",
        "robot": "afftfilt=real='hypot(re,im)*cos(0)':imag='hypot(re,im)*sin(0)':win_size=512:overlap=0.75",
        "underwater": "lowpass=f=500,volume=0.8",
        "demon": "asetrate=44100*0.6,aresample=44100,atempo=1.667",
        "drunk": "asetrate=44100*0.85,aresample=44100,atempo=1.176,vibrato=f=3:d=0.5",
        "megaphone": "highpass=f=300,lowpass=f=3000,volume=3,aecho=0.8:0.88:60:0.4",
        "ghost": "aecho=0.8:0.9:500|1000:0.3|0.2,lowpass=f=2000",
        "creature": "asetrate=44100*0.4,aresample=44100,atempo=2.5,overdrive=gain=10",
        "alien": "flanger=delay=5:depth=5:speed=1:regen=50:width=80:shape=sinusoidal:phase=50",
        "radio": "highpass=f=300,lowpass=f=3400,volume=1.5",
    }

    af = effects.get(effect)
    if not af:
        raise ValueError(f"Noma'lum effekt: {effect}")

    await run_ffmpeg(["-i", input_path, "-af", af, output_path])
    return output_path


async def apply_remix_effect(input_path: str, output_path: str,
                             preset: str) -> str:
    """Remix effektlari (pitch + speed)."""
    presets = {
        "deep_slowed": "asetrate=44100*0.65,aresample=44100,atempo=1.538",
        "super_slowed": "asetrate=44100*0.75,aresample=44100,atempo=1.333",
        "slowed": "asetrate=44100*0.85,aresample=44100,atempo=1.176",
        "speedup": "asetrate=44100*1.15,aresample=44100,atempo=0.87",
        "very_speedup": "asetrate=44100*1.35,aresample=44100,atempo=0.741",
    }
    af = presets.get(preset)
    if not af:
        raise ValueError(f"Noma'lum preset: {preset}")
    await run_ffmpeg(["-i", input_path, "-af", af, output_path])
    return output_path


async def apply_8d_audio(input_path: str, output_path: str) -> str:
    """8D Audio - 360° aylanma ovoz effekti."""
    # apulsator bilan atrofga aylanish simulyatsiyasi
    af = (
        "apulsator=mode=sine:hz=0.125:amount=1:offset_l=0:offset_r=0.5,"
        "extrastereo=m=2.5,"
        "aecho=0.8:0.88:40:0.3"
    )
    await run_ffmpeg(["-i", input_path, "-af", af, output_path])
    return output_path


async def apply_echo(input_path: str, output_path: str) -> str:
    """Echo effekti."""
    await run_ffmpeg([
        "-i", input_path,
        "-af", "aecho=0.8:0.9:100|200:0.5|0.3",
        output_path,
    ])
    return output_path


async def apply_reverb(input_path: str, output_path: str) -> str:
    """Reverb effekti."""
    await run_ffmpeg([
        "-i", input_path,
        "-af", "aecho=0.8:0.88:60|120|180:0.4|0.3|0.2",
        output_path,
    ])
    return output_path


async def apply_bass_boost(input_path: str, output_path: str) -> str:
    """Bass Boost."""
    await run_ffmpeg([
        "-i", input_path,
        "-af", "bass=g=15:f=80:w=0.6,equalizer=f=60:t=h:w=50:g=5",
        output_path,
    ])
    return output_path


async def apply_noise_reduction(input_path: str, output_path: str) -> str:
    """Shovqinni kamaytirish."""
    await run_ffmpeg([
        "-i", input_path,
        "-af", "highpass=f=80,lowpass=f=12000,afftdn=nf=-20",
        output_path,
    ])
    return output_path


async def reverse_audio(input_path: str, output_path: str) -> str:
    """Teskari aylantirish."""
    await run_ffmpeg([
        "-i", input_path, "-af", "areverse", output_path,
    ])
    return output_path


async def make_stereo(input_path: str, output_path: str) -> str:
    """Mono → Stereo."""
    await run_ffmpeg([
        "-i", input_path,
        "-af", "channelsplit,join=inputs=2:channel_layout=stereo",
        output_path,
    ])
    return output_path
