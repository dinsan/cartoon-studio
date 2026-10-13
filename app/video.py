import subprocess
from pathlib import Path

from .config import FPS, HEIGHT, WIDTH
from .models import Story
from .scene_renderer import SceneRenderer


class VideoRenderer:
    def __init__(self, scene_renderer: SceneRenderer):
        self.scene_renderer = scene_renderer

    def render(self, story: Story, output: str | Path, progress) -> Path:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)

        total = sum(scene.duration * FPS for scene in story.scenes)
        count = 0
        video_path = output / "video.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video_path),
        ]

        log_path = output / "render.log"

        with log_path.open("w") as log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=log,
            )

            try:
                for n, scene in enumerate(story.scenes, 1):
                    for f in range(scene.duration * FPS):
                        t = f / FPS
                        image = self.scene_renderer.render_frame(scene, t)

                        if f == 0:
                            image.save(output / f"scene-{n}.png")

                        process.stdin.write(image.tobytes())
                        count += 1

                        if count % FPS == 0:
                            progress(round(count / total * 95))

                process.stdin.close()

                return_code = process.wait(timeout=90)
                if return_code != 0:
                    raise RuntimeError(
                        "Video encoder failed. Check FFmpeg installation and "
                        f"{log_path}"
                    )

            except BaseException:
                process.kill()
                process.wait()
                raise

        (output / "story.json").write_text(
            story.model_dump_json(indent=2),
            encoding="utf-8",
        )

        progress(100)
        return video_path
