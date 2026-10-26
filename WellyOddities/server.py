"""Welly Oddities: local event indexer and web server.

Run: python server.py
Requires: requests, beautifulsoup4 (pip install -r requirements.txt)
Eventfinda API credentials are read only from environment variables; never embed them in files.
"""
from __future__ import annotations
import ast
import hashlib
import xml.etree.ElementTree as ET
import json
import logging
import os
import re
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit('Install dependencies first: python -m pip install -r requirements.txt')

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / 'sources.json').read_text('utf-8'))
SEED = json.loads((ROOT / 'events.json').read_text('utf-8'))
CACHE = ROOT / 'index_cache.json'
LOCK = threading.Lock()
STATUS = {'running': False, 'started': None, 'ended': None, 'results': {}}
PORT = 8765
APP_VERSION = '1.7.3'
TZ_DAY = lambda: datetime.now(ZoneInfo("Pacific/Auckland")).date()
MONTHS = {m.lower(): i for i, m in enumerate(['','January','February','March','April','May','June','July','August','September','October','November','December']) if m}
MONTHS.update({m[:3].lower(): v for m,v in list(MONTHS.items())})
DATE_RE = re.compile(r'(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+(20\d{2}))?', re.I)
TIME_RE = re.compile(r'(?<!\d)(\d{1,2})[:.](\d\d)\s*(am|pm)?\b', re.I)
ISO_RE = re.compile(r'20\d\d-\d\d-\d\d')
# The feed is WELLINGTON ONLY. National event sources regularly include events
# in other cities, even when their listing URL appears to be Wellington-filtered.
LOCAL_AREAS = {'Wellington', 'Lower Hutt', 'Upper Hutt', 'Porirua', 'Kāpiti', 'Wairarapa'}
NATIONAL_SOURCES = {'eventfinda', 'humanitix', 'meetup', 'eventbrite', 'allevents', 'whatsfree', 'natlib'}
# These organisers publish substantially local listings; venue-less entries can
# be accepted, but an explicit out-of-region venue still overrides this hint.
LOCAL_SOURCES = {'glean', 'pyramid', 'bats', 'fringebar', 'heritage', 'hutt',
                 'upper', 'kapiti', 'porirua', 'wellingtonnz', 'museums',
                 'vuw', 'rsonz', 'was', 'tepapa', 'wcl', 'zealandia',
                 'fringe', 'performance', 'artclub', 'wtmc', 'utr', 'image',
                 'engineering'}
NONLOCAL_CITIES = ('auckland', 'north shore', 'manukau', 'papakura',
                   'hamilton', 'tauranga', 'rotorua', 'taupō', 'taupo',
                   'new plymouth', 'whanganui', 'wanganui', 'palmerston north',
                   'napier', 'hastings', 'gisborne', 'nelson', 'blenheim',
                   'christchurch', 'dunedin', 'invercargill', 'queenstown',
                   'wānaka', 'wanaka', 'timaru', 'ashburton', 'whangārei',
                   'whangarei', 'kerikeri', 'canterbury', 'otago', 'waikato',
                   'southland', 'northland', 'bay of plenty')
NONLOCAL_RE = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(c) for c in NONLOCAL_CITIES) + r')(?!\w)', re.I)
NONLOCAL_TITLE_SUFFIX_RE = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(c) for c in NONLOCAL_CITIES) + r')(?:\s*,?\s*(?:NZ|New Zealand))?\s*$', re.I)
# Compare a conventional HTML request header set with the original identifiable
# indexer headers. Never rotate identities or proxies; honour website restrictions.
# Set WELLY_HTTP_PROFILE=indexer to reproduce the old behaviour for debugging.
INDEXER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; WellyOdditiesPersonalIndexer/1.0; +local-app)',
    'Accept-Language': 'en-NZ,en;q=0.9',
}
BROWSER_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/140.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-NZ,en;q=0.9',
}
def html_request_headers():
    profile = os.environ.get('WELLY_HTTP_PROFILE', 'browser').strip().lower()
    return (INDEXER_HEADERS if profile == 'indexer' else BROWSER_HEADERS).copy()

HEADERS = html_request_headers()
log = logging.getLogger('welly')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

def normspace(s):
    return re.sub(r'\s+',' ',str(s or '')).strip()

def uid(source,date,title):
    return hashlib.sha1((source+date+title).lower().encode()).hexdigest()[:16]

def infer_category(title, fallback='Community'):
    t=title.lower()
    groups=[('Engineering',r'engineer|robot|technolog|electr|energy|battery|rail|grid|transport|comput|program|ai |machine learn|cyber|industry|design|mathematic|manufactur'),
            ('Heritage',r'heritage|historic|history|archive|cemetery|lighthouse|walking tour|oldest|architecture|building tour'),
            ('Science',r'science|astronom|space|star|physics|ecolog|biology|conserv|planet|climate|research|fossil|geolog|ocean|telescope|botan|genetic|lecture|seminar|species|peripatus'),
            ('Outdoors',r'tramp|hike|field trip|garden|nature walk|guided walk|trail|outdoor|bird|forest|kayak'),
            ('Workshops',r'workshop|class|course|training|learning|make your own|hands.on|craft|intro to|beginner'),
            ('Arts',r'theatre|theater|improv|comedy|cabaret|burlesque|drag king|drag queen|circus|performance|installation|film|screening|stage|poetry|book launch'),
            ('Music',r'concert|jazz|gig|tape night|band|sonic|music|sound|vinyl'),
            ('Social',r'network|meetup|espresso|coffee|quiz|social|ball |game night')]
    for kind,pat in groups:
        if re.search(pat,t): return kind
    return fallback

def format_jsonld_address(address):
    """Return human-readable address components, never a stringified dict."""
    if isinstance(address, list):
        return ', '.join(p for x in address if (p:=format_jsonld_address(x)))
    if isinstance(address, str):
        return normspace(address)
    if not isinstance(address, dict):
        return ''
    parts = []
    for key in ('name','streetAddress','addressLocality','addressRegion','postalCode','addressCountry'):
        value = address.get(key,'')
        if isinstance(value,dict):
            value = value.get('name') or value.get('@id') or ''
        if not isinstance(value,(str,int)):
            continue
        value = normspace(value)
        if value and not any(value.lower()==p.lower() for p in parts):
            parts.append(value)
    return ', '.join(parts)


def jsonld_location_text(loc):
    """Extract physical location first, even from hybrid events.

    Returning the real physical address is important: a remote venue must not
    disappear behind an OnlineEventAttendanceMode flag.
    """
    if isinstance(loc,list):
        pieces=[jsonld_location_text(x) for x in loc]
        physical=[p for p in pieces if p and not re.search(r'^(?:online|virtual)$',p,re.I)]
        return ', '.join(dict.fromkeys(physical)) if physical else (pieces[0] if pieces else '')
    if isinstance(loc,str):
        return normspace(loc)
    if not isinstance(loc,dict):
        return ''
    typ=loc.get('@type','')
    if (isinstance(typ,str) and 'VirtualLocation' in typ and
            not loc.get('address') and not loc.get('addressLocality')):
        return 'Online'
    name=normspace(loc.get('name',''))
    addr=format_jsonld_address(loc.get('address',loc))
    if not addr:
        addr=format_jsonld_address(loc)
    if not name:return addr
    if not addr or addr.lower() in name.lower():return name
    return name + ', ' + addr


