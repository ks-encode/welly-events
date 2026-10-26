"""Offline parser regression tests. Run: python test_indexers.py"""
import unittest
from unittest.mock import patch
import server

class Resp:
    def __init__(self,html):self.content=html.encode()
    def raise_for_status(self):pass
class Session:
    def __init__(self,pages):self.pages=pages
    def get(self,url,**kw):return Resp(self.pages.get(url,'<html><body></body></html>'))

class RequestHeaderTests(unittest.TestCase):
    def test_browser_profile_and_indexer_profile(self):
        import os
        with patch.dict(os.environ, {'WELLY_HTTP_PROFILE': 'browser'}):
            h=server.html_request_headers()
            self.assertIn('Mozilla/5.0', h['User-Agent'])
            self.assertIn('text/html', h['Accept'])
        with patch.dict(os.environ, {'WELLY_HTTP_PROFILE': 'indexer'}):
            h=server.html_request_headers()
            self.assertIn('WellyOdditiesPersonalIndexer', h['User-Agent'])

    def test_http_failure_reports_final_host_and_cloudflare(self):
        class Forbidden:
            status_code=403
            content=b'forbidden'
            url='https://events.humanitix.com/blocked?private=secret'
            history=[object()]
            headers={'cf-ray':'abc123', 'Content-Type':'text/html; charset=utf-8'}
        class DeniedSession:
            def get(self,*args,**kwargs):return Forbidden()
        with self.assertRaises(server.requests.HTTPError) as err:
            server.request_soup(DeniedSession(),'https://humanitix.com/nz/events')
        message=str(err.exception)
        self.assertIn('403',message)
        self.assertIn('Cloudflare',message)
        self.assertIn('redirects',message)
        self.assertNotIn('secret',message)

