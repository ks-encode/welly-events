# Welly Events v1.7.3 — Eventfinda API pagination fix

## What changed

The Eventfinda API returns an `events.count` field that may reflect the number of rows in the current page, not the total available. The earlier scraper treated `count` as an overall total, so a first page with 10 event records could incorrectly stop pagination after the first 10. This version:

- Continues with the actual returned page size as the offset (`0, 10, 20, ...`), even when a page returns fewer than the requested 100 records.
- Treats only explicitly named fields such as `total` / `total_count` as a result-set total; otherwise continues until the API returns an empty page.
- Detects repeated pages and raises a visible error rather than silently publishing a partial set.
- Logs each page's offset, returned record count, and any explicit total.
- Caps retrieval at 60 pages to protect API quota; reports an error if the cap is reached before the result set is exhausted.
- Retains v1.7.1 browser-style headers and the v1.7.2 Wellington Region lookup, date filtering, API credentials and source settings.

### Why your old log said 10 records, 62 dates

Those are two different counts. The API returned 10 event objects, and the calendar expands recurring/multi-session events into dated entries. This is not necessarily 62 distinct event titles.

## GitHub install

1. Extract the small `welly_events_v1_7_3_eventfinda_pagination_update.zip`.
2. Upload its `WellyOddities` and `public` files into the corresponding folders in `main`, replacing the existing files (preserve directory structure). There is no `.github` folder in this update; your existing working GitHub Actions workflow can remain untouched.
3. Commit and run **Actions → Refresh and publish Welly Oddities → Run workflow**.
4. In the `Refresh the public source index` job, look for `Eventfinda API page` lines and the final `Eventfinda API:` summary.

The API credentials must remain in GitHub Actions Secrets, not in the repository. No credentials are bundled.

This update has been unit tested with simulated paginated API responses; real API behavior needs confirmation from your GitHub run. If page 2 repeats page 1 or returns an error, the log will now expose that issue.