def clean_legacy_venue(venue):
    """Convert the literal Python dicts saved by older JSON-LD scrapers."""
    if isinstance(venue,(dict,list)):
        return jsonld_location_text(venue)
    venue=normspace(venue)
    # Old code concatenated the place name with str(PostalAddress dict).
    matches=list(re.finditer(r'\{[^{}]*\}',venue))
    for m in reversed(matches):
        try:obj=ast.literal_eval(m.group())
        except (ValueError,SyntaxError):continue
        if not isinstance(obj,dict) or not any(k in obj for k in ('addressLocality','streetAddress','addressRegion')):
            continue
        pretty=format_jsonld_address(obj)
        prefix=normspace(venue[:m.start()].rstrip(' ,'))
        suffix=normspace(venue[m.end():].lstrip(' ,'))
        venue=', '.join(part for part in (prefix,pretty,suffix) if part)
    return venue

def area_from(text):
    """Return a location only when it is actually identified.

    An unknown place must NOT default to Wellington. This was the bug that
    let Auckland, Christchurch and other out-of-region events into the feed.
    """
    t=(text or '').lower()
    if NONLOCAL_RE.search(t): return 'Outside region'
    if 'online' in t or 'webinar' in t or 'zoom' in t: return 'Online'
    if any(x in t for x in ['lower hutt','petone','eastbourne','wainuiomata','hutt central','naenae','taita','stokes valley']): return 'Lower Hutt'
    if any(x in t for x in ['upper hutt','trentham','silverstream','pinehaven','ebdentown']): return 'Upper Hutt'
    if 'porirua' in t or 'pātaka' in t or 'tītahi bay' in t or 'titahi bay' in t or 'plimmerton' in t: return 'Porirua'
    if any(x in t for x in ['kāpiti','kapiti','waikanae','paraparaumu','paekākāriki','raumati','otaki','ōtaki']): return 'Kāpiti'
    if any(x in t for x in ['wairarapa','martinborough','featherston','greytown','masterton']): return 'Wairarapa'
    if any(x in t for x in ['wellington','pōneke','te aro','newtown','kelburn','karori','thorndon','miramar','johnsonville','newlands','hutt central','tawa','brooklyn','island bay','kilbirnie','mount cook','mount victoria','thorndon','mt victoria','mt cook','wadestown','hataitai']): return 'Wellington'
    return ''


def location_for_event(source, title, venue='', area='', online=False, url=''):
    """Reject identifiable out-of-region events before considering online/local hints."""
    venue=clean_legacy_venue(venue)
    area=normspace(area)
    if area=='Outside region' or NONLOCAL_RE.search(venue) or NONLOCAL_RE.search(area):
        return None
    path=urlparse(url or '').path.rstrip('/').lower()
    slug=path.split('/')[-1] if path else ''
    # Out-of-region city at the end of detail URL/title is a strong signal.
    if slug and NONLOCAL_RE.fullmatch(slug.replace('-', ' ')):
        return None
    if (not area_from(venue) in LOCAL_AREAS) and NONLOCAL_TITLE_SUFFIX_RE.search(title or ''):
        return None
    # HTML from ticket sites may identify an Auckland *hybrid* event as online.
    # Only genuinely location-less remote events can be treated as online.
    recognised=area_from(venue) if venue else ''
    if recognised=='Outside region':return None
    if recognised in LOCAL_AREAS:return recognised
    if online or area=='Online' or recognised=='Online':return 'Online'
    if area in LOCAL_AREAS and source not in NATIONAL_SOURCES:return area
    url_areas={'wellington':'Wellington','lower-hutt':'Lower Hutt',
               'upper-hutt':'Upper Hutt','porirua':'Porirua',
               'kapiti':'Kāpiti','kāpiti':'Kāpiti','wairarapa':'Wairarapa',
               'petone':'Lower Hutt','paraparaumu':'Kāpiti'}
    if slug in url_areas:return url_areas[slug]
    if source in LOCAL_SOURCES:
        return {'hutt':'Lower Hutt','upper':'Upper Hutt','kapiti':'Kāpiti',
                'porirua':'Porirua'}.get(source,'Wellington')
    return 'Unknown'


def local_record(e):
    """Revalidate cached events and repair venues saved by older app versions."""
    source=e.get('source','')
    venue=clean_legacy_venue(e.get('venue',''))
    area=location_for_event(source,e.get('title',''),venue,
                            e.get('area',''),e.get('online',False),e.get('url',''))
    if not area:return None
    e=dict(e)
    e['venue']=venue[:150]
    e['area']=area
    e['online']=(area=='Online')
    return e

def fmt_date(day,month,year=None):
    monthno=MONTHS.get(month.lower())
    if not monthno: return None
    now=TZ_DAY()
    m_year_explicit = bool(year)
    year=int(year) if year else now.year
    try: dt=datetime(year,monthno,int(day)).date()
    except ValueError: return None
    # Events listed near New Year can refer to the following year.
    if dt < now-timedelta(days=35) and not m_year_explicit:
        dt=dt.replace(year=dt.year+1)
    return dt.isoformat()

def parse_date(s):
    s=normspace(s)
    iso=ISO_RE.search(s)
    if iso:return iso.group()
    m=DATE_RE.search(s)
    if not m:return None
    return fmt_date(*m.groups())

def parse_time(s):
    s=normspace(s)
    m=TIME_RE.search(s)
    if m:
        h,minute,ampm=m.groups();h=int(h)
    else:
        m=re.search(r'(?<!\d)(\d{1,2})\s*(am|pm)\b',s,re.I)
        if not m:return ''
        h,ampm=m.groups();h=int(h);minute='00'
    if ampm:
        if ampm.lower()=='pm' and h!=12:h+=12
        if ampm.lower()=='am' and h==12:h=0
    if h>23:return ''
    return f'{h:02}:{minute}'

def good_date(s):
    try:
        d=datetime.strptime(s,'%Y-%m-%d').date()
        return TZ_DAY()-timedelta(days=1)<=d<=TZ_DAY()+timedelta(days=300)
    except Exception:return False

def make_event(source,date,title,*,url=None,time='',venue='',price='',area='',online=False,end='',description=''):
    title=normspace(re.sub(r'\*(?:WGTN|ONLINE|NEW)\*','',title,flags=re.I))
    title=re.sub(r'^(?:NEW|CANCELLED)\s*', '', title,flags=re.I)
    if len(title)<5 or len(title)>230 or not good_date(date):return None
    source_url=next((x['url'] for x in SOURCES if x['id']==source),'')
    event_url=url or source_url
    venue=clean_legacy_venue(venue)
    place=location_for_event(source,title,venue,area,online,event_url)
    if not place: return None
    return dict(id=uid(source,date,title),source=source,date=date,title=title,type=infer_category(title,next((x['group'] for x in SOURCES if x['id']==source),'Community')),time=time,venue=normspace(venue)[:150],area=place,url=event_url,price=price,online=(place=='Online'),end=end,description=description[:400],origin='live index')

