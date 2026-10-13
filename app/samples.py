from .models import Scene, Story


def create_test_story() -> Story:
    return Story(
        title="Milo the Happy Cat",
        scenes=[
            Scene(
                narration="Milo wakes up in the beautiful garden.",
                setting="garden",
                action="wake",
                duration=4,
            ),
            Scene(
                narration="Milo starts walking around the garden.",
                setting="garden",
                action="walk",
                duration=4,
            ),
            Scene(
                narration="Suddenly, Milo sees a butterfly and jumps!",
                setting="forest",
                action="jump",
                duration=4,
            ),
            Scene(
                narration="Milo dances happily with his new friend.",
                setting="forest",
                action="dance",
                duration=4,
            ),
            Scene(
                narration="After a wonderful day, Milo falls asleep.",
                setting="night",
                action="sleep",
                duration=5,
            ),
        ],
    )
