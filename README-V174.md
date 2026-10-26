# Welly Events v1.7.4 — Eventfinda page-cap fix

The GitHub log showed that Eventfinda was returning about 568 records in 60 pages, but the old script raised an exception at the page cap. This discarded the whole new Eventfinda batch, leaving the old 61-entry cache in place.

**What's changed**

- A page budget is no longer treated as an indexing failure. Partial batches are published and retained.
- Each refresh collects up to **90 pages** (configurable with `WELLY_EVENTFINDA_PAGES_PER_RUN`, range 1–300). Eventfinda's free API was returning roughly 6–10 records per page, even when `rows=100` was requested.
- The next refresh resumes at the saved offset. Previously retrieved events are merged and deduplicated; once the end is reached, the source is marked `indexed` and the cursor resets.
- Source cards display `partial` and the next offset while the catalogue is still being collected. The terminal logs `Eventfinda catalogue PARTIAL` rather than `Failed eventfinda` when only the budget was hit.
- All earlier APIs, HTTP headers and interface features are preserved.

**GitHub installation**: extract the smaller update ZIP into your repository, preserving `WellyOddities/` and `public/` paths, commit to `main`, and run the existing **Refresh and publish Welly Oddities** Action. Your API username and password stay in GitHub Secrets. No `.github` change is necessary.

**Expected log**: `Eventfinda API: ... complete=False, next_offset=...` followed by `Eventfinda catalogue PARTIAL...`. A following refresh should start with `offset=<previous next_offset>`. Eventually it will log `complete=True, next_offset=0`. This can require several runs if the catalogue is large. We have tested the behaviour with simulated responses, not your live API.

**Important limitations**: the offset is based on a dynamic API result list, so newly inserted events during successive runs can shift positions. Re-running a full refresh after finishing the catalogue mitigates this. Use only API request volumes allowed by your Eventfinda free-tier terms.