def request_soup(session,url):
    response=session.get(url,headers=HEADERS,timeout=14,allow_redirects=True)
    code=getattr(response, 'status_code', 200)
    if code >= 400:
        # Log a useful diagnostic without storing response bodies or query tokens.
        actual=urlparse(getattr(response, 'url', url))
        headers=getattr(response, 'headers', {}) or {}
        hops=len(getattr(response, 'history', []) or [])
        server_hint='Cloudflare' if ('cf-ray' in headers or 'cf-mitigated' in headers) else 'unspecified server'
        content_type=headers.get('Content-Type', '?').split(';')[0]
        raise requests.HTTPError(
            f'HTTP {code} from {actual.netloc}{actual.path[:80]} '
            f'({hops} redirects; {server_hint}; type={content_type})', response=response)
    response.raise_for_status()
    if len(response.content)>4_000_000:raise ValueError('Page too large')
    headers=getattr(response, 'headers', {}) or {}
    if headers.get('cf-mitigated', '').lower() == 'challenge':
        raise RuntimeError('Cloudflare challenge instead of event HTML')
    # Some sites return XML for feed URLs. Dedicated feed readers parse those as XML.
    return BeautifulSoup(response.content,'html.parser')

def scrape_glean(session,src):
    soup=request_soup(session,src['url']); out=[]
    for tr in soup.find_all('tr'):
        tds=tr.find_all('td',recursive=False)
        if len(tds)<2:continue
        d=parse_date(tds[0].get_text(' ',strip=True))
        if not d:continue
        time=parse_time(tds[0].get_text(' ',strip=True))
        main=tds[1]
        a=next((a for a in main.find_all('a',href=True) if 'more information' not in a.get_text(' ',strip=True).lower() and 'ics' not in a.get_text(' ',strip=True).lower() and len(a.get_text(' ',strip=True))>10),None)
        if not a:continue
        name=a.get_text(' ',strip=True)
        alltext=main.get_text(' ',strip=True)
        online=('ONLINE' in name.upper() and 'WGTN' not in name.upper())
        venue=''
        match=re.search(r'\bat\s+(.+?)(?:\s+More information|\s+Add To Calendar|$)',alltext,re.I)
        if match:venue=match.group(1)
        href=next((urljoin(src['url'],a['href']) for a in main.select('a[href]') if 'more information' in a.get_text(' ',strip=True).lower()), urljoin(src['url'],a['href']))
        if 'cancelled' in alltext.lower():continue
        ev=make_event(src['id'],d,name,url=href,time=time,venue=venue,online=online)
        if ev:out.append(ev)
    return out

def scrape_engineering(session,src):
    out=[];seen=set()
    # Explicitly follow Wellington location pagination; this catches page 2 too.
    for p in range(1,8):
        url=src['url']+ ('&p='+str(p) if p>1 else '')
        soup=request_soup(session,url)
        before=len(out)
        for a in soup.select('a[href*="/courses-events/event/"] , a[href*="/courses-events/event-template/"]'):
            href=urljoin(url,a.get('href',''))
            # The same link often appears on both a price and a title.
            text=normspace(a.get_text(' ',strip=True))
            m=re.search(r'(\d{1,2})\s+([a-z]{3})\s+(20\d\d),?\s+([\d:.]+\s*[ap]m)\s+(.+)',text,re.I)
            if not m or href in seen:continue
            date=fmt_date(m.group(1),m.group(2),m.group(3));time=parse_time(m.group(4))
            title=m.group(5)
            venue=''
            # Try to separate venue text from event name without inventing it.
            for suffix in ['Engineering New Zealand Wellington Office, Wellington','Engineering New Zealand, Wellington','Tākina Wellington Convention and Exhibition Centre, Wellington','Massey University - Wellington Campus, Wellington','Harbourside Function Centre, Wellington','Smith the Grocer Cafe, Wellington','AECOM Wellington, Wellington','JMD Railtech - Upper Hutt, Wellington','Tonkin and Taylor - Wellington, Wellington']:
                if title.lower().endswith(suffix.lower()):title=title[:-len(suffix)].strip();venue=suffix;break
            # price sometimes comes from nearest listing card text
            wrap=a.parent
            for _ in range(3):
                if wrap and wrap.parent and len(wrap.get_text(' ',strip=True))<500:wrap=wrap.parent
            context=normspace(wrap.get_text(' ',strip=True)) if wrap else ''
            price=''
            pm=re.search(r'(?:Free|\$\d+(?:\.\d\d)?)',context,re.I)
            if pm:price=pm.group()
            ev=make_event(src['id'],date,title,url=href,time=time,venue=venue,price=price)
            if ev:
                seen.add(href);out.append(ev)
        if len(out)==before:break
    return out

def jsonld_event_objects(obj):
    if isinstance(obj,list):
        for x in obj:yield from jsonld_event_objects(x)
    elif isinstance(obj,dict):
        if '@graph' in obj:yield from jsonld_event_objects(obj['@graph'])
        types=obj.get('@type',[])
        if isinstance(types,str):types=[types]
        if any('Event' in str(t) or str(t).lower() in ('course','festival','exhibitionevent') for t in types):yield obj
        if 'itemListElement' in obj:yield from jsonld_event_objects(obj['itemListElement'])
        if 'item' in obj and isinstance(obj['item'],dict):yield from jsonld_event_objects(obj['item'])

def parse_jsonld(soup,src,pageurl):
    out=[]
    for tag in soup.find_all('script',type=lambda x: x and 'ld+json' in x):
        try:obj=json.loads(tag.string or tag.get_text())
        except Exception:continue
        for e in jsonld_event_objects(obj):
            dt=e.get('startDate','')
            if isinstance(dt,dict):dt=dt.get('@value','')
            date=parse_date(str(dt));time=parse_time(str(dt))
            if not date:continue
            loc=e.get('location',{})
            venue=jsonld_location_text(loc)
            virt=bool(e.get('eventAttendanceMode','').endswith('OnlineEventAttendanceMode')) if isinstance(e.get('eventAttendanceMode',''),str) else False
            online=virt or (venue.lower() in ('online','virtual','webinar'))
            title=e.get('name','')
            if not isinstance(title,str):continue
            offers=e.get('offers',{});
            if isinstance(offers,list):offers=offers[0] if offers else {}
            p=str(offers.get('price','')) if isinstance(offers,dict) else ''
            price=('Free' if p=='0' else ('$'+p if p else ''))
            end=parse_date(str(e.get('endDate',''))) or ''
            ev=make_event(src['id'],date,title,url=e.get('url') or pageurl,time=time,venue=venue,price=price,online=online,end=end,description=BeautifulSoup(str(e.get('description','')),'html.parser').get_text(' ',strip=True))
            if ev:out.append(ev)
    return out

