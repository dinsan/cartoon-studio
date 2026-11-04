# Cartoon Studio

Turns a short story into a cartoon video with a sprite character.

## Structure

```
cartoon_studio/
├── requirements.txt
├── assets/
│   ├── characters/cat/     # idle.png, walk.png, walk_1.png, ...
│   └── backgrounds/        # garden.jpeg, forest.jpeg, night.jpeg
└── app/
    ├── config.py           # constants and paths
    ├── models.py           # Action, Scene, Story, Prompt
    ├── assets.py           # AssetManager (loads images)
    ├── actions.py          # keyword -> action detection
    ├── storyboard.py       # demo / Ollama storyboard generation
    ├── fonts.py            # font loading
    ├── animator.py         # CharacterAnimator (sprite motion)
    ├── camera.py           # camera moves and easing helpers
    ├── scene_renderer.py   # SceneRenderer (one frame)
    ├── video.py            # VideoRenderer (FFmpeg encoding)
    ├── samples.py          # create_test_story
    ├── container.py        # wiring + render()/frame() wrappers
    ├── main.py             # CLI entry point (python -m app.main)
    ├── api/main.py         # FastAPI app (routes + render jobs)
    └── data/               # per-job output written by the API
```

## Run

From the project root (the folder containing `app/`):

```
pip install -r requirements.txt
python -m app.main                                    # render the sample story to output/video.mp4
python -m uvicorn app.api.main:app --port 8000        # or start the API (docs at /docs)
```

Requires FFmpeg on your PATH. Put your own PNG/JPEG files in `assets/` first.
