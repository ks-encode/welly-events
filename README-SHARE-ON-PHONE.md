# Welly Oddities — public phone-friendly edition

This folder contains the original local Welly Oddities app **plus** a ready-to-deploy website. The website uses the same Wellington-region filters and the same event scrapers, including **Engineering New Zealand** and **The Fringe Bar**.

## What friends see

A normal link like `https://YOUR-USERNAME.github.io/welly-oddities/`. It works on iPhone, Android and desktop in a browser. No Python install, BAT file, login or GitHub account needed for visitors. Dates and event filters work on their phones; the filter settings and saved stars remain private to each visitor's device.

The feed is **scheduled**, not a real-time ticketing feed: GitHub checks the source websites daily. Scrapers may fail or miss listings and should not be treated as exhaustive; attendees should confirm the event with its organiser. The "Reload published feed" button fetches the last published feed, **not** a fresh scrape of the websites.

## Put it online (one-time setup)

1. Sign in to **GitHub** (create a free account if necessary).
2. Create a **public** repository called `welly-oddities`, with a `main` branch. A public repository makes its files visible to everyone; this package contains only public event listings and app code. Do not add personal files.
3. Upload the **contents of this extracted folder** to the repository root, **including the hidden `.github/workflows` folder**. You can use GitHub Desktop or the GitHub website's **Add file → Upload files** (drag all extracted contents, not the zip archive itself). Commit the upload to `main`.
4. In the repository, open **Settings → Pages → Build and deployment → Source** and select **GitHub Actions**.
5. In the **Actions** tab, open **Refresh and publish Welly Oddities**, then click **Run workflow** (branch `main`) to run the first refresh/deployment. The initial push may also trigger it automatically; one successful run is enough.
6. When the workflow completes successfully, open **Settings → Pages** for the public URL. Usually `https://YOUR-USERNAME.github.io/welly-oddities/`. Share that URL with anyone.

**Note:** If the first workflow ran before Pages was enabled, re-run it from Actions after selecting the Pages source. If GitHub reports a workflow permission error, check **Settings → Actions → General → Workflow permissions** and allow read/write where available. The workflow needs permission to save its latest event cache for the next daily update.

## After setup

- GitHub runs the indexer automatically on a daily schedule. A scheduled job can run late or be skipped due to GitHub Actions capacity or policies; visit the Actions tab occasionally to check.
- You can run an immediate refresh yourself from **Actions → Refresh and publish Welly Oddities → Run workflow**.
- The website's **Reload published feed** button just reloads the latest posted records; visitors cannot trigger the public scraper.
- Adding a website or fixing a scraper means updating the repository code, then running the workflow again.
- Add the site to your phone's home screen using your browser's **Share → Add to Home Screen** (iPhone) or the browser menu's **Add to Home screen/Install app** (Android, if offered).
- Source switches and bookmarks are individual to each browser and do not sync across devices.

## What's in here

- `public/` — the actual phone-friendly website, standalone event feed and home-screen icons.
- `WellyOddities/` — all original Python scrapers, the local-server version and tests.
- `WellyOddities/build_public.py` — creates `public/index.html` and `public/events-feed.json` from the latest cached data.
- `WellyOddities/refresh_for_web.py` — runs all site scrapers and saves results without launching a server.
- `.github/workflows/refresh-and-publish.yml` — daily scheduled refresh and Pages deployment.

## Try it before publishing

Open `public/index.html` to see the bundled calendar. To simulate the published feed locally, start a basic Python web server from the `public` folder:

```bash
cd public
python -m http.server 8000
```

Then visit `http://127.0.0.1:8000` on that computer. The public site does **not** serve `/api/refresh` — automatic refresh happens only through GitHub Actions.

### Important data limitation

The initial calendar is an October 2026 snapshot, not an actively verified feed. The site becomes more current only **after a successful scheduled scraper run**. Some external sites are not machine-readable. Each source card reports its own indexing status, and the top of the app shows the **last index attempt** rather than incorrectly claiming every source is current. Old records from a source may be retained if that source fails to scrape.