def scrape_heritage(session,src):
    """Index the dated festival cards, including multiple dates where displayed."""
    soup=request_soup(session,src['url']);out=[];seen=set()
    weekday=re.compile(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+[A-Za-z]{3}',re.I)
    timeseq=re.compile(r'(?<!\d)\d{1,2}(?::\d{2})?\s*[ap]m\s*[-–]\s*\d{1,2}(?::\d{2})?\s*[ap]m',re.I)
    for a in soup.select('a[href*="/event/"]'):
        href=urljoin(src['url'],a.get('href',''))
        if not href.startswith('https://wellingtonheritagefestival.co.nz/event/') or href in seen:continue
        seen.add(href)
        raw=normspace(a.get_text(' ',strip=True))
        if not weekday.search(raw):
            for p in [a.parent,a.parent.parent if a.parent else None]:
                if p and len(p.get_text(' ',strip=True))<650 and weekday.search(p.get_text(' ',strip=True)):
                    raw=normspace(p.get_text(' ',strip=True));break
        dates=list(weekday.finditer(raw))
        if not dates:continue
        title=raw
        tm=timeseq.search(raw)
        if tm:title=raw[:tm.start()]
        elif dates:title=raw[:dates[0].start()]
        title=re.sub(r'^(?:Fully booked|Book early|Limited spots remaining|Filling up fast)\s+','',title,flags=re.I)
        if len(title)<5:continue
        for m in dates[:5]:
            date=parse_date(m.group())
            if not date:continue
            before=raw[max(0,m.start()-24):m.start()]
            time=parse_time(before)
            price='Free' if re.search(r'\bFree\b',raw) else ('Koha' if re.search(r'\bKoha\b',raw) else '')
            pm=re.search(r'\$\d+(?:\.\d+)?',raw)
            if pm:price=pm.group()
            # An explicitly sold-out event is not attendable. Leave it out.
            if re.search(r'fully booked',raw,re.I):continue
            ev=make_event(src['id'],date,title,url=href,time=time,price=price,area=area_from(raw))
            if ev:out.append(ev)
    return out

def scrape_hutt(session,src):
    """Hutt City's public homepage uses event titles and calendar dates in cards."""
    soup=request_soup(session,src['url']);out=[];seen=set()
    for a in soup.find_all('a',href=True):
        title=normspace(a.get_text(' ',strip=True))
        if not 5<=len(title)<=130 or title.lower() in ('more category events','read more','learn more'):continue
        href=urljoin(src['url'],a['href'])
        if not href.startswith('https://events.huttcity.govt.nz/'):continue
        for p in [a.parent,a.parent.parent if a.parent else None,a.parent.parent.parent if a.parent and a.parent.parent else None]:
            if not p:continue
            raw=normspace(p.get_text(' ',strip=True))
            if len(raw)>380:continue
            date=parse_date(raw)
            if not date:continue
            key=(date,title)
            if key in seen:break
            ev=make_event(src['id'],date,title,url=href,time=parse_time(raw),area='Lower Hutt')
            if ev:seen.add(key);out.append(ev)
            break
    return out

def fringe_date_span(raw):
    """Parse event date labels shown by Fringe Bar's Eventfinda listing widget.

    A short Friday–Saturday run yields two separate dated performances.
    Long series are never treated as happening every day.
    """
    raw=normspace(raw)
    matches=list(DATE_RE.finditer(raw))[:2]
    if not matches:return None,None
    dates=[]
    for m in matches:
        d=parse_date(m.group())
        if not d:return None,None
        dates.append(d)
    start=dates[0]
    end=dates[1] if len(dates)>1 else None
    if end and end<start:
        # Eventfinda commonly omits the year on the end of a date range.
        if not matches[1].group(3):
            try:end=datetime.fromisoformat(end).replace(year=int(start[:4])+1).date().isoformat()
            except ValueError:end=None
    return start,end


def scrape_fringebar(session,src):
    """Read the Fringe Bar's public Eventfinda-powered show listings.

    Separately inspect the homepage and paginated gig-guide pages: the latter
    include performances several months ahead. Event titles link to Eventfinda.
    """
    root='https://thefringebar.co.nz/'
    pages=[src['url'],urljoin(root,'page/2/?pageId=2'),
           urljoin(root,'event-finder-fringe-bar/'),
           urljoin(root,'event-finder-fringe-bar/?pageId=2')]
    out=[]
    succeeded=0
    for url in pages:
        try:soup=request_soup(session,url);succeeded+=1
        except Exception as ex:
            log.info('Fringe Bar page unavailable %s: %s',url,str(ex)[:100]);continue
        for a in soup.select('h2 a[href], h3 a[href], h4 a[href], h5 a[href]'):
            href=urljoin(url,a.get('href',''))
            if 'eventfinda.co.nz' not in urlparse(href).netloc.lower():continue
            title=normspace(a.get_text(' ',strip=True))
            if not 5<=len(title)<=180:continue
            # Look for the smallest listing container that includes the heading
            # and its date, without picking up dates from neighbouring shows.
            context=''
            node=a.parent
            for _ in range(6):
                if not node or not getattr(node,'parent',None):break
                node=node.parent
                segment=normspace(node.get_text(' ',strip=True))
                if len(segment)>1000:break
                after=segment.split(title,1)[-1]
                if DATE_RE.search(after[:130]):
                    context=after[:220]
                    break
            if not context:continue
            # Date must be close to the heading; not a date in a review/description.
            m=DATE_RE.search(context)
            if not m or m.start()>90:continue
            # The date range is on its own line in the listings. Cut before the
            # prose description if there is one (and keep at most two date hits).
            nearby=context[m.start():m.start()+95]
            start,end=fringe_date_span(nearby)
            if not start:continue
            first=datetime.fromisoformat(start).date()
            last=datetime.fromisoformat(end).date() if end else first
            if last<first:continue
            span=(last-first).days
            dates=[]
            if span<=3:
                dates=[(first+timedelta(days=i)).isoformat() for i in range(span+1)]
            elif span>=14 and (title.lower().startswith('raw meat monday') or
                               title.lower()=='fringe bar comedy club'):
                # These two are explicitly weekly recurring shows.
                target=0 if 'monday' in title.lower() else 2  # Monday / Wednesday
                cursor=max(first,TZ_DAY())
                cursor+=timedelta(days=(target-cursor.weekday())%7)
                while cursor<=last and len(dates)<52:
                    dates.append(cursor.isoformat());cursor+=timedelta(days=7)
            else:
                # A multi-week booking period does not imply daily performances.
                dates=[start]
            for day in dates:
                ev=make_event(src['id'],day,title,url=href,
                              venue='The Fringe Bar, 26 Allen Street, Wellington',
                              area='Wellington',end=end if (span>3 and len(dates)==1) else '')
                if ev:out.append(ev)
    if not succeeded:raise RuntimeError('Could not open any Fringe Bar listing pages')
    return unique_events(out)


# Humanitix's main Wellington landing page currently exposes only FOUR featured
# event cards in server-rendered HTML. Category "trending" pages expose many more.
# These are public listing URLs, not Humanitix's organiser-only private API.
HUMANITIX_CATEGORIES = (
    'trending--businessandprofessional',
    'trending--healthandwellness',
    'trending--music',
)
HUMANITIX_CARD_PLACES = (
    'Wellington Central', 'Mount Victoria', 'Mount Cook', 'Oriental Bay',
    'Hutt Central', 'Lower Hutt', 'Upper Hutt', 'Wellington',
    'Porirua', 'Petone', 'Newtown', 'Te Aro', 'Kelburn', 'Thorndon',
    'Brooklyn', 'Karori', 'Island Bay', 'Johnsonville', 'Miramar',
    'Tawa', 'Pipitea', 'Kilbirnie', 'Roseneath', 'Khandallah',
    'Newlands', 'Elsdon', 'Woburn', 'Days Bay', 'Wainuiomata',
    'Waikanae', 'Paraparaumu', 'Paekākāriki', 'Featherston',
    'Greytown', 'Masterton', 'Hamilton Central', 'Auckland Central',
    'Christchurch Central', 'To be announced', 'Online',
)


def humanitix_card_event(src, raw, url):
    """Read dated, labelled cards from the marketplace's public HTML."""
    raw=normspace(raw)
    m=DATE_RE.search(raw)
    if not m:return None
    date=parse_date(m.group())
    if not date:return None
    # Cards can start with follower counts and weekday. Capture only after date.
    title=raw[m.end():].lstrip(' ,–-')
    # Drop the time and optional 'more times' badge preceding the event title.
    title=re.sub(r'^(?:\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b)\s*', '', title,flags=re.I)
    title=re.sub(r'^\+\d+\s+more\s+times?\s*', '',title,flags=re.I)
    if not title or title==raw:return None
    venue=''
    for loc in sorted(HUMANITIX_CARD_PLACES,key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(loc)+r'\s*$',title,re.I):
            title=re.sub(r'(?<!\w)'+re.escape(loc)+r'\s*$', '',title,flags=re.I).strip(' ,-')
            if loc.lower()!='to be announced':venue=loc
            break
    if len(title)<5:return None
    return make_event(src['id'],date,title,url=url,time=parse_time(raw),
                      venue=venue,online=(venue.lower()=='online'))


def scrape_humanitix(session, src):
    """Collect public Wellington category listings, not just four featured cards.

    The homepage only exposes a small 'Trending' carousel in its HTML. Additional
    public category pages typically expose dozens of dated anchors and may have
    a 'Next' pagination link. These are browsed separately and deduplicated by
    canonical event URL/date; detail JSON-LD enriches the card when available.
    """
    base=src['url'].rstrip('/')
    listing_urls=[base]+[base+'/'+p for p in HUMANITIX_CATEGORIES]
    queue=list(listing_urls)
    visited=set()
    items={}  # (detail url, event day) -> best known event
    detail_links=[]
    successful=0
    failures=[]

    def canonical(u):
        p=urlparse(u)
        return (p.scheme+'://'+p.netloc.lower()+p.path.rstrip('/')).lower()

    def retain(event):
        if not event:return
        k=(canonical(event['url']),event['date'])
        old=items.get(k)
        if old is None:
            items[k]=event
        else:
            # A detail page has a complete name, venue and perhaps description.
            richness=lambda e:(bool(e.get('venue')), bool(e.get('description')),len(e.get('venue','')))
            if richness(event)>richness(old):items[k]=event

    while queue and len(visited)<10:
        page=queue.pop(0)
        if page in visited:continue
        visited.add(page)
        try:
            soup=request_soup(session,page)
        except Exception as exc:
            failures.append(f'{page.split("/")[-1]}: {exc}')
            continue
        successful+=1
        for a in soup.find_all('a',href=True):
            url=urljoin(page,a['href']).split('#',1)[0]
            parsed=urlparse(url)
            if parsed.netloc.lower() in ('events.humanitix.com','www.events.humanitix.com') and parsed.path.strip('/'):
                # Query parameters often contain tracking; keep a canonical URL.
                url=parsed.scheme+'://'+parsed.netloc+parsed.path.rstrip('/')
                if url not in detail_links:detail_links.append(url)
                raw=normspace(a.get_text(' ',strip=True))
                if not DATE_RE.search(raw):
                    for ancestor in (a.parent, a.parent.parent if a.parent else None):
                        if ancestor is None:continue
                        candidate=normspace(ancestor.get_text(' ',strip=True))
                        if len(candidate)<400 and DATE_RE.search(candidate):
                            raw=candidate;break
                retain(humanitix_card_event(src,raw,url))
            # Follow explicit next-page links, but never wander to other cities.
            elif (parsed.netloc.lower() in ('humanitix.com','www.humanitix.com')
                  and parsed.path.rstrip('/') == urlparse(page).path.rstrip('/')
                  and parsed.query and re.search(r'\b(?:next|page\s*\d+)\b',a.get_text(' ',strip=True),re.I)
                  and url not in visited and url not in queue):
                queue.append(url)

    if not successful:
        raise RuntimeError('All Humanitix listing pages failed: '+('; '.join(failures)[:300]))

    # Detail JSON-LD is more reliable for venue, cost and multi-day metadata.
    # Cap requests so a single provider doesn't monopolise the refresh cycle.
    for url in detail_links[:30]:
        try:
            detail=request_soup(session,url)
            parsed=parse_jsonld(detail,src,url)
            if not parsed:
                parsed=parse_detail_dates(detail,src,url)
            for e in parsed:retain(e)
        except Exception:continue

    if failures:
        log.warning('Humanitix: %d of %d listing pages failed; showing partial index: %s',
                    len(failures),successful+len(failures),'; '.join(failures)[:200])
    log.info('Humanitix: %d listing pages checked, %d event links, %d dated events',
             successful,len(detail_links),len(items))
    return unique_events(list(items.values()))


# Eventfinda Developer API v2 uses HTTP Basic authentication. Credentials are
# supplied by GitHub Secrets, never bundled with public assets or cached events.
EVENTFINDA_API = 'https://api.eventfinda.co.nz/v2'


def _ef_collection(payload, singular, plural):
    """V2 responses vary between flat and nested XML-to-JSON forms."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    container = payload.get(plural, payload)
    if isinstance(container, list):
        return container
    if isinstance(container, dict):
        values = container.get(singular, container.get(plural, []))
        if isinstance(values, dict):
            return [values]
        if isinstance(values, list):
            return values
    values = payload.get(singular, [])
    return values if isinstance(values, list) else ([values] if isinstance(values, dict) else [])


def _ef_total(payload, plural):
    if not isinstance(payload, dict):
        return None
    obj = payload.get(plural, payload)
    if not isinstance(obj, dict):
        obj = payload
    # In Eventfinda collection responses `count` may be the number of
    # records in *this page* (e.g. 10), not the total number of matches.
    # Treat only an explicitly named total as the total; otherwise fetch
    # until an empty page or until the repeated-page guard detects trouble.
    for holder in (obj, payload.get('pagination', {}), payload.get('meta', {})):
        if not isinstance(holder, dict):
            continue
        for field in ('total', 'total_count', 'total_results'):
            try:
                value = int(holder[field])
                return value if value >= 0 else None
            except (KeyError, TypeError, ValueError):
                continue
    return None


def _ef_api_get(session, resource, user, password, params):
    url = EVENTFINDA_API + '/' + resource + '.json'
    # Never log user, password, Basic authorization header or full response.
    response = session.get(url, params=params, auth=(user, password),
                           headers={'Accept': 'application/json', 'User-Agent': HEADERS['User-Agent']},
                           timeout=18, allow_redirects=False)
    response.raise_for_status()
    if len(response.content) > 4_000_000:
        raise ValueError('Eventfinda API response too large')
    data = response.json()
    if not isinstance(data, (dict, list)):
        raise ValueError('Unexpected Eventfinda API response structure')
    if isinstance(data, dict) and (data.get('error') or data.get('errors')):
        raise ValueError('Eventfinda API returned an error response (check access tier and parameters)')
    return data


def _ef_location_id(session, user, password):
    """Look for the whole region before using Wellington city as a fallback.

    The Eventfinda location search can return multiple Wellington-named places.
    Earlier versions could select the city before finding the parent region.
    """
    override = os.environ.get('EVENTFINDA_LOCATION_ID', '').strip()
    if override:
        if not override.isdigit():
            raise ValueError('EVENTFINDA_LOCATION_ID must be numeric')
        log.info('Eventfinda API location: explicit location ID %s', override)
        return override
    city_candidate = None
    for search in ('Wellington Region', 'Wellington'):
        for page in range(6):
            obj = _ef_api_get(session, 'locations', user, password,
                              {'q': search, 'rows': 100, 'offset': page * 100})
            records = _ef_collection(obj, 'location', 'locations')
            for record in records:
                if not isinstance(record, dict):
                    continue
                ident = str(record.get('id', ''))
                if not ident.isdigit():
                    continue
                name = normspace(record.get('name', '')).lower()
                slug = normspace(record.get('url_slug', '')).lower()
                if name == 'wellington region' or slug == 'wellington-region':
                    log.info('Eventfinda API location: Wellington Region (ID %s)', ident)
                    return ident
                if name in ('wellington city', 'wellington') or slug in ('wellington-city', 'wellington'):
                    city_candidate = (ident, normspace(record.get('name', 'Wellington')))
            total = _ef_total(obj, 'locations')
            if not records or len(records) < 100 or (total is not None and (page + 1) * 100 >= total):
                break
    if city_candidate:
        ident, name = city_candidate
        log.warning('Eventfinda API: Wellington *region* ID not found; falling back to %s (ID %s). '
                    'This can exclude Hutt, Porirua, Kāpiti and Wairarapa. '
                    'Set EVENTFINDA_LOCATION_ID to the region ID.', name, ident)
        return ident
    raise ValueError('Wellington location ID not found in Eventfinda locations API. '
                     'Set EVENTFINDA_LOCATION_ID to the numeric Wellington Region ID.')


def _ef_text(v):
    if isinstance(v, dict):
        return normspace(v.get('name') or v.get('text') or v.get('value') or '')
    return normspace(v)


def _ef_venue(row):
    loc = row.get('location') or row.get('venue') or {}
    parts = []
    if isinstance(loc, dict):
        for field in ('name', 'address', 'city', 'region'):
            value = _ef_text(loc.get(field, ''))
            if value and value.lower() not in [p.lower() for p in parts]:
                parts.append(value)
    elif isinstance(loc, str):
        parts.append(loc)
    for field in ('venue_name', 'venue_address'):
        value = _ef_text(row.get(field, ''))
        if value and value.lower() not in [p.lower() for p in parts]:
            parts.append(value)
    return ', '.join(parts)


def _ef_occurrences(row):
    """Yield dated sessions or the overall event date if no sessions supplied."""
    sess = row.get('sessions', row.get('session', []))
    if isinstance(sess, dict):
        sess = _ef_collection({'sessions': sess}, 'session', 'sessions')
    if isinstance(sess, list) and sess:
        for item in sess[:120]:
            if isinstance(item, dict):
                yield item
        return
    yield row


def _ef_day_and_time(item, event):
    for obj in (item, event):
        for field in ('datetime_start', 'start_datetime', 'startDate', 'start_date', 'date'):
            value = obj.get(field, '')
            if isinstance(value, dict):
                value = value.get('datetime') or value.get('date') or value.get('value') or ''
            value = str(value or '')
            parsed = parse_date(value)
            if parsed:
                hhmm = re.search(r'T(\d\d:\d\d)', value)
                return parsed, (hhmm.group(1) if hhmm else parse_time(value))
    return '', ''


def parse_eventfinda_api(payload, src):
    """Convert API records to the calendar schema; explicit non-Wellington
    venues are rejected by make_event, unknown locations remain optional."""
    out = []
    for row in _ef_collection(payload, 'event', 'events'):
        if not isinstance(row, dict):
            continue
        title = _ef_text(row.get('name') or row.get('title') or '')
        if not title:
            continue
        url = _ef_text(row.get('url') or row.get('event_url') or src['url'])
        if not url.startswith('https://www.eventfinda.co.nz/'):
            url = src['url']
        venue = _ef_venue(row)
        price = _ef_text(row.get('price') or row.get('ticket_price') or '')
        if row.get('is_free') is True:
            price = 'Free'
        description = _ef_text(row.get('description') or row.get('short_description') or '')
        for item in _ef_occurrences(row):
            date, time = _ef_day_and_time(item, row)
            if date:
                event = make_event(src['id'], date, title, url=url, time=time,
                                   venue=venue, price=price, description=description)
                if event:
                    out.append(event)
    return unique_events(out)


def scrape_eventfinda_api(session, src):
    user = os.environ.get('EVENTFINDA_USERNAME', '').strip()
    password = os.environ.get('EVENTFINDA_PASSWORD', '')
    if not user or not password:
        raise ValueError('Eventfinda API credentials are not configured')
    location_id = _ef_location_id(session, user, password)
    # Explicit date bounds avoid relying on the API's implicit/default window.
    # The app only displays events up to 300 days ahead (see good_date).
    start_date = TZ_DAY()
    end_date = start_date + timedelta(days=300)
    common = {'location': location_id, 'rows': 100,
              'start_date': start_date.isoformat(), 'end_date': end_date.isoformat()}
    results = []
    pages = 0
    offset = 0
    total = None
    seen_pages = set()
    # A free-tier request may return only 10 records despite rows=100.
    # Allow enough pages for several hundred unique listings. Raise rather
    # than silently claim completeness if this safety cap is exhausted.
    max_pages = 60
    for _ in range(max_pages):
        data = _ef_api_get(session, 'events', user, password, dict(common, offset=offset))
        rows = _ef_collection(data, 'event', 'events')
        pages += 1
        reported = _ef_total(data, 'events')
        if reported is not None:
            total = reported
        page_count = (data.get('events', {}) if isinstance(data, dict) else {})
        page_count = page_count.get('count') if isinstance(page_count, dict) else None
        log.info('Eventfinda API page %d: offset=%d, returned=%d, page count=%s, explicit total=%s',
                 pages, offset, len(rows), str(page_count) if page_count is not None else '?',
                 str(total) if total is not None else '?')
        if not rows:
            break
        # Do not assume the service honours rows=100. It may cap each page
        # to a smaller size; advancing by 100 skips records in that case.
        fingerprint = (str(rows[0].get('id', '')) if isinstance(rows[0],dict) else str(rows[0]),
                       str(rows[-1].get('id', '')) if isinstance(rows[-1],dict) else str(rows[-1]))
        if fingerprint in seen_pages:
            raise ValueError('Eventfinda API repeats a page (offset appears to be ignored)')
        seen_pages.add(fingerprint)
        results.extend(rows)
        offset += len(rows)
        if total is not None and offset >= total:
            break
    else:
        raise ValueError(f'Eventfinda API exceeded {max_pages} pages; increase the page cap to cover the full catalogue')
    if not results:
        raise ValueError('Eventfinda API responded but contained no event records')
    events = parse_eventfinda_api({'events': results}, src)
    # Diagnostics distinguish incomplete retrieval from date/venue parsing.
    with_date = sum(bool(_ef_day_and_time(row, row)[0]) for row in results if isinstance(row, dict))
    unknown = sum(e['area'] == 'Unknown' for e in events)
    first = min((e['date'] for e in events), default='none')
    last = max((e['date'] for e in events), default='none')
    log.info('Eventfinda API: location ID %s, range %s to %s, %d page(s), '
             '%d raw records, API reported total=%s, %d records with top-level dates, '
             '%d retained event dates (%d unknown locations), from %s to %s',
             location_id, start_date.isoformat(), end_date.isoformat(),
             pages, len(results), str(total) if total is not None else '?',
             with_date, len(events), unknown, first, last)
    if not events:
        raise ValueError('Eventfinda API returned records but no usable upcoming Wellington dates')
    return events


def scrape_eventfinda_best(session, src):
    """API when credentials are available, otherwise preserve HTML fallback."""
    if os.environ.get('EVENTFINDA_USERNAME') and os.environ.get('EVENTFINDA_PASSWORD'):
        return scrape_eventfinda_api(session, src)
    return scrape_eventfinda(session, src)


def scrape_eventfinda(session, src):
    """Parse public regional event cards/details; flag HTTP 403 instead of pretending success.

    The listing site may deny automated traffic. No private API or key is assumed.
    """
    url=src['url'];soup=request_soup(session,url)
    out=parse_jsonld(soup,src,url)
    links=[];seen=set()
    for a in soup.find_all('a',href=True):
        href=urljoin(url,a['href']); parsed=urlparse(href)
        if not parsed.netloc.lower().endswith('eventfinda.co.nz'):continue
        if not re.search(r'^/20\d\d/[^/]+/(?:wellington(?:-[^/]+)?|lower-hutt|upper-hutt|porirua|kapiti|wairarapa)',parsed.path,re.I):continue
        if href in seen:continue
        seen.add(href);links.append(href)
        text=normspace(a.get_text(' ',strip=True))
        ctx=text
        for parent in (a.parent,a.parent.parent if a.parent else None):
            if parent:
                t=normspace(parent.get_text(' ',strip=True))
                if 15<len(t)<700 and DATE_RE.search(t):ctx=t;break
        date=parse_date(ctx)
        if date and len(text)>=5:
            ev=make_event(src['id'],date,text,url=href,time=parse_time(ctx),area=area_from(parsed.path.replace('-',' ')))
            if ev:out.append(ev)
    # Limit network requests: preserve availability of the entire refresh job.
    for href in links[:20]:
        try:
            detail=request_soup(session,href)
            found=parse_jsonld(detail,src,href)
            if found:out+=found
            elif not any(e['url']==href for e in out):out+=parse_detail_dates(detail,src,href)
        except Exception:continue
    return unique_events(out)


def scrape_upper(session,src):
    """Council's dated anchor cards, including events linking to library websites."""
    soup=request_soup(session,src['url']);out=[];seen=set()
    for a in soup.find_all('a',href=True):
        raw=normspace(a.get_text(' ',strip=True))
        m=DATE_RE.search(raw)
        if not m or len(raw)>850:continue
        date=parse_date(m.group(0));title=raw[:m.start()].strip(' -–')
        if not title or len(title)<5 or len(title)>170:continue
        key=(date,title)
        if key in seen:continue
        seen.add(key)
        # Location is already trustworthy because this is the city council's local calendar.
        ev=make_event(src['id'],date,title,area='Upper Hutt',url=urljoin(src['url'],a['href']),time=parse_time(raw[m.end():m.end()+80]))
        if ev:out.append(ev)
    return unique_events(out)


def scrape_natlib(session,src):
    """Extract individual dated event listings from National Library calendar cards."""
    soup=request_soup(session,src['url']);out=[]
    out.extend(parse_jsonld(soup,src,src['url']))
    for a in soup.select('a[href]'):
        href=urljoin(src['url'],a['href']);path=urlparse(href).path
        if not re.search(r'^/events/20\d\d/\d{1,2}/\d{1,2}(?:/|$)',path):continue
        title=normspace(a.get_text(' ',strip=True))
        if not 5<=len(title)<=170:continue
        date_match=re.search(r'/events/(20\d\d)/(\d\d?)/(\d\d?)',path)
        date=f'{date_match.group(1)}-{int(date_match.group(2)):02}-{int(date_match.group(3)):02}'
        context=normspace(a.parent.get_text(' ',strip=True)) if a.parent else ''
        ev=make_event(src['id'],date,title,url=href,venue='',time=parse_time(context),online=bool(re.search(r'\bonline\b',context,re.I)))
        if ev:out.append(ev)
    # If the site uses event cards without date URLs, use nearby explicit display date.
    if not out:out+=parse_cards(soup,src,src['url'])
    return unique_events(out)


def scrape_wcl(session,src):
    """Wellington City Libraries publishes a public Trumba RSS xCal event feed."""
    base='https://www.trumba.com/calendars/wellington-city-libraries.rss'
    now=TZ_DAY().strftime('%Y%m%d')
    response=session.get(base,params={'startdate':now,'weeks':12,'previousweeks':0,'xcal':1},headers=HEADERS,timeout=18)
    response.raise_for_status()
    root=ET.fromstring(response.content)
    out=[]
    def tag_text(node, ending):
        for item in node.iter():
            if item.tag.rsplit('}',1)[-1].lower()==ending.lower():
                value=normspace(' '.join(item.itertext()))
                if value:return value
        return ''
    for item in root.iter():
        if item.tag.rsplit('}',1)[-1].lower()!='item':continue
        title=tag_text(item,'title');link=tag_text(item,'link')
        # Never use rss pubDate: it is the publishing date, not event time.
        start=tag_text(item,'dtstart') or tag_text(item,'startdate') or tag_text(item,'start')
        if not start:
            description=BeautifulSoup(tag_text(item,'description'),'html.parser').get_text(' ',strip=True)
            m=re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*[,]?\s+\d{1,2}\s+[A-Za-z]+\s+20\d\d',description,re.I)
            start=m.group(0) if m else ''
        date=parse_date(start)
        if not date:continue
        venue=tag_text(item,'location') or tag_text(item,'where')
        ev=make_event(src['id'],date,title,url=link or src['url'],venue=venue or 'Wellington City Libraries',time=parse_time(start))
        if ev:out.append(ev)
    if not out:raise ValueError('No dated events found in Trumba RSS; feed layout may have changed')
    return unique_events(out)


def scrape_generic(session,src):
    """Best-effort publicly available JSON-LD event discovery. No fabricated dates."""
    out=[];url=src['url'];soup=request_soup(session,url)
    out.extend(parse_jsonld(soup,src,url))
    links=[];base=urlparse(url).netloc.lower().removeprefix('www.')
    for a in soup.select('a[href]'):
        href=urljoin(url,a['href'])
        parts=urlparse(href)
        host=parts.netloc.lower().removeprefix('www.')
        if host!=base:continue
        if href.split('#')[0].rstrip('/')==url.split('#')[0].rstrip('/'):continue
        path=parts.path.lower()
        if not re.search(r'/(event|events|whats-on|whatson|calendar|show|gig|courses-events)/',path):continue
        if path.count('/')<2:continue
        if href not in links:links.append(href)
        if len(links)>=18:break
    # For dedicated organisers, an event listing may have dates but no schema.
    out.extend(parse_cards(soup,src,url))
    # Crawl a modest number of same-site detail pages (no login, no third-party data).
    for link in links[:15]:
        try:
            detail=request_soup(session,link)
            found=parse_jsonld(detail,src,link)
            if found:out.extend(found)
            else:
                out.extend(parse_detail_dates(detail,src,link))
        except Exception:continue
    return out

def parse_cards(soup,src,url):
    """Recognise cards with an explicit date and a linked heading/title."""
    out=[]
    for element in soup.find_all(['article','li','div'],class_=lambda x:x and bool(re.search(r'event|card|listing|entry|item',str(x),re.I))):
        if len(element.get_text(' ',strip=True))>900:continue
        text=normspace(element.get_text(' ',strip=True))
        date=parse_date(text)
        if not date:continue
        a=element.find(['h2','h3','h4'])
        if not a:continue
        name=a.get_text(' ',strip=True)
        if len(name)<8:continue
        link=a.find('a',href=True) or element.find('a',href=True)
        href=urljoin(url,link['href']) if link else url
        ev=make_event(src['id'],date,name,url=href,time=parse_time(text))
        if ev:out.append(ev)
        if len(out)>=100:break
    return out

def parse_detail_dates(soup,src,url):
    title=soup.find('h1')
    if not title:return []
    title=title.get_text(' ',strip=True)
    # Only use event-specific pages, not general site landing pages.
    text=normspace(soup.get_text(' ',strip=True))
    datehit=None
    for area in [soup.select_one('main'),soup.find('article'),soup.body]:
        if not area:continue
        t=normspace(area.get_text(' ',strip=True))
        # Avoid unrelated dates deep in footers.
        for m in list(DATE_RE.finditer(t))[:8]:
            date=parse_date(m.group())
            if date and good_date(date):datehit=(date,parse_time(t[m.end():m.end()+45]));break
        if datehit:break
    if not datehit:return []
    date,time=datehit
    ev=make_event(src['id'],date,title,url=url,time=time)
    return [ev] if ev else []

def unique_events(events):
    unique={}
    for e in events:
        k=(e['source'],e['date'],re.sub(r'\W+','',e['title'].lower())[:90])
        if k not in unique or len(e.get('venue',''))>len(unique[k].get('venue','')):unique[k]=e
    return sorted(unique.values(),key=lambda x:(x['date'],x.get('time','') or '25:00',x['title']))

def load_cache():
    if CACHE.exists():
        try:
            cached=json.loads(CACHE.read_text('utf-8'))
            known=set(cached.get('source_status',{}))
            # This enables newly added organisers without deleting the user's
            # existing index, preferences, or earlier refresh results.
            new_ids={s['id'] for s in SOURCES if s['id'] not in known}
            if new_ids:
                cached['events']=unique_events(cached.get('events',[])+[e for e in SEED['events'] if e['source'] in new_ids and good_date(e['date'])])
                for sid in new_ids:
                    num=sum(e['source']==sid for e in cached['events'])
                    cached.setdefault('source_status',{})[sid]={'state':'snapshot' if num else 'not indexed','count':num}
            before=len(cached.get('events',[]))
            cached['events']=unique_events([safe for e in cached.get('events',[]) if e.get('source') in {x['id'] for x in SOURCES} and (safe:=local_record(e)) is not None])
            removed=before-len(cached['events'])
            if removed: log.info('Excluded %d cached out-of-region or unverified-location events',removed)
            for sid,st in cached.get('source_status',{}).items():
                st['count']=sum(e['source']==sid for e in cached['events'])
            return cached
        except Exception:pass
    seed_events=unique_events([safe for e in SEED['events'] if e.get('source') in {x['id'] for x in SOURCES} and (safe:=local_record(e)) is not None])
    return dict(updated=SEED['updated'],events=seed_events,source_status={s['id']:{'state':'snapshot' if any(e['source']==s['id'] for e in seed_events) else 'not indexed','count':sum(e['source']==s['id'] for e in seed_events)} for s in SOURCES})

DATA=load_cache()

def run_refresh(source_ids):
    global DATA
    ids=set(source_ids)
    log.info('HTML request profile: %s', 'indexer' if HEADERS == INDEXER_HEADERS else 'browser')
    candidates=[s for s in SOURCES if s['id'] in ids]
    outcome={}
    def worker(src):
        with requests.Session() as session:
            if src['id']=='glean':ev=scrape_glean(session,src)
            elif src['id']=='engineering':ev=scrape_engineering(session,src)
            elif src['id']=='heritage':ev=scrape_heritage(session,src)
            elif src['id']=='hutt':ev=scrape_hutt(session,src)
            elif src['id']=='fringebar':ev=scrape_fringebar(session,src)
            elif src['id']=='humanitix':ev=scrape_humanitix(session,src)
            elif src['id']=='eventfinda':ev=scrape_eventfinda_best(session,src)
            elif src['id']=='upper':ev=scrape_upper(session,src)
            elif src['id']=='natlib':ev=scrape_natlib(session,src)
            elif src['id']=='wcl':ev=scrape_wcl(session,src)
            else:ev=scrape_generic(session,src)
            return unique_events(ev)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futuremap={pool.submit(worker,src):src for src in candidates}
        for f in as_completed(futuremap):
            source=futuremap[f]
            try:
                events=f.result();state='indexed' if events else 'no readable events'
                outcome[source['id']]=dict(state=state,count=len(events),unknown=sum(e.get('area')=='Unknown' for e in events),events=events,checked=datetime.now().isoformat(timespec='minutes'))
            except Exception as ex:
                log.warning('Failed %s: %s',source['id'],ex)
                outcome[source['id']]=dict(state='failed',count=0,error=str(ex)[:130],checked=datetime.now().isoformat(timespec='minutes'))
    with LOCK:
        old=DATA['events']
        finished={sid for sid,x in outcome.items() if x['state']=='indexed'}
        # Replace a source's previous events only when new events were actually readable.
        final=[e for e in old if e['source'] not in finished]
        for sid in finished:final+=outcome[sid]['events']
        current_status=dict(DATA.get('source_status',{}))
        for sid,x in outcome.items():
            current_status[sid]={k:v for k,v in x.items() if k!='events'}
        # Defence in depth: revalidate all events, including records carried
        # forward from failed/empty scrapes and older caches.
        safe=[ok for e in final if (ok:=local_record(e)) is not None]
        DATA=dict(updated=datetime.now().isoformat(timespec='minutes'),events=unique_events(safe),source_status=current_status)
        for sid,st in DATA['source_status'].items():
            st['count']=sum(e['source']==sid for e in DATA['events'])
            st['unknown']=sum(e['source']==sid and e.get('area')=='Unknown' for e in DATA['events'])
        temp=CACHE.with_suffix('.tmp')
        temp.write_text(json.dumps(DATA,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(CACHE)
        STATUS.update(running=False,ended=datetime.now().isoformat(timespec='minutes'),results={sid:{k:v for k,v in x.items() if k!='events'} for sid,x in outcome.items()})
    log.info('Refresh complete: %s sources / %s events',len(outcome),len(DATA['events']))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        path=self.path.split('?')[0]
        if path=='/api/data':
            with LOCK:obj={'events':DATA['events'],'updated':DATA['updated'],'source_status':DATA.get('source_status',{}),'sources':SOURCES,'app_version':APP_VERSION,'refresh':dict(STATUS)}
            return self.json_out(obj)
        if path=='/api/status':
            with LOCK:obj=dict(STATUS)
            return self.json_out(obj)
        if path=='/':self.path='/index.html'
        return super().do_GET()
    def do_POST(self):
        if self.path!='/api/refresh':return self.send_error(404)
        try:
            n=int(self.headers.get('Content-Length','0'))
            obj=json.loads(self.rfile.read(min(n,10000)) or b'{}')
            ids=obj.get('sources',[s['id'] for s in SOURCES]);allow={s['id'] for s in SOURCES}
            ids=[x for x in ids if isinstance(x,str) and x in allow]
            if not ids:return self.json_out({'error':'No sources selected'},400)
        except Exception:return self.json_out({'error':'Invalid request'},400)
        with LOCK:
            if STATUS['running']:return self.json_out({'running':True})
            STATUS.update(running=True,started=datetime.now().isoformat(timespec='minutes'),ended=None,results={})
        threading.Thread(target=run_refresh,args=(ids,),daemon=True).start()
        return self.json_out({'running':True,'sources':len(ids)})
    def json_out(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,format,*args):
        if '/api/status' not in self.path:super().log_message(format,*args)

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
    logging.info('Open http://127.0.0.1:%d',PORT)
    threading.Timer(.9,lambda:webbrowser.open(f'http://127.0.0.1:{PORT}')).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    server.server_close()
