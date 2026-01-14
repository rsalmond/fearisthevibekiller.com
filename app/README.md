Instagram event pipeline

Overview
- Fetch recent posts from Instagram accounts.
- Store post metadata and media locally in a datastore.
- Classify posts as event listings with CPU-only CLIP analysis.
- Extract event details with OpenAI and render QMD files.

Setup
- Install dependencies: pip install -r /app/requirements.txt
- Set environment variables:
  - INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD (or USERNAME / PASSWORD)
  - OPENAI_API_KEY (only for second pass)
  - INSTAGRAM_FETCH_VERBOSE=1 to log per-account fetch errors
  - EVENT_LISTING_THRESHOLD=0.30 to set the event classifier threshold (lower is more sensitive)
  - LOG_LEVEL=DEBUG to enable debug logging for API calls and CLIP inference

Usage
- Fetch posts:
  python /app/main.py --accounts /data/accounts.txt fetch
- Classify event listings:
  python /app/main.py classify-events
- Extract event metadata:
  python /app/main.py extract-events
- Full pipeline:
  python /app/main.py --accounts /data/accounts.txt run
- Render a single event from testdata:
  python /app/render_single_event.py /app/testdata/eventclassifier/events/<POST_ID>
  python /app/render_single_event.py /app/testdata/eventclassifier/events/<POST_ID> --no-cache

CLI Arguments
- main.py
  - --datastore: Datastore root for downloaded posts and analysis results.
  - --limit: Maximum number of recent posts to fetch per account.
  - --session-file: Path to the Instagram session file.
  - --events-dir: Output directory for rendered event templates.
  - --model: OpenAI model for event metadata extraction.
  - --accounts: Path to a file of account URLs or a comma-separated list (required for fetch/run).
  - fetch: Fetch new posts.
  - classify-events: Classify posts as event listings.
  - extract-events: Extract event metadata and render templates.
  - run: Fetch, classify, and extract in one pass.
- render_single_event.py
  - post_dir: Path to a labeled event post directory.
  - --session-file: Instagram session file for DJ link lookups.
  - --output-dir: Directory for rendered templates.
  - --model: OpenAI model for event extraction when needed.
  - --no-cache: Ignore cached event data and re-run OpenAI extraction.
- label_event_posts.py
  - --datastore: Datastore root containing post metadata and media.
  - --limit: Stop after labeling/listing this many posts (0 means no limit).
  - --testdata-root: Root directory where labeled test data is stored.
  - --prioritize-events: Use the classifier to surface likely event listings first.
  - --match-qmd-events: Only show posts whose captions match QMD event text.
  - --events-dir: Directory containing QMD files with known events.
  - --list-classifications: List posts with captions, media paths, and classifier results.
  - --include-testdata: Include posts already stored in the labeled testdata directories.

Notes
- `classify-events` and `extract-events` operate only on the datastore and do not need `--accounts`.
- Datastore default: /app/datastore
- Events output: /app/_events
- Template: /data/template.txt or /data/template.qmd
- ffmpeg must be available on PATH for video frame extraction

Session notes
- The Instagram session file defaults to `/app/instagram_session.json` (or `--session-file`).
- To create a new session, remove the old session file and run:
  `python /app/main.py --accounts /data/accounts.txt fetch`
