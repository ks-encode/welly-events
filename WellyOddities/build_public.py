"""Build a static, phone-friendly GitHub Pages site using the latest cached index.

The published site reads events-feed.json (no server or API required on visitors' devices).
The app's local Python server remains available as before.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent / 'public'
PUBLIC.mkdir(exist_ok=True)

import server

# Sanitise all records, including stale hand-curated seed and old cache entries.
feed = {
    'events': server.unique_events([v for e in server.DATA.get('events', []) if (v := server.local_record(e))]),
    'sources': server.SOURCES,
    'source_status': server.DATA.get('source_status', {}),
    'updated': server.DATA.get('updated', server.SEED['updated']),
    'app_version': server.APP_VERSION,
}
(PUBLIC/'events-feed.json').write_text(json.dumps(feed, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
html = (ROOT/'index.html').read_text('utf-8')

# Keep a helpful fallback if the JSON fetch fails; all current feed data comes
# from the published JSON on successful page load, not the embedded snapshot.
fallback = json.dumps(feed, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
html, count = re.subn(r'(<script id="initial-data" type="application/json">).*?(</script>)',
                      lambda m: m.group(1)+fallback+m.group(2), html, count=1, flags=re.S)
assert count == 1
html = html.replace('const APP_VERSION=\'1.3.0\';', "const APP_VERSION='1.4-web';")
html = html.replace("const ready=data.updated?.slice(0,10)||'2026-10-13';const live=state.hasServer;", "const ready=data.updated?.slice(0,10)||'unknown';const live=state.hasPublishedFeed;")
start = html.index(" $('data-note').innerHTML=live?")
stop = html.index("\n $('scanstatus').textContent=", start)
html = html[:start] + """ $('data-note').innerHTML=live
  ? `<b>Shared event calendar · Last index attempt: ${esc(ready)}.</b> A scheduled update checks public event websites daily. Some sources may fail or have incomplete listings; check the individual source status and confirm event details with organisers.`
  : `<b>Saved snapshot · ${esc(ready)}.</b> Live feed unavailable right now. This device is showing the last data built into the app, which could be out of date.`;""" + html[stop:]
html = html.replace("$('scanstatus').textContent=state.refreshing?'Checking websites…':'';", "$('scanstatus').textContent=state.refreshing?'Loading latest published feed…':'';")
html = html.replace("$('refreshbtn').textContent=state.refreshing?'◌ Updating…':'↻  Refresh events';", "$('refreshbtn').textContent=state.refreshing?'◌ Reloading…':'↻  Reload published feed';")
html = html.replace("<b>How indexing works</b><br>The initial 182 records are a date-stamped, manually checked snapshot. With the Python server running, “Refresh events” attempts to read public listings from the sources you've enabled.",
                    "<b>How indexing works</b><br>The published feed is rebuilt by a scheduled GitHub job. 'Reload published feed' downloads the latest posted data; it does not crawl event sites from your phone. The scraper attempts to read public listings from the sources.")
html = html.replace("<b>Use the app with or without Python</b><br>Open this HTML file directly for the 13 October 2026 snapshot and all browsing filters. For live fetching, install Python 3, run START-WINDOWS.bat or START-MAC-LINUX.sh from the project folder, then open localhost:8765. No account or API key is needed.",
                    "<b>Shareable mobile website</b><br>Anyone with this site's public URL can use the calendar on a phone or computer. The server-side indexer checks sites on a schedule and publishes a shared dated feed; 'Reload published feed' only downloads that feed. Your source exclusions and saved events are stored separately in each visitor's browser.")
html = html.replace("Hand-checked opening snapshot · <span id=\"railupdated\">13 Oct 2026</span>", "Published event feed · <span id=\"railupdated\">Loading…</span>")
html = html.replace("<meta name=\"theme-color\" content=\"#10171b\">", "<meta name=\"theme-color\" content=\"#10171b\"><meta name=\"apple-mobile-web-app-capable\" content=\"yes\"><link rel=\"manifest\" href=\"./manifest.webmanifest\"><link rel=\"apple-touch-icon\" href=\"./icon-192.png\">")

start = html.index('async function detectServer()')
stop = html.index("document.addEventListener('click'", start)
html = html[:start] + """async function loadPublishedFeed(){
 if(state.refreshing)return;
 state.refreshing=true;render();
 try{
   const r=await fetch('./events-feed.json?cache='+Date.now(),{cache:'no-store'});
   if(!r.ok)throw Error('The published feed could not be loaded (HTTP '+r.status+').');
   const d=await r.json();
   if(!Array.isArray(d.events)||!Array.isArray(d.sources))throw Error('Invalid feed format');
   data=acceptData(d);state.hasPublishedFeed=true;
   $('scanstatus').textContent='';
 }catch(e){
   state.hasPublishedFeed=false;
   $('scanstatus').textContent='Feed unavailable — showing bundled data';
 }finally{state.refreshing=false;render();}
}
async function refresh(){return loadPublishedFeed();}
""" + html[stop:]
html = html.replace("render();if(location.protocol.startsWith('http'))detectServer();", "render();if(location.protocol.startsWith('http'))loadPublishedFeed();")
html = html.replace("<h2>Your saved events</h2><p>Star events to keep them on this device.</p>", "<h2>Your saved events</h2><p>Star events to keep them on this device. Saved events are not shared between phones.</p>")
# Prevent erroneous claim "the starting listings were checked" on published page.
html = html.replace("The starting listings were checked 13 Oct 2026. Run the included local server to fetch new events from public websites. Some sources require special access.",
                    "A published events feed loads automatically. Use Reload published feed to check the latest shared update. Some sources may have incomplete listings.")
(PUBLIC/'index.html').write_text(html, encoding='utf-8')
(PUBLIC/'.nojekyll').write_text('',encoding='utf-8')
print(f'Published {len(feed["events"])} events, {len(feed["sources"])} sources; last indexed {feed["updated"]}.')
