<div align="center">

# 📖 Folio

**A cozy online library where books turn their pages, read themselves aloud, and find you.**

Read, upload, share, and get told when your favourite author posts a new chapter.<br>
Everything runs on your own computer, including the AI.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-XAMPP-4479A1?logo=mysql&logoColor=white)
![Ollama](https://img.shields.io/badge/AI-Ollama%20%2B%20DeepSeek%20R1-8A2BE2)
![Voice](https://img.shields.io/badge/Voice-Kokoro%20%7C%20Piper-C9A227)
![Security](https://img.shields.io/badge/Security-CSP%20%C2%B7%20CSRF%20%C2%B7%20rate%20limits-2E8B57)

</div>

---

## ✨ Why Folio?

I wanted a reading site that feels like holding a real book, not scrolling a web page.
So Folio has an actual page-turn animation, a proper two-page spread on desktop, and one
calm page on your phone. It can also read to you in a soft, storyteller voice, and it never
sends your books to anyone else's servers.

<!--
  Add a few screenshots here once you have them. Put the images in a docs/ folder, e.g.:
  <p align="center"><img src="docs/reader.png" width="720" alt="The Folio reader"></p>
-->

## 🌟 What it can do

| | |
|---|---|
| 📚 **A real reader** | A 3D page flip, a two-page spread on desktop, a single page on phones, full-screen mode, three paper colours, adjustable text size, and your place saved automatically. |
| ⬆️ **Upload anything** | `.txt`, `.md`, `.epub`, `.pdf`, or a `.zip` holding a Markdown file and its pictures. Folio splits the book into chapters for you. |
| 🖼️ **Pictures in books** | Images inside EPUBs and Markdown books show up on the page, sized so they never spill over. |
| 🔒 **Private or public** | Keep a book to yourself, or share it with everyone. Private books simply don't exist for other people. |
| ➕ **Chapter by chapter** | Write as you go, or drop in a whole file of chapters at once. |
| 🔔 **New-chapter alerts** | Follow a book and get a notification when the author publishes more. |
| 🧠 **Learns your taste** | Folio notices the genres and moods you finish, and after 3 to 5 books it starts recommending. |
| 💬 **A local AI librarian** | Ask the chat for something "cozy and a bit mysterious". It runs on your machine through Ollama (DeepSeek R1 7B by default). |
| 🎧 **Read aloud** | Press play and the page is read to you, then turned, then the next. A natural AI voice (Kokoro) if you set it up, your browser's voice if not. |
| 🛡️ **Careful with security** | Strong passwords, lockouts, CSRF protection, a strict content policy, and safe handling of every upload. |

## 🧰 Built with

- **Python + Flask** for the server, with SQLAlchemy, Flask-Login, Flask-WTF and Flask-Limiter
- **MySQL** from XAMPP for the data (SQLite is used in the tests)
- **Plain JavaScript modules and hand-written CSS**, with no frameworks and no build step
- **Ollama** for the chat assistant, and **Kokoro** or **Piper** for the voice

## 🚀 Getting started (Windows with XAMPP)

You'll need Python 3.10 or newer and [XAMPP](https://www.apachefriends.org).

**1. Start MySQL.** Open the XAMPP control panel and press *Start* next to MySQL.

**2. Get the code and install the packages.**

```bash
git clone https://github.com/YOUR-NAME/folio.git
cd folio
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

**3. Add a secret key.** Generate one and paste it after `SECRET_KEY=` in your new `.env` file:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**4. Create the database.** This makes the `folio` database and all its tables:

```bash
flask --app run init-db
```

Want some sample books to look at first?

```bash
flask --app run seed-demo
```

**5. Run it.**

```bash
python run.py
```

Open <http://127.0.0.1:5000>, create an account, and you're in. There's no default login:
the first account is whatever you register.

> **Tip:** To open Folio on your phone, start it with `flask --app run run --host 0.0.0.0`
> instead, then visit `http://YOUR-PC-IP:5000` while on the same Wi-Fi.

## 🤖 The local AI librarian

1. Install [Ollama](https://ollama.com).
2. Pull the model: `ollama pull deepseek-r1:7b`
3. Leave Ollama running. The chat bubble on the home page will start answering.

No Ollama? Nothing breaks. The chat still shows matching books and just says the AI is resting.

A 7B model on a laptop can take a little while to answer, so Folio waits up to three minutes.
You can change the model or the timeout in `.env`.

## 🎧 Making it read aloud

Press the headphones button in the reader (or the **L** key). Folio reads the page, turns it,
and keeps going. If you turn a page yourself, it carries on from there.

| Voice | Quality | Setup |
|---|---|---|
| **Browser voice** | Fine | Nothing to do. |
| **Kokoro** | Sweet and smooth, with several voices | See below. Runs on a normal CPU, no graphics card needed. |
| **Piper** | Clear and light | `pip install piper-tts`, download a voice, set `PIPER_BIN` and `PIPER_MODEL`. |

**Setting up Kokoro**

1. `pip install -U kokoro-onnx`
2. Download `kokoro-v1.0.onnx` and `voices-v1.0.bin` (about 350 MB together) from the
   [model files page](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0)
   into a folder such as `C:\kokoro`.
3. Add these two lines to your `.env` file, then restart Folio:

   ```
   KOKORO_MODEL=C:\kokoro\kokoro-v1.0.onnx
   KOKORO_VOICES=C:\kokoro\voices-v1.0.bin
   ```

Open the Listen panel and pick a voice: Heart, Bella, Nicole, Sky, Emma, Isabella, Michael or George.
Dialogue in quotation marks is read a little livelier than the narration, and there is a pause
between paragraphs, so it sounds more like someone telling a story.

If the AI voice ever fails, Folio quietly switches to your browser's voice and lets you know.

## 📥 Adding books

| You upload | What happens |
|---|---|
| `.txt` / `.md` | Split at headings like "Chapter 1". |
| `.epub` | Chapters, title, author and pictures are all read from the book. |
| `.pdf` | Text is pulled out and grouped into chapters. Scanned PDFs (images of pages) need OCR first. |
| `.zip` | One Markdown file plus its images. Reference a picture with `![caption](images/map.png)`. |

Uploads up to 20 MB are accepted. Files are read in memory and never saved or run, pictures
are re-encoded as safe JPEGs, and there are limits on page counts and total text so one huge
file can't bring the site down.

To add a lot of chapters to a book you already started, use **Add many chapters at once** on its
chapter page. Followers get a single notification instead of dozens.

## ⌨️ Reader controls

| Action | How |
|---|---|
| Turn the page | Arrow keys, Space, swipe, or the side buttons |
| Full-screen reading | **F** |
| Chapter list | **C** |
| Read aloud | **L** |
| Close a panel or leave full screen | **Esc** |

## ⚙️ Settings

Everything lives in `.env`. The important ones:

| Setting | What it does |
|---|---|
| `SECRET_KEY` | **Required.** Keeps sessions safe. |
| `DATABASE_URL` | Where the database is. The XAMPP default is already filled in. |
| `COOKIE_SECURE` | Set to `true` once you serve the site over HTTPS. |
| `AI_ENABLED`, `OLLAMA_URL`, `OLLAMA_MODEL` | The chat assistant. |
| `KOKORO_MODEL`, `KOKORO_VOICES` | The Kokoro voice files. |
| `PIPER_BIN`, `PIPER_MODEL` | The Piper voice, if you prefer it. |
| `RATELIMIT_STORAGE_URI` | Use `redis://...` when running more than one worker. |

## 🔐 Security, in plain words

- Passwords are hashed with scrypt, must be reasonably strong, and accounts lock after repeated failed sign-ins.
- Login errors are all the same, so nobody can tell which accounts exist.
- Every form and API call carries a CSRF token, and requests are rate limited.
- A strict Content-Security-Policy blocks inline scripts. Book text is never rendered as HTML.
- Changing your password signs out every other session.
- A private book returns "not found" to everyone except its owner, including its pictures and its chapter API.
- Uploads are parsed on the server with size, page, picture and text limits, and archive paths can't escape.
- The text-to-speech command is fixed in the server settings. Nothing a visitor types ever reaches a command line.

**Before putting it on the internet:** set `COOKIE_SECURE=true`, use HTTPS, create a real MySQL user instead
of `root`, and point rate limiting at Redis.

## 🗂️ Project layout

```
folio/
├── app/
│   ├── blueprints/    # pages and API routes (auth, books, reader, speech, ...)
│   ├── models/        # users, books, chapters, pictures, reading activity
│   ├── services/      # the real work: importing, publishing, recommendations, voice
│   ├── forms/         # validated forms
│   ├── templates/     # Jinja pages
│   └── static/        # CSS and JavaScript (reader, narrator, chat)
├── tests/             # pytest suite
├── run.py
└── requirements.txt
```

## 🧪 Tests

```bash
python -m pytest
```

They cover signing in and lockouts, private-book access, upload limits and damaged files, the PDF text
limit, picture safety, and cleaning up files when a save fails. They use a throw-away in-memory database,
so your real data is never touched.

## 🩹 If something goes wrong

| Problem | Fix |
|---|---|
| `Unknown database 'folio'` | Start MySQL in XAMPP, then run `flask --app run init-db` again. You can also create an empty `folio` database in phpMyAdmin. |
| "This PDF needs a password" | It really is password protected. Remove the password and try again. |
| "No selectable text" in a PDF | It's a scan. Run OCR on it first. |
| The AI voice stays silent | Check both Kokoro paths in `.env`, then restart. Folio falls back to the browser voice meanwhile. |
| Chat says the AI is offline | Make sure Ollama is running and you've pulled the model. |

## 🛣️ What's next

- Email confirmation when you sign up
- "Forgot password" by email
- More voices and a better way to mark up emotion when reading aloud

## 💛 Contributing

Ideas and fixes are welcome. Open an issue to talk it through, keep the code tidy and free of
duplication, and run `python -m pytest` before sending a pull request.

## 📄 License

Add the licence you'd like here (MIT is a friendly default).

<div align="center">

Made with a lot of tea and a love of books. 📚

</div>
