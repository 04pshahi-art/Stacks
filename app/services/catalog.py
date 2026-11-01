"""The fixed vocabulary of genres and moods used across the app."""

GENRES = (
    "Fantasy",
    "Science Fiction",
    "Mystery",
    "Romance",
    "Thriller",
    "Horror",
    "Historical",
    "Literary",
    "Adventure",
    "Poetry",
    "Non-fiction",
    "Self-help",
)

MOODS = (
    "Cozy",
    "Dark",
    "Adventurous",
    "Romantic",
    "Thoughtful",
    "Funny",
    "Suspenseful",
    "Inspiring",
    "Melancholic",
    "Mysterious",
)

GENRE_CHOICES = [(genre, genre) for genre in GENRES]
MOOD_CHOICES = [(mood, mood) for mood in MOODS]

MAX_TAGS_PER_KIND = 3
