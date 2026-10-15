# Welly Oddities — Wellington event index

A date-first local web app for finding upcoming and unusual events in Wellington, the Hutt Valley, Porirua, Kāpiti and Wairarapa.

## What you get

- **An expanded dated event snapshot** from 13 October 2026, sorted into one timeline.
- **32 known event websites**, including **Engineering New Zealand (Wellington)**. The source switches let you exclude websites completely from your calendar.
- Filters for **Engineering, Science, Heritage, Outdoors, Workshops, Arts, Music, Social, Community**; 7/14/30/60/120 days; region; free events; and online events.
- Star/save events, open organiser links, and download an `.ics` calendar invitation for each.
- The interface works on desktop and mobile.
- An optional Python local service attempts to **update dated listings from public websites**. Sources with no readable event data, errors or login restrictions are labelled accurately rather than silently counted as complete.

## Option 1: Browse immediately (no installation)

Double-click **index.html**. All the filtering and saved-event features work immediately, but the dated event dataset will remain the **13 October 2026 snapshot**. Saved events and preferences use your browser's local storage.

## Option 2: Refresh listings (recommended for ongoing use)

The local service needs **Python 3.10+** and an Internet connection. It uses two standard Python packages: `requests` and `beautifulsoup4`.

### Windows

1. Install Python 3 if you do not have it: https://www.python.org/downloads/ (enable **Add Python to PATH**).
2. Double-click **START-WINDOWS.bat**. It installs the packages and starts the local app.
3. Your browser opens `http://127.0.0.1:8765` (or enter that URL yourself).
4. Click **Refresh events**. It checks the websites you've enabled. Refresh can take a while, depending on the sites and your connection.
5. Leave the terminal window open while using the live refresh function. The static calendar still works without it.

### macOS / Linux

In Terminal, navigate to the project folder and run:

```bash
python3 -m pip install -r requirements.txt
python3 server.py
```

Then go to http://127.0.0.1:8765. You may need to create a Python virtual environment depending on your system Python installation.

## How indexing works (important limitations)

This is not a commercial event API. Many ticketing sites do **not** permit simple anonymous programmatic access to their full databases, and some are heavily JavaScript-driven. For that reason, **the program cannot guarantee that every event from all 31 websites is included**.

The updater includes dedicated parsers for:

- **Glean Report** — public science and humanities talks.
- **Engineering New Zealand** — Wellington-filtered event pages, including pagination and its second page.
- **Wellington Heritage Festival** — dated festival cards and multiple displayed event sessions.
- **Hutt City Events** — dated council event cards.
- **The Fringe Bar** — its public Eventfinda-powered gig guide, including page 2, short multi-day runs, and explicitly weekly recurring comedy nights.

For the remaining websites, it tries standard structured `schema.org/Event` data and recognisable public event cards and detail pages. Facebook and other login-protected services will often not work. A source is marked as **indexed**, **not indexed**, **no readable events**, or **failed**. An empty scan does not falsely clear a valid older snapshot. Public websites change HTML often; some parsers may need maintenance.

The app **does not use Google/Bing searches as event entries**, and it never invents event dates. The provided snapshot has organiser pages linked wherever practical. Some snapshot records link to an organiser's main event listing rather than their individual ticket page.

**Attendance, location, pricing, cancellations and whether events are fully booked must always be confirmed on the linked organiser's site.** A `Free only` filter only includes events explicitly listed as free, not ones with unspecified pricing or koha.

## Included files

- `index.html` — the app, with embedded date-stamped snapshot, works offline.
- `server.py` — local web server and optional web crawlers.
- `events.json` — editable initial snapshot, dated 13 October 2026.
- `sources.json` — websites registry.
- `index_cache.json` — generated after your first refresh, stores the most recent results.
- `START-WINDOWS.bat` and `START-MAC-LINUX.sh` — launchers.
- `build_html.py`, `make_seed.py` — developer tools for regenerating the offline snapshot.
- `test_indexers.py` — parser sanity tests; run `python test_indexers.py`.

The server binds only to **127.0.0.1**, not the public internet. Preferences and saved event IDs are kept locally in your browser. There is no paid service or API key.

## Sources

The initial hand-checked data came from Glean Report, Engineering New Zealand, The Fringe Bar, Wellington Heritage Festival, Hutt City Council, BATS and Pyramid Club (checked on 13 October 2026). For ongoing accuracy, check each organiser's site or use Refresh with the local server.

## Adding The Fringe Bar (13 October 2026)

The Fringe Bar is a separate source from the NZ Fringe Festival (which is a different organiser). The source list now includes The Fringe Bar at 26 Allen Street. A dedicated public-listing parser attempts to index comedy, cabaret, drag and burlesque dates and ticket links; it does not require an Eventfinda account. Long date ranges are not assumed to run every day.

**Updating an existing installation:** close the old server window, overwrite the extracted app files with this new version (keep your `index_cache.json` if you have one), then restart `START-WINDOWS.bat`. The app merges seed events for newly added sources into existing caches. The Fringe Bar appears in Manage Sources and you can refresh to get current listings.


## Location filtering fix (version 1.2)

This update fixes a bug in which missing or unfamiliar event locations defaulted to
Wellington. Non-Wellington cities such as Auckland, Hamilton, Christchurch and
Dunedin are rejected when identified in the venue, location metadata, or at the
end of an event title/URL. Unknown-location events from national aggregators are
excluded rather than silently classified as Wellington. Local organisers whose
event cards omit addresses are still accepted, unless an out-of-region location
is explicit. Online events may still appear and can be hidden with **Hide online**.

The server rechecks existing cached events on startup, so you **can keep** your
`index_cache.json`: previously saved out-of-region entries will be removed from
the displayed results without erasing the rest of the cache. The source filter
label now reads "Wellington region + online" rather than "Everywhere".

If a venue has no locality and the source is national, the app may now omit a
legitimate local event: this favours avoiding false Wellington positives.

## v1.3 (October 2026): structured locations and startup verification

Ticketing platforms such as Eventbrite sometimes embed a `schema.org/PostalAddress`
object instead of text in their event metadata. Previously the app printed the
object literally (`{'addressLocality': 'Auckland', ...}`), and some older copies
of the updater could still admit out-of-region results. v1.3 parses structured
addresses into a readable venue and rejects out-of-region physical events,
including those marked as hybrid/online. It also removes leaked dictionary
text and revalidates old event records when opening the cache.

**Check the version**: the app's sidebar shows `v1.3.0`, and the notice at the
top confirms `Local indexer v1.3.0 connected.` If it instead says **Indexer
version mismatch**, close every previous app command window and launch the new
`START-WINDOWS.bat` from the extracted v1.3 folder; the browser might still be
connected to an older server listening on port 8765. Refresh the browser with
Ctrl+F5. Keep `index_cache.json` to preserve your indexed data.

The browser also filters known out-of-region cities before displaying results,
so old cached records are hidden even when their source was updated earlier.
