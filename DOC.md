# Cartoon Studio

Turns a short story into a cartoon video with a sprite character.

## Structure

```
cartoon_studio/
├── requirements.txt
├── assets/
│   ├── characters/<id>/    # cat, kid, adult, dog, car, bicycle: images + character.json
│   └── backgrounds/        # garden.jpeg, forest.jpeg, night.jpeg
├── docs/characters/        # contact sheets of every expression
├── tools/
│   ├── art/                # code that draws the kid, adult, dog, car and bicycle
│   ├── generate_characters.py  # redraw them and write their character.json
│   └── link_image.py       # link an expression to your own image(s)
└── app/
    ├── config.py           # constants and paths
    ├── models.py           # Scene (character + action), Story, Prompt
    ├── characters.py       # character.json loading, story -> character/expression
    ├── assets.py           # AssetManager (loads images)
    ├── actions.py          # keyword -> action detection (cat vocabulary, fallback)
    ├── storyboard.py       # demo / Ollama storyboard generation
    ├── fonts.py            # font loading
    ├── animator.py         # CharacterAnimator (one function per motion)
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
