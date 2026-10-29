# Stacks — Library Book Finder

Stacks is a responsive book discovery app. It runs locally without cloud setup. Connect the optional Supabase backend for email accounts, cross-device book storage, uploader-only editing, and public book listings.

## Run it

You need Python 3.

1. Open a terminal in this `outputs` folder.
2. Start the local web server:

   ```powershell
   python server.py
   ```

   On Windows, `py -3 server.py` is another option if `python` is not on your PATH.

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
4. Stop the server with **Ctrl+C** in the terminal.

You can also open `index.html` directly, though the local server is the recommended way to use the on-demand metadata lookup.

## Features

- Search a sample catalog by title, author, genre, or subject keywords.
- Filter by reading mood, genre, maximum page count, availability, and ebook format.
- Sort by match, sample rating, title, or length.
- Use the book guide to answer three preference questions and see three ranked picks.
- Save books and give recommendation feedback with **More like this** or **Not for me**.
- Save a reader name, favorite genre, and preferred length in this browser.
- Open book details, including publication descriptions, covers, and subject tags looked up from Open Library when available.
- View links to Open Library records and reader review searches.
- Use **＋ Add a book** to upload a cover image, one complete PDF, or ordered chapter PDFs; search Project Gutenberg or Open Library; or open a DRM-free `.epub` or `.txt` file for the current session.
  - Read uploaded PDFs and full text in a two-page reader with animated page turns, keyboard navigation, and saved reading position. Multi-file books open one chapter PDF at a time from the chapter menu.
- Read a page spread aloud with a device voice, or use the optional local Piper neural voice. PDF text can be narrated when it has a selectable text layer; scanned pages need OCR.
- Rank book-guide recommendations with an installed local Ollama model when Ollama is running; the guide prefers a model named DeepSeek and keeps its built-in matcher as a fallback.
- Use the responsive layout on desktop and mobile.
- Sign in to upload PDFs to private online storage and access them from another device.
- Edit and delete only your own listings; Supabase Row Level Security enforces ownership in the database and file store.
- Optionally publish book metadata. The PDF remains private to its uploader.
- Use public listing links, Book structured data, `robots.txt`, and `sitemap.xml` to support search-engine discovery.

## Set up accounts and online book storage

Online features require a Supabase project. No Supabase account secrets are included in this folder.

