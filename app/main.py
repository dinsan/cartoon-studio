from pathlib import Path

from app.container import render
from app.samples import create_test_story


def show_progress(value: int) -> None:
    print(f"Rendering: {value}%")


if __name__ == "__main__":
    story = create_test_story()
    video = render(story, Path("output"), show_progress)
    print(f"\nVideo created successfully: {video}")
