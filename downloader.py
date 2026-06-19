import asyncio
import os
import re
import tempfile
from typing import Optional
import yt_dlp


class VideoDownloader:
    def __init__(self):
        self.download_dir = tempfile.gettempdir()

    def _format_duration(self, seconds: int) -> str:
        if not seconds:
            return "Noma'lum"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

    def _format_views(self, count) -> str:
        if not count:
            return "Noma'lum"
        if count >= 1_000_000:
            return f"{count/1_000_000:.1f}M"
        if count >= 1_000:
            return f"{count/1_000:.1f}K"
        return str(count)

    async def get_video_info(self, url: str) -> Optional[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_info_sync, url)

    def _get_info_sync(self, url: str) -> Optional[dict]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'cookiefile': 'cookies.txt',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                return None

            formats_raw = info.get('formats', [])
            quality_map = {}

            for f in formats_raw:
                if f.get('vcodec') == 'none' or not f.get('height'):
                    continue

                height = f.get('height')
                quality_label = f"{height}p"
                filesize = f.get('filesize') or f.get('filesize_approx') or 0

                if quality_label not in quality_map or filesize > quality_map[quality_label]['filesize']:
                    quality_map[quality_label] = {
                        'format_id': f.get('format_id'),
                        'quality': quality_label,
                        'filesize': filesize,
                        'ext': f.get('ext', 'mp4'),
                    }

            if not quality_map:
                quality_map = {
                    'best': {
                        'format_id': 'best',
                        'quality': 'Eng yaxshi',
                        'filesize': 0,
                        'ext': 'mp4',
                    }
                }

            sorted_formats = sorted(quality_map.items(), key=lambda x: int(re.findall(r'\d+', x[0])[0]) if re.findall(r'\d+', x[0]) else 9999)

            return {
                'title': info.get('title', 'Video'),
                'duration': self._format_duration(info.get('duration', 0)),
                'view_count': self._format_views(info.get('view_count')),
                'thumbnail': info.get('thumbnail'),
                'formats': [v for _, v in sorted_formats],
            }

        except Exception as e:
            raise Exception(f"Ma'lumot olishda xatolik: {e}")

    async def download_video(self, url: str, format_id: str) -> tuple[str, int]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._download_sync, url, format_id)

    def _download_sync(self, url: str, format_id: str) -> tuple[str, int]:
        output_template = os.path.join(self.download_dir, '%(id)s_%(height)s.%(ext)s')

        ydl_opts = {
            'format': 'bv*+ba/best',
            'cookiefile': 'cookies.txt',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                if not os.path.exists(file_path):
                    file_path = file_path.rsplit('.', 1)[0] + '.mp4'

                if not os.path.exists(file_path):
                    video_id = info.get('id', '')
                    for fname in os.listdir(self.download_dir):
                        if video_id in fname:
                            file_path = os.path.join(self.download_dir, fname)
                            break

                file_size = os.path.getsize(file_path)
                return file_path, file_size

        except Exception as e:
            raise Exception(f"Yuklashda xatolik: {e}")