class ParserTests(unittest.TestCase):
    def setUp(self):
        # Fixtures are set in October 2026; keep tests stable on future dates.
        clock=patch('server.TZ_DAY', return_value=__import__('datetime').date(2026,10,13))
        clock.start()
        self.addCleanup(clock.stop)

    @patch('server.TZ_DAY',return_value=__import__('datetime').date(2026,10,25))
    def test_humanitix_category_pages_and_dedup(self, _mock_day):
        s=next(x for x in server.SOURCES if x['id']=='humanitix')
        base=s['url'].rstrip('/')
        def card(slug,day,title,locality):
            return f'<a href="https://events.humanitix.com/{slug}">9 followers WED, {day} NOV, 5:30PM {title} {locality}</a>'
        # Homepage exposes only four, category URLs have many more.
        home=''.join(card('event-'+str(i),i+1,'Initial Event '+str(i),'Te Aro') for i in range(4))
        business=''.join(card('event-'+str(i),i+1,'Initial Event '+str(i),'Te Aro') for i in range(4))
        business+=''.join(card('biz-'+str(i),i+1,'Business Science Talk '+str(i),'Pipitea') for i in range(5,17))
        wellness=''.join(card('well-'+str(i),i+1,'Mindfulness Class '+str(i),'Brooklyn') for i in range(1,8))
        wellness+=card('bad-auckland',15,'Another event','Auckland Central')
        music=''.join(card('music-'+str(i),i+1,'Live Music Event '+str(i),'Te Aro') for i in range(2,12))
        music+=card('mystery',22,'Mystery Event','To be announced')
        pages={base:home,
             base+'/trending--businessandprofessional':business,
             base+'/trending--healthandwellness':wellness,
             base+'/trending--music':music}
        ev=server.scrape_humanitix(Session(pages),s)
        # 4+12+7+10+1 = 34 distinct events; not just homepage's four.
        self.assertEqual(len(ev),34)
        self.assertEqual(sum(e['title'].startswith('Initial Event') for e in ev),4)
        self.assertFalse(any('Auckland' in e['title'] or 'Auckland' in e['venue'] for e in ev))
        self.assertIn('Unknown', [e['area'] for e in ev])
        self.assertTrue(all(e['url'].startswith('https://events.humanitix.com/') for e in ev))

    @patch('server.TZ_DAY',return_value=__import__('datetime').date(2026,10,25))
    def test_humanitix_detail_enriches_card_and_failed_category_is_nonfatal(self,_mock_day):
        s=next(x for x in server.SOURCES if x['id']=='humanitix');base=s['url'].rstrip('/')
        url='https://events.humanitix.com/robot-workshop'
        listing='<a href="'+url+'">WED, 4 NOV, 5:30PM Robot Workshop Pipitea</a>'
        detail='<script type="application/ld+json">{"@type":"Event","name":"Robot Workshop","startDate":"2026-11-04T17:30:00+13:00","description":"Build robots together","location":{"@type":"Place","name":"Engineering Hub","address":{"addressLocality":"Wellington","streetAddress":"12 Example St"}}}</script>'
        pages={base:listing,base+'/trending--businessandprofessional':listing,url:detail}
        ev=server.scrape_humanitix(Session(pages),s)
        self.assertEqual(len(ev),1)
        self.assertIn('12 Example St',ev[0]['venue'])
        self.assertIn('Build robots together',ev[0]['description'])

    def test_glean(self):
        s=next(s for s in server.SOURCES if s['id']=='glean')
        body='''<table><tbody><tr><td>Wed 14 October 12:00 - 13:00</td><td><a href="/event-a">Rainbows in space *WGTN*</a> | at Victoria University | <a href="https://sample.nz/e">More information</a></td></tr></tbody></table>'''
        es=server.scrape_glean(Session({s['url']:body}),s)
        self.assertEqual(len(es),1)
        self.assertEqual(es[0]['date'],'2026-10-14')
        self.assertEqual(es[0]['time'],'12:00')
        self.assertEqual(es[0]['url'],'https://sample.nz/e')

    def test_engineering_pagination(self):
        s=next(s for s in server.SOURCES if s['id']=='engineering')
        a='''<div><b>Free</b><a href="/courses-events/event/rail-test/">21 oct 2026, 5.00PM JMD Railtech | Introduction to Railway Engineering JMD Railtech - Upper Hutt, Wellington</a></div>'''
        b='''<div><b>Free</b><a href="/courses-events/event/monitor-test/">28 oct 2026, 5.00PM Transformer Monitoring Engineering New Zealand, Wellington</a></div>'''
        pages={s['url']:a,s['url']+'&p=2':b}
        es=server.scrape_engineering(Session(pages),s)
        self.assertEqual(len(es),2)
        self.assertEqual([e['date'] for e in es],['2026-10-21','2026-10-28'])
        self.assertTrue(all(e['time']=='17:00' for e in es))

    def test_heritage_card(self):
        s=next(s for s in server.SOURCES if s['id']=='heritage')
        html='''<a href="/event/railway-carriage-restoration-workshop/">Railway Carriage Restoration Workshop 10am-3pm Sat 31 Oct10am-3pm Sun 1 Nov Chalfont Road, Silverstream Accessible Koha</a><a href="/event/sold/">Fully booked Cancelled thing 2-3pm Sun 1 Nov Wellington</a>'''
        es=server.scrape_heritage(Session({s['url']:html}),s)
        self.assertEqual(len(es),2)
        self.assertEqual([e['date'] for e in es],['2026-10-31','2026-11-01'])
        self.assertEqual(es[0]['time'],'10:00')

    def test_hutt(self):
        s=next(s for s in server.SOURCES if s['id']=='hutt')
        html='''<div class="event"><a href="/events/a">Lower Hutt Art Trail</a><div>17 October 2026 at 1:00 PM</div><div>Off-site</div></div>'''
        es=server.scrape_hutt(Session({s['url']:html}),s)
        self.assertEqual(len(es),1)
        self.assertEqual(es[0]['date'],'2026-10-17')

    @patch('server.TZ_DAY',return_value=__import__('datetime').date(2026,10,13))
    def test_fringebar_pagination_and_recurring(self, _mock_day):
        s=next(s for s in server.SOURCES if s['id']=='fringebar')
        page_one='''<div class="event-card"><h4><a href="https://www.eventfinda.co.nz/2026/wip/wellington">Work in Progress Laughs!</a></h4><span>Fri 16 Oct - Sat 17 Oct</span><p>Jokes from comics</p></div>
        <section><h4><a href="https://www.eventfinda.co.nz/2026/raw-meat/wellington">Raw Meat Monday - Live Stand Up Comedy</a></h4><p>Mon 25 May 2026 - Mon 21 Dec</p><p>Weekly open mic comedy night</p></section>'''
        page_two='''<div><h4><a href="https://www.eventfinda.co.nz/2026/circus/wellington">Circus of the Night - November</a></h4><div>Fri 13 Nov - Sat 14 Nov</div></div>'''
        pages={s['url']:page_one,'https://thefringebar.co.nz/page/2/?pageId=2':page_two}
        es=server.scrape_fringebar(Session(pages),s)
        wip=[e for e in es if e['title']=='Work in Progress Laughs!']
        self.assertEqual([e['date'] for e in wip],['2026-10-16','2026-10-17'])
        circus=[e for e in es if e['title'].startswith('Circus of the Night')]
        self.assertEqual([e['date'] for e in circus],['2026-11-13','2026-11-14'])
        monday=[e for e in es if 'Raw Meat' in e['title']]
        self.assertGreaterEqual(len(monday),9)
        self.assertTrue(all(__import__('datetime').date.fromisoformat(e['date']).weekday()==0 for e in monday))
        self.assertTrue(all(e['source']=='fringebar' and e['url'].startswith('https://www.eventfinda.co.nz/') for e in es))

    @patch('server.TZ_DAY',return_value=__import__('datetime').date(2026,10,13))
    def test_fringebar_long_range_not_daily(self, _mock_day):
        s=next(s for s in server.SOURCES if s['id']=='fringebar')
        h='''<div><h4><a href="https://www.eventfinda.co.nz/2026/graduation/wellington">NZ Comedy School Graduation Showcase</a></h4><p>Thu 29 Oct - Fri 11 Dec</p></div>'''
        es=server.scrape_fringebar(Session({s['url']:h}),s)
        self.assertEqual(len(es),1)
        self.assertEqual(es[0]['date'],'2026-10-29')
        self.assertEqual(es[0]['end'],'2026-12-11')


    def test_venue_city_filter(self):
        d='2026-10-20'
        self.assertIsNone(server.make_event('engineering',d,'Bridge design workshop',venue='Auckland Town Hall, Auckland'))
        self.assertIsNone(server.make_event('eventfinda',d,'Robot workshop',venue='Christchurch, NZ'))
        self.assertIsNone(server.make_event('meetup',d,'Machine learning group',venue='Hamilton'))
        e=server.make_event('engineering',d,'Rail technology tour',venue='Upper Hutt Railway Station')
        self.assertEqual(e['area'],'Upper Hutt')
        self.assertEqual(server.make_event('eventfinda',d,'Mystery technical talk')['area'],'Unknown')
        self.assertEqual(server.make_event('bats',d,'Late night comedy')['area'],'Wellington')
        self.assertEqual(server.make_event('meetup',d,'Remote seminar',online=True,venue='')['area'],'Online')

    def test_bad_legacy_cache_record(self):
        e={'source':'engineering','date':'2026-10-20','title':'Materials science',
           'venue':'Auckland', 'area':'Wellington','url':'https://example.com/2026/materials/auckland',
           'online':False}
        self.assertIsNone(server.local_record(e))
        e['venue']='Te Papa, Wellington'
        e['url']='https://example.com/2026/materials/wellington'
        self.assertEqual(server.local_record(e)['area'],'Wellington')

    def test_remote_city_in_engineering_title_and_url(self):
        d='2026-10-20'
        self.assertIsNone(server.make_event('engineering',d,'Bridge site visit Auckland'))
        self.assertIsNone(server.make_event('engineering',d,'Bridge site visit',url='https://www.eventfinda.co.nz/2026/site-visit/auckland'))
        self.assertEqual(server.make_event('engineering',d,'Monitoring discussion Wellington')['area'],'Wellington')

    def test_eventbrite_auckland_jsonld_rejected(self):
        src=next(x for x in server.SOURCES if x['id']=='eventbrite')
        html='''<script type="application/ld+json">{
          "@context":"https://schema.org", "@type":"Event",
          "name":"SMITH & SHETH (CRU) WINE MASTERCLASS",
          "startDate":"2026-10-21T18:00:00+13:00",
          "location":{"@type":"Place","name":"Amber Café & Bistro",
           "address":{"@type":"PostalAddress","addressLocality":"Auckland",
           "addressRegion":"Auckland","postalCode":"1022","addressCountry":"NZ"}}
        }</script>'''
        es=server.parse_jsonld(server.BeautifulSoup(html,'html.parser'),src,src['url'])
        self.assertEqual(es,[])

    def test_eventbrite_wellington_jsonld_pretty_location(self):
        src=next(x for x in server.SOURCES if x['id']=='eventbrite')
        html='''<script type="application/ld+json">{
          "@type":"Event","name":"Wellington Opera House brass concert",
          "startDate":"2026-10-21T18:00:00+13:00",
          "location":{"@type":"Place", "name":"Wellington Opera House",
           "address":{"@type":"PostalAddress", "streetAddress":"111 Manners St",
           "addressLocality":"Wellington", "addressRegion":"Wellington", "addressCountry":"NZ"}}
        }</script>'''
        es=server.parse_jsonld(server.BeautifulSoup(html,'html.parser'),src,src['url'])
        self.assertEqual(len(es),1)
        self.assertEqual(es[0]['area'],'Wellington')
        self.assertIn('111 Manners St',es[0]['venue'])
        self.assertNotIn('{',es[0]['venue'])

    def test_auckland_hybrid_gets_excluded(self):
        src=next(x for x in server.SOURCES if x['id']=='eventbrite')
        html='''<script type="application/ld+json">{
          "@type":"Event","name":"The Digital Journey — Transforming Construction and Building BIM Careers",
          "startDate":"2026-10-21T18:00:00+13:00",
          "eventAttendanceMode":"https://schema.org/OnlineEventAttendanceMode",
          "location":[{"@type":"Place","name":"GHD","address":{"addressLocality":"Auckland","addressRegion":"Auckland"}},{"@type":"VirtualLocation","url":"https://example.com/live"}]
        }</script>'''
        es=server.parse_jsonld(server.BeautifulSoup(html,'html.parser'),src,src['url'])
        self.assertEqual(es,[])

    def test_clean_and_reject_old_location_dict_in_cache(self):
        e={'source':'eventbrite','date':'2026-10-21','title':'Smith & Sheth masterclass',
           'venue':"Amber Café & Bistro {'addressLocality': 'Auckland', 'addressRegion': 'Auckland', 'addressCountry': 'NZ'}",
           'area':'Online','online':True,'url':'https://example.com/e/example'}
        self.assertIsNone(server.local_record(e))
        e['venue']="Wellington Opera House {'streetAddress': '111 Manners St', 'addressLocality': 'Wellington', 'addressRegion': 'Wellington'}"
        e['area']='Wellington';e['online']=False
        cleaned=server.local_record(e)
        self.assertIn('111 Manners St',cleaned['venue'])
        self.assertNotIn('{',cleaned['venue'])
        self.assertEqual(cleaned['area'],'Wellington')

    def test_unknown_location_visible_but_remote_rejected(self):
        d='2026-10-25'
        ev=server.make_event('humanitix',d,'Bizarre science debate',venue='To be announced',url='https://events.humanitix.com/weird-science')
        self.assertEqual(ev['area'],'Unknown')
        self.assertEqual(server.local_record(ev)['area'],'Unknown')
        self.assertIsNone(server.make_event('humanitix',d,'Bizarre science debate',venue='Civic Centre Auckland'))
        self.assertIsNone(server.make_event('humanitix',d,'Bizarre science debate Auckland',url='https://events.humanitix.com/weird-science'))

    def test_humanitix_cross_domain_marketplace(self):
        s=next(x for x in server.SOURCES if x['id']=='humanitix')
        html='''<a href="https://events.humanitix.com/sound-stage-berna">
            WED, 28 OCT, 6:30PM Sound Stage - Berna &amp; Moana Hutt Central</a>
            <a href="https://events.humanitix.com/unknown-science">FRI, 30 OCT, 7PM Mysterious workshop To be announced</a>
            <a href="https://events.humanitix.com/auckland-show">FRI, 30 OCT, 8PM Auckland Show Auckland</a>'''
        detail='''<script type="application/ld+json">{
          "@type":"Event", "name":"Sound Stage - Berna & Moana", "startDate":"2026-10-28T18:30:00+13:00",
          "location":{"@type":"Place","name":"Hutt Recreation","address":{"addressLocality":"Lower Hutt"}}
        }</script>'''
        sess=Session({s['url']:html,'https://events.humanitix.com/sound-stage-berna':detail})
        events=server.scrape_humanitix(sess,s)
        sound=[e for e in events if 'Sound Stage' in e['title']]
        self.assertTrue(sound)
        self.assertEqual(sound[0]['date'],'2026-10-28')
        self.assertTrue(any(e['area']=='Unknown' for e in events))
        self.assertFalse(any(e['area']=='Outside region' or 'Auckland Show' in e['title'] for e in events))

    def test_upper_hutt_dated_listing(self):
        s=next(x for x in server.SOURCES if x['id']=='upper')
        page='''<a href="/events/composition-class">Compost 101 Workshop 03 Nov 2026 Learn how to compost for free. Council garden, Upper Hutt</a>
        <a href="/events/meeting">Council Meeting 30 Oct 2026 Watch in-person, 838 Fergusson Drive Upper Hutt</a>'''
        events=server.scrape_upper(Session({s['url']:page}),s)
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]['date'],'2026-10-30')
        self.assertTrue(all(e['area']=='Upper Hutt' for e in events))

    def test_trumba_rss_feed_not_publish_date(self):
        s=next(x for x in server.SOURCES if x['id']=='wcl')
        rss='''<?xml version="1.0"?><rss xmlns:xcal="urn:ietf:params:xml:ns:xcal" version="2.0"><channel>
          <item><title>Make a robot at the library</title><link>https://www.trumba.com/calendar/1</link>
          <pubDate>Mon, 01 Jun 2026 12:00:00 GMT</pubDate>
          <xcal:dtstart><xcal:date-time>2026-10-25T11:00:00+13:00</xcal:date-time></xcal:dtstart>
          <xcal:location>Karori Library, Wellington</xcal:location></item>
          </channel></rss>'''
        class RSSSession:
            def get(self,url,**kw):return Resp(rss)
        events=server.scrape_wcl(RSSSession(),s)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['date'],'2026-10-25')
        self.assertEqual(events[0]['time'],'11:00')
        self.assertEqual(events[0]['area'],'Wellington')

    def test_eventfinda_listing_and_region(self):
        s=next(x for x in server.SOURCES if x['id']=='eventfinda')
        page='''<div class="event-card"><a href="/2026/brass-band-night/wellington">Brass Band Night</a><span>24 Oct 2026, 7pm</span></div>
        <div class="event-card"><a href="/2026/big-comedy/auckland">Big Comedy</a><span>24 Oct 2026</span></div>'''
        events=server.scrape_eventfinda(Session({s['url']:page}),s)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['title'],'Brass Band Night')
        self.assertEqual(events[0]['date'],'2026-10-24')

    def test_eventfinda_api_short_pages_continue_and_date_window(self):
        """A 61-row page is not necessarily the end of a 200-row result."""
        from datetime import date
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        class ApiResponse:
            content=b'{}'
            def __init__(self,data):self.data=data
            def json(self):return self.data
            def raise_for_status(self):pass
        class ApiSession:
            def __init__(self):self.offsets=[]
            def get(self,url,**kwargs):
                q=kwargs.get('params',{})
                if url.endswith('locations.json'):
                    return ApiResponse({'locations':{'location':[{'name':'Wellington Region','id':77}], 'count':1}})
                off=q['offset'];self.offsets.append(off)
                self_outer.assertEqual(q['start_date'],'2026-10-13')
                self_outer.assertEqual(q['end_date'],'2027-08-09')
                data=[{'id':i,'name':f'Interesting Event {i}',
                       'url':f'https://www.eventfinda.co.nz/2026/test-{i}/wellington',
                       'datetime_start':'2026-11-02T12:30:00+13:00',
                       'location':{'name':'Wellington'}} for i in range(off,min(off+61,200))]
                return ApiResponse({'events':{'count':200, 'event':data}})
        self_outer=self
        sess=ApiSession()
        with patch.dict('os.environ',{'EVENTFINDA_USERNAME':'test','EVENTFINDA_PASSWORD':'test','EVENTFINDA_LOCATION_ID':''}):
            found=server.scrape_eventfinda_api(sess,src)
        self.assertEqual(sess.offsets,[0,61,122,183,200])
        self.assertEqual(len(found),200)

    def test_eventfinda_count_is_page_size_not_total(self):
        # Realistic small free-tier page sizes: the old code incorrectly
        # interpreted 'count':10 as a full-result total and stopped at page 1.
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        class ApiResponse:
            content=b'{}'
            def __init__(self, data): self.data=data
            def json(self): return self.data
            def raise_for_status(self): pass
        class ApiSession:
            def __init__(self): self.offsets=[]
            def get(self, url, **kwargs):
                q=kwargs['params']
                if url.endswith('locations.json'):
                    return ApiResponse({'locations':{'location':[{'name':'Wellington Region','id':77}], 'count':1}})
                off=q['offset']; self.offsets.append(off)
                rows=[{'id':i, 'name':f'Wellington event {i}',
                       'url':f'https://www.eventfinda.co.nz/2026/example-{i}/wellington',
                       'datetime_start':'2026-11-05T17:30:00+13:00',
                       'location':{'name':'Wellington'}}
                      for i in range(off, min(off+10, 37))]
                return ApiResponse({'events':{'count':len(rows), 'event':rows}})
        sess=ApiSession()
        with patch.dict('os.environ', {'EVENTFINDA_USERNAME':'test', 'EVENTFINDA_PASSWORD':'test',
                                      'EVENTFINDA_LOCATION_ID':''}):
            got=server.scrape_eventfinda_api(sess,src)
        self.assertEqual(sess.offsets, [0,10,20,30,37])
        self.assertEqual(len(got),37)

    def test_eventfinda_page_budget_saves_partial_and_resumes(self):
        """Page cap must NOT discard all events; next run resumes at saved offset."""
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        class Resp:
            content=b'{}'
            def __init__(self, data):self.data=data
            def raise_for_status(self):pass
            def json(self):return self.data
        class ApiSession:
            def __init__(self):self.offsets=[]
            def get(self,url,**kw):
                if url.endswith('locations.json'):
                    return Resp({'locations':{'location':[{'name':'Wellington Region','id':11}]}})
                off=kw['params']['offset'];self.offsets.append(off)
                rows=[{'id':i,'name':f'Workshop number {i}',
                       'url':f'https://www.eventfinda.co.nz/2026/ww{i}/wellington',
                       'datetime_start':'2026-11-04T18:00:00+13:00',
                       'location':{'name':'Wellington'}}
                      for i in range(off,min(off+10,47))]
                return Resp({'events':{'event':rows,'count':len(rows)}})
        sess=ApiSession()
        old=server.DATA
        try:
            # Partial run indexes 30 records, even without the final empty page.
            server.DATA={'events':[],'source_status':{}}
            with patch.dict('os.environ', {'EVENTFINDA_USERNAME':'test',
                    'EVENTFINDA_PASSWORD':'test','EVENTFINDA_LOCATION_ID':'11',
                    'WELLY_EVENTFINDA_PAGES_PER_RUN':'3'}):
                first=server.scrape_eventfinda_api(sess,src)
            self.assertFalse(first.complete)
            self.assertEqual(first.next_offset,30)
            self.assertEqual(len(first),30)
            self.assertEqual(sess.offsets,[0,10,20])
            server.DATA={'events':list(first), 'source_status':{'eventfinda':{'state':'partial','next_offset':30}}}
            sess2=ApiSession()
            with patch.dict('os.environ', {'EVENTFINDA_USERNAME':'test',
                    'EVENTFINDA_PASSWORD':'test','EVENTFINDA_LOCATION_ID':'11',
                    'WELLY_EVENTFINDA_PAGES_PER_RUN':'3'}):
                last=server.scrape_eventfinda_api(sess2,src)
            self.assertTrue(last.complete)
            self.assertTrue(last.continued)
            self.assertEqual(last.next_offset,0)
            self.assertEqual(len(last),17)
            self.assertEqual(sess2.offsets,[30,40,47])
        finally:
            server.DATA=old

    def test_partial_refresh_keeps_previous_eventfinda_entries(self):
        import tempfile
        from pathlib import Path
        old_data=server.DATA;old_cache=server.CACHE
        with tempfile.TemporaryDirectory() as td:
            try:
                server.CACHE=Path(td)/'index_cache.json'
                older=server.make_event('eventfinda','2026-11-02','Older Wellington Workshop',venue='Wellington')
                newer=server.make_event('eventfinda','2026-11-03','Newer Wellington Workshop',venue='Wellington')
                server.DATA={'events':[older],'source_status':{'eventfinda':{'state':'partial','next_offset':20}},'updated':''}
                with patch('server.scrape_eventfinda_best',return_value=server.EventfindaBatch(
                        [newer],complete=False,next_offset=30,continued=True)):
                    server.run_refresh(['eventfinda'])
                self.assertEqual(server.DATA['source_status']['eventfinda']['state'],'partial')
                self.assertEqual(server.DATA['source_status']['eventfinda']['next_offset'],30)
                self.assertEqual(sum(e['source']=='eventfinda' for e in server.DATA['events']),2)
                self.assertTrue(server.CACHE.exists())
            finally:
                server.DATA=old_data;server.CACHE=old_cache

    def test_eventfinda_prefers_region_to_city(self):
        class ApiResponse:
            content=b'{}'
            def __init__(self,data):self.data=data
            def json(self):return self.data
            def raise_for_status(self):pass
        class ApiSession:
            def get(self,url,**kwargs):
                q=kwargs['params']
                locations=[{'name':'Wellington','id':44}]
                if q['q']=='Wellington':
                    locations.append({'name':'Wellington Region','id':77})
                return ApiResponse({'locations':{'location':locations,'count':len(locations)}})
        with patch.dict('os.environ', {'EVENTFINDA_LOCATION_ID':''}):
            self.assertEqual(server._ef_location_id(ApiSession(),'user','pass'),'77')

    def test_eventfinda_api_nested_response_and_location_safety(self):
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        payload={'events':{'count':3,'event':[
            {'id':1,'name':'Future Electronics Lecture',
             'url':'https://www.eventfinda.co.nz/2026/future-electronics/wellington',
             'datetime_start':'2026-11-02T18:30:00+13:00',
             'location':{'name':'Te Papa','address':'Cable Street, Wellington'}},
            {'id':2,'name':'Auckland Technology Show',
             'url':'https://www.eventfinda.co.nz/2026/auckland-tech/auckland',
             'datetime_start':'2026-11-03T12:00:00+13:00',
             'location':{'name':'Auckland Centre','address':'Auckland'}},
            {'id':3,'name':'Mystery Science Gathering',
             'url':'https://www.eventfinda.co.nz/2026/mystery-science/wellington',
             'datetime_start':'2026-11-05T09:00:00+13:00'}]}}
        got=server.parse_eventfinda_api(payload,src)
        self.assertEqual(len(got),2)
        self.assertEqual(got[0]['date'],'2026-11-02')
        self.assertEqual(got[0]['time'],'18:30')
        self.assertEqual(got[1]['area'],'Wellington')
        self.assertFalse(any('Auckland' in e['title'] for e in got))

    def test_eventfinda_api_location_lookup_and_auth(self):
        from unittest.mock import patch
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        class ApiResponse:
            def __init__(self,data):
                self._data=data
                self.content=b'{}'
            def raise_for_status(self):pass
            def json(self):return self._data
        class ApiSession:
            def __init__(self):self.calls=[]
            def get(self,url,**kwargs):
                self.calls.append((url,kwargs))
                if url.endswith('locations.json'):
                    return ApiResponse({'locations':{'location':[
                        {'id':88,'name':'Wellington City','url_slug':'wellington-city'},
                        {'id':77,'name':'Wellington Region','url_slug':'wellington-region'}], 'count':2}})
                if url.endswith('events.json'):
                    if kwargs.get('params', {}).get('offset', 0) > 0:
                        return ApiResponse({'events':{'event':[], 'count':0}})
                    return ApiResponse({'events':{'event':[
                        {'id':15,'name':'Microscope Workshop','datetime_start':'2026-11-04T11:00:00+13:00',
                         'url':'https://www.eventfinda.co.nz/2026/microscope-workshop/wellington',
                         'location':{'name':'Lower Hutt','address':'Lower Hutt'}}], 'count':1}})
                raise AssertionError(url)
        sess=ApiSession()
        with patch.dict('os.environ',{'EVENTFINDA_USERNAME':'test-user','EVENTFINDA_PASSWORD':'test-password'},clear=False):
            got=server.scrape_eventfinda_api(sess,src)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]['area'],'Lower Hutt')
        self.assertEqual(sess.calls[-1][1]['params']['location'],'77')
        self.assertEqual(sess.calls[-1][1]['auth'],('test-user','test-password'))
        self.assertTrue(all('test-password' not in url for url,_ in sess.calls))

    def test_eventfinda_api_multiple_sessions(self):
        src=next(x for x in server.SOURCES if x['id']=='eventfinda')
        payload={'events':[{'name':'Meteorite Exhibition',
            'url':'https://www.eventfinda.co.nz/2026/meteorite-exhibition/wellington',
            'location':{'name':'Museum Wellington','address':'Wellington'},
            'sessions':{'session':[{'datetime_start':'2026-11-06T11:00:00+13:00'},
                                   {'datetime_start':'2026-11-07T13:00:00+13:00'}]}}]}
        got=server.parse_eventfinda_api(payload,src)
        self.assertEqual([x['date'] for x in got], ['2026-11-06','2026-11-07'])

    def test_natlib_dated_card(self):
        s=next(x for x in server.SOURCES if x['id']=='natlib')
        html='<article><a href="/events/2026/10/24/poetry-slam">Wellington Regional Poetry Slam Finals</a></article>'
        events=server.scrape_natlib(Session({s['url']:html}),s)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['date'],'2026-10-24')

if __name__=='__main__':unittest.main()