1. Create a project at [Supabase](https://supabase.com/dashboard).
2. In **SQL Editor**, run `supabase/schema.sql`. It creates the books tables, private storage buckets, and ownership rules. Keep row-level security enabled.
3. In **Project Settings → API**, copy the Project URL and **publishable/anon key**. Put them in `js/config.js`:

   ```js
   window.STACKS_CONFIG = {
     supabaseUrl: 'https://YOUR-PROJECT.supabase.co',
     supabaseAnonKey: 'YOUR-PUBLISHABLE-OR-ANON-KEY',
     siteUrl: 'https://YOUR-PUBLIC-DOMAIN'
   };
   ```

   The browser key is public by design; database policies protect the data. Never put a Supabase service-role/secret key in this file or browser code.

4. In **Authentication → URL Configuration**, set the Site URL to your final HTTPS domain and add that domain and `http://127.0.0.1:8000/**` to allowed redirect URLs. Keep email confirmation enabled and configure a working sender before public sign-ups.
5. Run Stacks locally, choose **Log in → Create an account**, confirm your email if prompted, then sign in. Uploads go to Supabase. Only the uploader can edit, delete, or read their PDFs.
6. To share searchable details, choose **Publish the book listing** when uploading or edit your listing later. This shares title, author, page count, and cover. It does not share the PDF.

The upload dialog supports up to 30 PDFs and 150 MB total per book. Larger PDFs use the browser build of `tus-js-client` for resumable uploads, loaded from jsDelivr. Check your Supabase plan's current storage and bandwidth limits before launch. Earlier books saved in IndexedDB can be moved to Supabase from **My book files → Move books saved in this browser to your account** after signing in.

If Supabase shows `permission denied for table books`, open **SQL Editor** and run the updated full `supabase/schema.sql` again. It includes explicit Data API grants; row-level security still restricts which records each account can read or change.

## Publish the website

1. Finish Supabase setup and set `siteUrl` in `js/config.js` to your final domain.
2. Choose a static host (for example, Netlify, Cloudflare Pages, or Vercel), upload the contents of this `outputs` folder, and attach your domain with HTTPS. `server.py` is for local development and is not a hardened public server.
3. Replace `YOUR-DOMAIN.example` in `robots.txt` and `sitemap.xml` with the final HTTPS domain. Replace the bracketed operator/contact details in `privacy.html` and `terms.html` before accepting public users.
4. Verify your domain in [Google Search Console](https://search.google.com/search-console), submit `https://YOUR-DOMAIN/sitemap.xml`, and use URL Inspection to request a crawl. Public listings use unique `?book=...` links. Google can take time to crawl a new site; a sitemap is a discovery hint, not a promise of indexing or rankings.
5. Before public sign-ups, decide how to respond to copyright complaints, abuse, account deletion requests, and storage/billing issues. Add a support contact, review privacy/terms for your jurisdiction, and configure backups and usage alerts.

Listing pages add canonical URLs and `Book` structured data after loading public metadata. Google can render JavaScript, but it may take an extra crawl/render step. Server-rendered listing pages would strengthen SEO further if organic search becomes important.

## PDF files

PDF pages are rendered with [Mozilla PDF.js](https://mozilla.github.io/pdf.js/getting_started/) from its pinned `pdfjs-dist` 6.3.289 release, loaded on demand from jsDelivr. PDF.js is licensed under Apache-2.0. The browser needs an internet connection the first time it loads the PDF reader. Without cloud setup, PDFs stay in this browser's storage. With Supabase configured and signed in, PDFs are stored in private Supabase Storage.

Local-mode covers and PDFs are stored in IndexedDB. Cloud-mode uploads are stored in private Supabase Storage. Keep chapter PDF files under 150 MB combined and select them in reading order; the upload dialog lets you move chapters up or down before saving.

## Files

```text
outputs/
├── index.html       Page structure and dialogs
├── server.py        Local-only web server and Ollama/Piper proxy
├── README.md        Local, cloud, and deployment guide
├── privacy.html     Privacy policy draft to complete before launch
├── terms.html       Book upload terms draft to complete before launch
├── robots.txt       Search crawler rules (set your domain)
├── sitemap.xml      Search sitemap starter (set your domain)
├── supabase/
│   └── schema.sql   Tables, private buckets, and ownership policies
├── css/
│   ├── styles.css   Layout, visual styling, and responsive rules
│   └── cloud.css    Account, publishing, and legal page styles
└── js/
    ├── app.js       Catalog, search, guide, login, and cloud uploads
    ├── cloud.js     Loads the Supabase client when configured
    └── config.js    Public project settings and domain
```

## Local Ollama recommendations

1. Start the Ollama app so its local API is available at `http://127.0.0.1:11434`.
2. If needed, install a DeepSeek model from Ollama, for example `ollama pull deepseek-r1:7b`.
3. Run Stacks with `python server.py` and open the book guide. Stacks detects installed Ollama models and prefers a model with `deepseek` in its name.

The book guide sends only the answers from that session and the available catalog titles to the local Ollama service. The app detects installed model names and prefers the first name containing `deepseek`; if none exists, it uses the first available model. If Ollama is unavailable, the built-in matcher ranks books instead. The included Python server binds to `127.0.0.1` and proxies model requests locally.

## Local neural narration (optional)

The reader can use a voice available in your browser right away. For a separate local neural voice, install Piper in a Python environment supported by Piper, then start its local HTTP voice service in a second terminal:

```powershell
python -m pip install "piper-tts[http]"
python -m piper.download_voices en_US-lessac-medium
python -m piper.http_server -m en_US-lessac-medium --host 127.0.0.1 --port 5000
```

With that service running, choose **Local neural voice** in the reader. The voice reads the current two-page spread. Piper is a text-to-speech engine; DeepSeek is the language model that helps rank recommendations. DeepSeek itself does not synthesize speech.

## Data and service notes

- The built-in catalog is sample data. Ratings and library availability are illustrative; reservation and waitlist buttons do not contact a library.
- Project Gutenberg search only includes titles marked public domain in the United States. Rights can differ by country; check before downloading or reading.
- Open Library is used for catalog metadata, not full-text access. A catalog record can be added to your shelf without a reader copy.
- The reader profile, saved books, reading position, and recommendation feedback remain in this browser. With Supabase configured, accounts and uploaded books sync across devices. Without it, online upload and account features prompt you to set up Supabase.
- Book metadata is requested from Open Library when a details view is opened. Gutenberg search and reading require an internet connection; the local server only fetches Gutenberg text from Gutenberg HTTPS hosts. Local text and EPUB files remain in memory for the current session only. The built-in EPUB reader supports DRM-free EPUBs in modern browsers.
- Age guidance and content warnings are not included unless a connected catalog provides them; the current demo labels them as unavailable.

## Public AI and voice

Ollama and Piper use the local Python API and work only on the computer running those services. A static public deployment does not expose that local API to visitors. Public recommendations fall back to built-in ranking and narration uses the visitor's device voice. Supporting AI for every visitor requires a separate hosted backend/model provider; never put private API keys in `js/config.js`.
