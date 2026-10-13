# Cartoon Studio

Turns a short story into a cartoon video with a sprite character.

## Structure

```
cartoon_studio/
├── main.py                 # entry point
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
    └── container.py        # wiring + render()/frame() wrappers
```

## Run

```
pip install -r requirements.txt
python main.py
```

Requires FFmpeg on your PATH. Put your own PNG/JPEG files in `assets/` first.
