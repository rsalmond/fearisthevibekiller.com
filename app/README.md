Instagram event pipeline

Overview
- Fetch recent posts from Instagram accounts.
- Store post metadata and media locally in a datastore.
- Classify posts as event listings with CPU-only CLIP analysis.
- Extract event details with OpenAI and render QMD files.

Setup
- Install dependencies: pip install -r /app/app/requirements.txt
- Set environment variables:
  - INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD (or USERNAME / PASSWORD)
  - INSTAGRAM_SESSIONID (preferred if username/password login fails; can be raw value or full cookie string)
  - OPENAI_API_KEY (only for second pass)
  - INSTAGRAM_FETCH_VERBOSE=1 to log per-account fetch errors
  - EVENT_LISTING_THRESHOLD=0.30 to set the event classifier threshold (lower is more sensitive)
  - LOG_LEVEL=DEBUG to enable debug logging for API calls and CLIP inference

Usage
- Fetch posts:
  python /app/app/main.py --accounts /app/data/accounts.txt fetch
- Classify event listings:
  python /app/app/main.py classify-events
- Extract event metadata:
  python /app/app/main.py extract-events
- Progress report:
  python /app/app/main.py progress
- Full pipeline:
  python /app/app/main.py --accounts /app/data/accounts.txt run
- Render a single event from testdata:
  python /app/app/render_single_event.py /app/app/testdata/eventclassifier/events/<POST_ID>
  python /app/app/render_single_event.py /app/app/testdata/eventclassifier/events/<POST_ID> --no-cache

CLI Arguments
- main.py: Run the pipeline stages and report progress.
  - Subcommands: fetch, classify-events, extract-events, progress, run.
  - Flags: --datastore, --limit, --session-file, --events-dir, --model, --accounts (fetch/run).
- render_single_event.py: Render a template for a single labeled event post.
  - Arguments: post_dir.
  - Flags: --session-file, --output-dir, --model, --no-cache.
- label_event_posts.py: Label or list posts for classifier training.
  - Flags: --datastore, --limit, --testdata-root, --prioritize-events, --match-qmd-events, --events-dir, --list-classifications, --include-testdata.

Notes
- `classify-events` and `extract-events` operate only on the datastore and do not need `--accounts`.
- Datastore default: /app/app/datastore
- Events output: /app/data/_events
- Template: /app/data/template.qmd
- Session file: /secure/instagram_session.json
- Environment: /secure/.env
- ffmpeg must be available on PATH for video frame extraction

Session notes
- The Instagram session file defaults to `/secure/instagram_session.json` (or `--session-file`).
- To create a new session, remove the old session file and run:
  `python /app/app/main.py --accounts /app/data/accounts.txt fetch`


# useful commands

sudo nerdctl build -t instagram-event-pipeline /app/app

sudo nerdctl run --rm --env-file /secure/.env -v /app:/app --entrypoint python instagram-event-pipeline /app/app/main.py progress
sudo nerdctl run --rm --env-file /secure/.env -e LOG_LEVEL=INFO -v /app:/app --entrypoint python instagram-event-pipeline /app/app/main.py extract-events
