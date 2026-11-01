"""Sample content for trying the app. All text here is original to Folio."""
from sqlalchemy import select

from .extensions import db
from .models import User
from .services.importing import ParsedChapter
from .services.publishing import BookDetails, create_book

PUBLISHER_NAME = "inkwell"
PUBLISHER_EMAIL = "inkwell@example.com"

SAMPLE_BOOKS = [
    {
        "title": "The Lantern Keeper of Saltmarsh",
        "author": "Mira Hale",
        "description": "A quiet village, a lighthouse that glows at the wrong hour, and a baker who notices.",
        "status": "complete",
        "genres": ["Fantasy", "Mystery"],
        "moods": ["Cozy", "Mysterious"],
        "chapters": [
            ("The Wrong Hour", [
                "Saltmarsh woke slowly, the way a cat does, one rumour at a time. By the time Ines had lit the bakery ovens, three neighbours had already told her the lighthouse was glowing again, and it was not yet dawn.",
                "She wiped flour from her hands and went to the window. Across the reeds, the old tower sat dark against a darker sky. Then, as if it had been waiting for her to look, a single pale lantern bloomed at the top and drifted slowly down the stairs.",
                "Nobody had kept that lighthouse in forty years. Ines knew because her grandmother had told her so, often, with the particular satisfaction of someone who kept every secret she was ever given.",
                "The loaves could wait. She tied her scarf, tucked a warm roll in each pocket for courage, and took the long path through the marsh where the boards creaked like old knees.",
                "Halfway there she heard a voice humming. It was not a tune she knew, but her feet knew it, and they slowed down all by themselves.",
            ]),
            ("The Keeper's Kettle", [
                "The door at the base of the tower stood open, and inside, a kettle was singing on a stove that should have been cold. A small woman in a patched coat looked up from the table as though Ines were merely late for tea.",
                "'Sit,' she said. 'You are the baker. Your grandmother promised me you would come when the lantern woke.' She poured two cups of something that smelled of smoke and orange peel.",
                "Ines sat. She had a hundred questions, and every one of them was too polite to be the right one, so she asked the only thing that came out. 'How long have you been here?'",
                "The woman smiled. 'Long enough to know every boat that ever came home, and every boat that did not.' She nudged the cup closer. 'Drink. The marsh is awake, and it will want to meet you.'",
                "Outside, the reeds began to whisper in a language of soft hissing. Ines held her cup in both hands and realised, with some alarm, that she understood the first word.",
            ]),
            ("What the Reeds Said", [
                "The first word was her name. The second was a place, and the third was a warning, delivered so gently that it took her a moment to hear it as one.",
                "'The tide is not the only thing coming in,' the keeper translated, topping up the cups. 'Someone has been tampering with the tower's light, and they are not from Saltmarsh.'",
                "Ines thought of the stranger who had bought six loaves on Tuesday and asked, too casually, about the tides. She thought of his clean boots, and the way he had not once looked at the sea.",
                "'I think I have met them,' she said slowly. 'They liked rye.' The keeper laughed so hard the kettle rattled, and for the first time that morning, the dark in the tower felt like company instead of threat.",
            ]),
        ],
    },
    {
        "title": "Orbit of Quiet Things",
        "author": "Tomas Reyes-Lindqvist",
        "description": "A station engineer, a failing garden module, and the long arithmetic of staying.",
        "status": "complete",
        "genres": ["Science Fiction", "Literary"],
        "moods": ["Thoughtful", "Melancholic"],
        "chapters": [
            ("Inventory", [
                "On the ninety-first day without a resupply ship, Dara counted the tomatoes again. There were fourteen, which was one fewer than yesterday and, she decided, not a theft but a decision the plant had made without consulting her.",
                "The garden module hummed its low, patient note. Behind its glass, the orbit turned the planet slowly beneath her, blue and white and indifferent. She had stopped finding it beautiful around day sixty, and started finding it necessary.",
                "She logged the count. She logged the temperature, the humidity, and the small rust-coloured patch on the third leaf. Then, because nobody was awake to read it, she added a line that was not data at all: 'I miss the sound of rain.'",
                "The station did not answer. Stations rarely do. But the lights along the corridor dimmed by a single shade, which was the schedule's way of saying evening, and Dara found that she was grateful for even that.",
            ]),
            ("Arithmetic", [
                "Oxygen was simple. Water was nearly simple. Food was a long division with a remainder, and the remainder was her.",
                "She worked the figures at the small table where, once, six people had argued about music. If she ate less in the first month and the garden recovered, the numbers closed. If the garden did not, they closed too, only later and with less to say about it.",
                "She tried to remember when she had last spoken aloud, and could not. So she spoke now, to the tomatoes, and found her voice was rougher than she expected, like a door that had not been opened in a while.",
                "'Thirteen,' she told them. 'We are going to be very careful.' The plants, being plants, kept their opinions to themselves. But she thought one of them leaned a little closer to the light.",
            ]),
        ],
    },
    {
        "title": "Seven Days to the Summit",
        "author": "Kofi Adeyemi",
        "description": "Two rivals, one unclimbed ridge and a week of weather that does not care who wins.",
        "status": "ongoing",
        "genres": ["Adventure"],
        "moods": ["Adventurous", "Inspiring"],
        "chapters": [
            ("Base Camp", [
                "The wind at base camp had opinions, and it shared them all night. Nuria lay in her sleeping bag listening to the tent fabric argue with the dark and tried not to count the hours until the alarm.",
                "At five the stove hissed to life, and Joaquin's grinning face appeared in the doorway, lit from below like a campfire story. 'Seven days,' he said. 'Weather window says seven days. After that, the mountain keeps whatever it likes.'",
                "They had not spoken for two years, not since the argument on the north face, and yet here they were, sharing a stove and a map. Mountains, she thought, were good at that. They made old quarrels feel small and old friendships feel necessary.",
                "She packed the rope, the radio, and the small tin of pepper she always carried for luck. Outside, the ridge stood against a sky the colour of cold steel, and for the first time in two years she was not afraid of it.",
            ]),
            ("The Icefall", [
                "The icefall greeted them at first light, a staircase of blue towers that groaned when the sun touched them. Joaquin went first, as he always did, testing each step with the shaft of his axe and humming something tuneless.",
                "Nuria counted his steps because counting kept her calm. Forty-one, forty-two. A crack ran beside the route like a drawn line, and she chose not to wonder how deep it went.",
                "At the third tower the rope snapped taut between them. For a moment neither moved. Then Joaquin laughed, a short startled sound, and said, 'Well. That woke me up.' She laughed too, and the sound carried across the ice and came back changed.",
            ]),
        ],
    },
]


def _get_or_create_publisher(password: str) -> User:
    user = db.session.scalar(select(User).where(User.email == PUBLISHER_EMAIL))
    if user is None:
        user = User(username=PUBLISHER_NAME, email=PUBLISHER_EMAIL, onboarded=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    return user


def create_demo_library(password: str) -> int:
    """Create the demo publisher and sample public books. Returns how many were added."""
    publisher = _get_or_create_publisher(password)
    existing_titles = {book.title for book in publisher.books}
    created = 0
    for sample in SAMPLE_BOOKS:
        if sample["title"] in existing_titles:
            continue
        chapters = [
            ParsedChapter(title, "\n\n".join(paragraphs)) for title, paragraphs in sample["chapters"]
        ]
        details = BookDetails(
            title=sample["title"],
            author=sample["author"],
            description=sample["description"],
            visibility="public",
            status=sample["status"],
            genres=sample["genres"],
            moods=sample["moods"],
        )
        create_book(publisher, details, chapters)
        created += 1
    return created
