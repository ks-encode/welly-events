# Welly Events v1.7.2 — Eventfinda coverage and diagnostics

This is a focused update to the existing v1.7.1 / v1.7 GitHub project.

## Why 61 might not be the full count

The previous Eventfinda API indexer:

- Requested `rows=100` and **stopped after any short page**, even if the API reported more results.
- Advanced pagination in increments of 100 even if the server returned fewer rows.
- Could accept a Wellington-city location match without checking for Wellington Region.
- Left start/end date bounds implicit, making the API's time window hard to check.
- Logged only the final count, which made it impossible to tell whether API coverage or parsing was at fault.

## What changed

- Fetches upcoming events for an explicit rolling 300-day window.
- Pages forward by *actual returned record count*, with safeguards for repeated pages and a 25-page cap.
- Searches for Wellington Region before falling back to Wellington city. If it falls back, logs a prominent warning.
- Logs the numeric location ID, date window, page count, raw API records, API reported total, and indexed event-date count.
- Keeps the existing API credential secret handling, other source readers, GitHub Actions schedule, source settings and all other UI features.

## Install in GitHub

1. Extract `welly_events_v1_7_2_eventfinda_update.zip`.
2. Upload the files under `WellyOddities/` into that *existing* directory in your GitHub repository, replacing matching files. The `public/` folder may be uploaded too, but GitHub Actions rebuilds it on each run.
3. Commit to `main` and run **Actions → Refresh and publish Welly Oddities → Run workflow**.
4. Open the run, expand **Refresh the public source index**, and find `Eventfinda API:` in the log.

Example (fake numbers):

```
Eventfinda API location: Wellington Region (ID 77)
Eventfinda API: location ID 77, range 2026-10-26 to 2027-08-22, 4 page(s), 200 raw records, API reported total=200, 200 records with top-level dates, 196 retained event dates (5 unknown locations), from ... to ...
```

If `raw records` is high but `retained event dates` is low, we should inspect the date/venue structure and filtering. If `raw records` itself is about 61, we need to check the API's location and response `total` before assuming hundreds are available under the free API.

**Live API results have not been verified with your private account.** Unit tests use simulated responses, and the actual number will only be known after running on GitHub.

Keep the API password exclusively in GitHub Secrets. If you previously shared that password, rotate it via Eventfinda and update the repository secret.
