import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sources=[
('glean','Glean Report','https://www.gleanreport.com/wellington/','Science','Curated Wellington talks, science and humanities'),
('engineering','Engineering New Zealand','https://www.engineeringnz.org/courses-events/?location=Wellington','Engineering','Engineering talks, professional courses, site visits and socials'),
('pyramid','Pyramid Club','https://pyramidclub.org.nz/calendar','Arts','Experimental music and art'),
('bats','BATS Theatre','https://bats.co.nz/whats-on/','Arts','Theatre, comedy and experimental performances'),
('fringebar','The Fringe Bar','https://thefringebar.co.nz/','Arts','Live comedy, improv, drag, burlesque, cabaret and quirky performances at 26 Allen Street'),
('heritage','Wellington Heritage Festival','https://wellingtonheritagefestival.co.nz/events/','Heritage','Historical buildings, machinery and guided tours'),
('eventfinda','Eventfinda','https://www.eventfinda.co.nz/whatson/events/wellington-region','General','Broad regional event listings'),
('humanitix','Humanitix','https://humanitix.com/nz/events/nz--wellington-region--wellington','Workshops','Independent talks, classes and community events'),
('meetup','Meetup','https://www.meetup.com/find/nz--wellington/','Social','Clubs, specialist interest groups and social gatherings'),
('eventbrite','Eventbrite','https://www.eventbrite.co.nz/d/new-zealand--wellington-region/events/','Workshops','Talks, classes and workshops'),
('wellingtonnz','WellingtonNZ','https://www.wellingtonnz.com/visit/events','General','City events and festivals'),
('allevents','AllEvents Wellington','https://allevents.in/wellington','General','Community-submitted events'),
('museums','Museums Wellington','https://www.museumswellington.org.nz/whats-on/','Science','Museums, astronomy and history'),
('vuw','Victoria University','https://www.wgtn.ac.nz/events','Science','Academic lectures and seminars'),
('rsonz','Royal Society Wellington','https://www.royalsocietyofnewzealandwellingtonbranch.org/','Science','Public lectures and talks'),
('was','Wellington Astronomical Society','https://www.was.org.nz/','Science','Stargazing and science meetings'),
('tepapa','Te Papa','https://www.tepapa.govt.nz/visit/events','Heritage','Tours, exhibitions and public events'),
('natlib','National Library','https://natlib.govt.nz/events','Heritage','Archives, literature and history'),
('wcl','Wellington City Libraries','https://www.wcl.govt.nz/','Community','Community workshops and free lectures'),
('zealandia','Zealandia','https://www.visitzealandia.com/whats-on/','Outdoors','Nature walks, wildlife and conservation'),
('fringe','NZ Fringe Festival','https://www.fringe.co.nz/','Arts','Experimental performing arts'),
('performance','Performance Arcade','https://www.theperformancearcade.com/','Arts','Experimental art installations'),
('artclub','Wellington Art Club','https://wellingtonart.co.nz/workshop/','Workshops','Hands-on visual art'),
('wtmc','Wellington Tramping and Mountaineering Club','https://wtmc.org.nz/trips/','Outdoors','Outdoor trips and skills'),
('hutt','Hutt City Council','https://events.huttcity.govt.nz/','Community','Lower Hutt community events'),
('upper','Upper Hutt Council','https://www.upperhutt.govt.nz/events','Community','Upper Hutt festivals and workshops'),
('kapiti','Kāpiti Coast Council','https://www.kapiticoast.govt.nz/','Community','Kāpiti events and open days'),
('porirua','Porirua Council','https://poriruacity.govt.nz/','Community','Porirua community events'),
('utr','UnderTheRadar','https://www.undertheradar.co.nz/utr/gigRegion/Wellington','Music','Independent gigs'),
('image','theimage04','https://theimage04.com/','Music','Alternative music listings'),
('whatsfree','Whats On Free Events','https://www.eventfinda.co.nz/whatson/events/wellington-region/price/free','Community','Free local events'),
('facebook','Facebook Events','https://www.facebook.com/events/','Social','Informal gatherings; may require login'),
]
src=[dict(id=x[0],name=x[1],url=x[2],group=x[3],description=x[4]) for x in sources]
(ROOT/'sources.json').write_text(json.dumps(src,ensure_ascii=False,indent=2),encoding='utf-8')
events=[]
def add(src,date,title,cat,time='',venue='',area='Wellington',url=None,price='',online=False,end='',desc=''):
    key=(src+date+title).lower()
    e=dict(id=hashlib.sha1(key.encode()).hexdigest()[:16],source=src,date=date,title=title,type=cat,time=time,venue=venue,area='Online' if online else area,url=url or next(s['url'] for s in globals()['src'] if s['id']==src),price=price,online=online,end=end,description=desc,origin='verified snapshot')
    events.append(e)
# Glean report: taken from verified 13 Oct 2026 Wellington calendar
G='glean'
add(G,'2026-10-14','SCANZ month of learning — four short talks','Science','12:00',online=True)
add(G,'2026-10-14','Mammalian sex-determining gene: a hidden exon essential for male development','Science','15:00',online=True)
add(G,'2026-10-14','Rainbows in space: spectroscopy of Earth and Mars','Science','17:30','Hunter Council Chambers, Victoria University')
add(G,'2026-10-14','Trade-offs. Choices. Decisions.','Science','17:30',online=True)
add(G,'2026-10-14','Kerbing consumption','Workshops','18:00','Te Aro Zero Waste Centre, Wellington')
add(G,'2026-10-14','Systemic barriers, shared solutions: Royal Society lecture','Science','18:00','Al-Ameen mosque, Newlands')
add(G,'2026-10-14','Pockmark formation on the Chatham Rise','Science','19:00','Old Government Buildings, Victoria University')
add(G,'2026-10-14','Stargazing 101: astronomy for beginners','Science','19:00','Space Place, Kelburn')
add(G,'2026-10-14','Changing waters: ocean acidification film and kōrero','Science','19:30','Te Papa, Wellington')
add(G,'2026-10-15','What does digital inclusion really mean?','Science','11:00','Karori Library')
add(G,'2026-10-15','Working smarter with AI','Engineering','12:00',online=True)
add(G,'2026-10-15','Science curriculum support for primary schools','Science','16:00',online=True)
add(G,'2026-10-15','Garden of forking paths: models and uncertainty','Science','17:30',online=True)
add(G,'2026-10-15','Climate Fresk interactive workshop','Workshops','18:00',online=True)
add(G,'2026-10-15','Wellington waste-ed workshop','Workshops','18:00','Newlands Community Centre')
add(G,'2026-10-15','Ngā Manu quiz night','Social','18:30','Waikanae Bowling Club',area='Kāpiti')
add(G,'2026-10-17','Our ocean, our home and future: community event','Science','09:00','EFKS Newtown')
add(G,'2026-10-17','New Zealand species edit-a-thon 2026','Workshops','10:00','Te Matapihi Central Library',url='https://www.gleanreport.com/wellington/')
add(G,'2026-10-17','Te rā o Te Kaiwharawhara: conservation and talks','Outdoors','10:00','Trelissick Park, Kaiwharawhara')
add(G,'2026-10-17','A walk with Katherine Mansfield','Heritage','11:00','Wellington Botanic Garden')
add(G,'2026-10-18','The oldest rocks on Earth','Science','14:00','Te Matapihi Central Library')
add(G,'2026-10-19','Eco-church conservation kōrero','Science','19:00',online=True)
add(G,'2026-10-19','Botanical Society student talks','Science','19:30','Murphy Building, Victoria University')
add(G,'2026-10-20','Research symposium: Graham Nuthall','Science','17:00',online=True)
add(G,'2026-10-20','Conservation kōrero: in pursuit of Peripatus','Science','17:45','Zealandia Visitor Centre')
add(G,'2026-10-20','The future of stroke trials in New Zealand','Science','18:30',online=True)
add(G,'2026-10-21','Future of agriculture and horticulture forum','Science','08:50',online=True)
add(G,'2026-10-21','Virome of kānuka soil ecosystems','Science','13:00',online=True)
add(G,'2026-10-21','Energy blindness: public talk','Science','18:00','113–115 Taranaki Street')
add(G,'2026-10-21','Why hope and action are our way through current crises','Science','18:00','Ngā Manu Reserve, Waikanae',area='Kāpiti')
add(G,'2026-10-22','Genetics of sexual dimorphism','Science','12:00',online=True)
add(G,'2026-10-22','SCANZ panel discussion: month of learning','Science','12:15',online=True)
add(G,'2026-10-22','Genes to genomes: drift to adaptation','Science','17:30','Hunter Council Chambers, Victoria University')
add(G,'2026-10-24','BotSoc field trip: Stoney Creek, Wairarapa','Outdoors','09:00','Martinborough Square',area='Wairarapa',end='2026-10-25')
add(G,'2026-10-24','Forest giants, fragrant herbs and birdsong: guided walk','Outdoors','13:30','Wellington Botanic Garden')
add(G,'2026-10-25','Dr Leonard Cockayne’s vision for Ōtari: guided walk','Heritage','14:00','Ōtari-Wilton’s Bush')
add(G,'2026-10-26','Wild Wellington waterfront nature walk','Outdoors','11:00','Frank Kitts Park waterfront')
add(G,'2026-10-27','The future of energy is communal','Engineering','12:30','113–115 Taranaki Street')
add(G,'2026-10-28','Holocene evolution of Greenland Ice Sheet','Science','12:00',online=True)
add(G,'2026-10-28','Future of clinical workstations','Engineering','12:30',online=True)
add(G,'2026-10-28','Australia’s Indigenous languages and what they can teach us','Science','16:00',online=True)
add(G,'2026-10-29','Exceptionally preserved fossils: history of life','Science','15:00','Cotton Building, Victoria University')
add(G,'2026-10-29','Wellington UniVentures and Booster NZ research showcase','Engineering','17:30','Rutherford House, Victoria University')
add(G,'2026-10-29','Astronomy on Tap: 1,000 ways to die in space','Science','20:00','Space Place, Kelburn')
add(G,'2026-10-31','Mangaroa Farms spring festival','Outdoors','10:00','Whitemans Valley, Upper Hutt',area='Upper Hutt')
add(G,'2026-10-31','Dark sky telescope observing and astrophotography','Science','19:30','Near Martinborough',area='Wairarapa')
add(G,'2026-11-03','Who was Dr Leonard Cockayne?','Heritage','19:30','Ōtari-Wilton’s Bush')
add(G,'2026-11-06','Awakening the Aitu: Germany’s human zoos','Heritage','11:00','Pātaka, Porirua',area='Porirua')
add(G,'2026-11-07','Druce garden botanical field trip','Outdoors','09:30','Pinehaven, Upper Hutt',area='Upper Hutt')
add(G,'2026-11-07','All about foliage: guided walk','Outdoors','13:30','Kelburn')
# Engineering NZ, page 1 and 2 filtered for Wellington. Price comes from site where shown
E='engineering'
add(E,'2026-10-14','Getting More Value from Procurement','Engineering','17:00','Engineering New Zealand, Wellington',url='https://www.engineeringnz.org/courses-events/event-template/?eventtemplate=5375-getting-more-value-from-procurement&region=IPENZT',price='Free')
add(E,'2026-10-20','Failing Forward 2.0','Engineering','17:00','Tonkin + Taylor, Wellington',price='Free')
add(E,'2026-10-21','Concrete NZ Conference 2026','Engineering','14:00','Tākina, Wellington',price='$920')
add(E,'2026-10-21','JMD Railtech: introduction to railway signalling systems','Engineering','17:00','JMD Railtech, Upper Hutt',area='Upper Hutt',url='https://www.engineeringnz.org/courses-events/event/jmd-railtech-introduction-to-railway-signalling-sy/',price='Free')
add(E,'2026-10-28','Engineers and Espressos','Social','07:30','Smith the Grocer, Wellington',price='Free')
add(E,'2026-10-28','Transformer monitoring in BESS','Engineering','17:00','Engineering New Zealand, Wellington',url='https://www.engineeringnz.org/courses-events/event-template/?eventtemplate=5331-transformer-monitoring-in-bess-what-asset-owners-n&region=IPENZT',price='Free')
add(E,'2026-10-29','What are you doing, Wellington?','Social','17:30','AECOM, Wellington',url='https://www.engineeringnz.org/courses-events/event/what-are-you-doing-wellington/',price='Free')
add(E,'2026-10-30','Engineering Netball Tourney 2026','Social','17:30',price='Free')
add(E,'2026-11-03','Stormwater management and design: introduction','Engineering','08:30','Engineering New Zealand Wellington Office',price='$900')
add(E,'2026-11-11','Engineering a safer future: design workshop','Engineering','09:00','Engineering New Zealand, Wellington',price='$69')
add(E,'2026-11-13','Leading-edge project management and leadership','Engineering','12:00','Engineering New Zealand, Wellington',price='Free')
add(E,'2026-11-13','Wellington Emerging Professionals Ball','Social','18:30','Harbourside Function Centre',url='https://www.engineeringnz.org/courses-events/event/wellington-emerging-professionals-ball-2026/',price='$50')
add(E,'2026-11-18','Transpower: Te Kanapu — developing a grid','Engineering','17:00','Engineering New Zealand, Wellington',price='Free')
add(E,'2026-11-26','Digital Kaitiakitanga: empowering wildlife','Engineering','17:00','Engineering New Zealand, Wellington',price='Free')
add(E,'2026-12-04','Non-structural elements: from research to reality','Engineering','09:00','Massey University Wellington',price='$460')
# Pyramid Club
P='pyramid'
add(P,'2026-10-15','New Jazz for the New Era','Music','18:30','Meow, Wellington')
add(P,'2026-10-16','Dillon Butcher / Helena / Frogmeat','Music','19:30','Pyramid Club')
add(P,'2026-10-24','Descendants book tour: Lee Hana, Ludus and friends','Arts','','Pyramid Club')
add(P,'2026-10-30','Tape Night: analogue misadventures','Music','20:00','Pyramid Club')
add(P,'2026-11-07','Kina:suttsu (Japan) / vegetable.animal.machine','Music','20:00','Pyramid Club')
add(P,'2026-11-22','Doxing Ur Mum: experimental improvisation','Music','14:00','Futuna Chapel, Karori')
# BATS
B='bats'
add(B,'2026-10-14','The King’s Gambit','Arts','','BATS Theatre',end='2026-10-17')
add(B,'2026-10-15','Poprox Shakespeare','Arts','','BATS Theatre')
add(B,'2026-10-15','Double Double Feature: improv','Arts','','BATS Theatre')
add(B,'2026-10-16','Happy Hour: improv','Arts','','BATS Theatre')
add(B,'2026-10-16','Scratch Night: new works in progress','Arts','20:30','BATS Theatre',url='https://bats.co.nz/whats-on/scratch-night-october/',price='$10–$40')
add(B,'2026-10-17','Theatresports','Arts','','BATS Theatre')
add(B,'2026-10-17','Late Night Knife Fight','Arts','','BATS Theatre')
add(B,'2026-10-20','Dear God','Arts','','BATS Theatre',end='2026-10-24')
add(B,'2026-10-20','The Quickest Route to Salvation','Arts','19:00','BATS Theatre',url='https://bats.co.nz/whats-on/the-quickest-route-to-salvation/',end='2026-10-25',price='$15–$40')
add(B,'2026-11-19','The Wodessey: improvised epic','Arts','','BATS Theatre',end='2026-11-21')
add(B,'2026-11-25','The Awakening','Arts','','BATS Theatre',end='2026-11-28')
# heritage confirmed as specific events (festival from 24/10)
add('heritage','2026-11-01','Pencarrow Lighthouse open day','Heritage','11:00','Pencarrow Lighthouse, Eastbourne',area='Lower Hutt',price='Koha')
# Wellington Heritage Festival's confirmed published programme — additional dates
# Source: https://wellingtonheritagefestival.co.nz/events/ (checked 13 Oct 2026).
H='heritage'
extra_heritage=[
 ('2026-10-24','Circa Theatre behind-the-scenes tour','11:00','Circa Theatre, Wellington','Wellington','Free','https://wellingtonheritagefestival.co.nz/event/circa-theatre-behind-the-scenes-tour-26/'),
 ('2026-10-24','Erskine Chapel open day','12:00','31 Avon Street, Island Bay','Wellington','Koha','https://wellingtonheritagefestival.co.nz/event/erskine-chapel/'),
 ('2026-10-24','Hikitia steam crane 100th birthday: steam up and tours','10:00','Taranaki Street Wharf','Wellington','$10',''),
 ('2026-10-24','Professor James Belich: museums and the stories we tell','12:00','Te Papa','Wellington','',''),
 ('2026-10-24','Mount Street Cemetery open day','10:00','Mount Street Cemetery','Wellington','Free',''),
 ('2026-10-24','Wellington Cathedral and bell tower open day','10:00','2 Hill Street, Wellington','Wellington','Koha',''),
 ('2026-10-24','Dead Interesting: Bolton Street Cemetery walking tour','14:00','Bolton Street Cemetery','Wellington','',''),
 ('2026-10-24','Wellington waterfront public sculpture walk','12:00','Wellington Waterfront','Wellington','Free',''),
 ('2026-10-25','Wellington Vintage Machinery Club open day','10:00','155A Mangaroa Hill Road','Upper Hutt','Koha','https://wellingtonheritagefestival.co.nz/event/wellington-vintage-machinery-club-open-days/'),
 ('2026-10-25','Haunted Inverlochy House heritage tour','14:00','Inverlochy Place','Wellington','$25',''),
 ('2026-10-25','Rita Angus Cottage open day','12:00','194A Sydney Street West','Wellington','Koha',''),
 ('2026-10-25','The Fabulous Carmen Rupe: Tea, Toasties and Trade','13:00','Te Matapihi Central Library','Wellington','Free',''),
 ('2026-10-25','Katherine Mansfield House and Garden open day','10:00','Tinakori Road, Wellington','Wellington','Koha',''),
 ('2026-10-26','Historic Johnsonville walking tour','10:30','Johnsonville Methodist Cemetery','Wellington','Koha',''),
 ('2026-10-26','Crime and punishment: Bolton Street Cemetery walking tour','14:00','Bolton Street Cemetery','Wellington','$10',''),
 ('2026-10-26','Wellington Vintage Machinery Club open day','10:00','155A Mangaroa Hill Road','Upper Hutt','Koha','https://wellingtonheritagefestival.co.nz/event/wellington-vintage-machinery-club-open-days/'),
 ('2026-10-27','SS Ventnor legacy: Navigating the Narrative','17:30','63 Boulcott Street','Wellington','Koha',''),
 ('2026-10-28','Walk of Champions walking tour','10:00','274B Jackson Street, Petone','Lower Hutt','Koha',''),
 ('2026-10-30','The evolution of Jackson Street walking tour','10:00','Jackson Street, Petone','Lower Hutt','Koha',''),
 ('2026-10-30','Old Jail Museum open day','10:00','274B Jackson Street, Petone','Lower Hutt','Free',''),
 ('2026-10-30','Petone Community House open day','10:00','Britannia Street, Petone','Lower Hutt','Free',''),
 ('2026-10-31','Railway carriage restoration workshop open day','10:00','Chalfont Road, Silverstream','Upper Hutt','Koha','https://wellingtonheritagefestival.co.nz/event/railway-carriage-restoration-workshop/'),
 ('2026-10-31','Visit the Upper Hutt Blockhouse','11:00','Blockhouse Lane, Upper Hutt','Upper Hutt','Koha',''),
 ('2026-10-31','Robert Orr Historic Homestead open day','10:00','132 Kings Crescent, Lower Hutt','Lower Hutt','Koha',''),
 ('2026-10-31','Hikitia steam crane 100th birthday','10:00','Taranaki Street Wharf','Wellington','$10',''),
 ('2026-10-31','Wellington Trades Hall open day','09:30','126 Vivian Street','Wellington','Koha',''),
 ('2026-10-31','Futuna Chapel: black and white exhibition','11:00','Futuna Chapel, Karori','Wellington','Koha',''),
 ('2026-10-31','Historic Jackson Street Old Jail open day','10:00','274B Jackson Street','Lower Hutt','Free',''),
 ('2026-11-01','Lower Hutt Heritage Centre open day','11:00','Walter Nash Centre, Taitā','Lower Hutt','Free',''),
 ('2026-11-01','Wellington Vintage Machinery Club open day','10:00','155A Mangaroa Hill Road','Upper Hutt','Koha','https://wellingtonheritagefestival.co.nz/event/wellington-vintage-machinery-club-open-days/'),
 ('2026-11-01','Railway carriage restoration workshop open day','10:00','Chalfont Road, Silverstream','Upper Hutt','Koha','https://wellingtonheritagefestival.co.nz/event/railway-carriage-restoration-workshop/'),
 ('2026-11-01','Old Jail Museum open day','10:00','274B Jackson Street, Petone','Lower Hutt','Free',''),
 ('2026-11-01','Futuna Chapel public talks','14:00','Futuna Chapel, Karori','Wellington','Koha',''),
 ('2026-11-01','Toi demonstrations, live music and a talk','10:30','Toi MAHARA, Waikanae','Kāpiti','Free',''),
 ('2026-11-04','Old High Court open evening','17:00','34–42 Stout Street','Wellington','Free',''),
 ('2026-11-04','Chinese settlement and business in Lower Hutt and Petone','19:00','2 Queens Drive, Lower Hutt','Lower Hutt','Koha',''),
 ('2026-11-05','Wellington as an experimental society during the 1840s','17:30','88 The Terrace','Wellington','$35',''),
 ('2026-11-07','Old St Paul’s Craft and Curio Market','10:00','34 Mulgrave Street','Wellington','Koha',''),
 ('2026-11-07','Kāpiti Aviation Museum history displays','10:00','227 Kāpiti Road, Paraparaumu','Kāpiti','Free',''),
 ('2026-11-07','Home entertainment in days gone by','12:00','9 Elizabeth Street, Waikanae','Kāpiti','Free',''),
 ('2026-11-07','Paekākāriki rail depot open day','10:00','219 State Highway 59','Kāpiti','Free',''),
 ('2026-11-07','The kilns at Te Horo open day','10:00','6 Jim Winiata Way, Te Horo','Kāpiti','Koha',''),
 ('2026-11-07','Golder Cottage heritage open day','13:30','707 Fergusson Drive, Upper Hutt','Upper Hutt','Koha',''),
 ('2026-11-08','Talk: The Expatriates, artists overseas','14:00','Toi MAHARA, Waikanae','Kāpiti','Free',''),
 ('2026-11-11','Hickety Pips: military matters in colonial Wellington','14:00','Bolton Street Cemetery Museum','Wellington','$10',''),
 ('2026-11-13','A wartime evening at Featherston RSA','18:30','Featherston RSA','Wairarapa','$60',''),
 ('2026-11-14','Stonehenge Aotearoa sunset stargazing and heritage tour','19:00','Stonehenge Aotearoa, Wairarapa','Wairarapa','',''),
 ('2026-11-14','Old Government Buildings 150th birthday open day','10:00','55 Lambton Quay','Wellington','Free',''),
 ('2026-11-14','Latin Market & Expo: Hutt Valley','10:00','Dowse Square, Lower Hutt','Lower Hutt','Free',''),
 ('2026-11-15','Dead Rabbits Run Experience','13:00','347 Underhill Road, Featherston','Wairarapa','$15',''),
]
for d,title,tm,venue,area,price,url in extra_heritage:
    add(H,d,title,'Heritage',tm,venue,area,url=url or None,price=price)
# A handful of other verified Lower Hutt listings from Hutt City's event calendar.
extra_hutt=[
 ('2026-10-15','Hutt City Night Market','16:00','Dowse Square','Community'),
 ('2026-10-16','Sketch Club Social','10:00','War Memorial Library','Workshops'),
 ('2026-10-16','Open Mic Night','18:30','War Memorial Library','Music'),
 ('2026-10-17','Lower Hutt Art Trail 2026','13:00','Lower Hutt','Arts'),
 ('2026-10-17','Tabletop Play','14:00','Naenae Neighbourhood Hub','Social'),
 ('2026-10-17','Game Face','16:00','Stokes Valley Neighbourhood Hub','Social'),
 ('2026-10-19','Wainuiomata Community Garden','09:00','Wainuiomata','Outdoors'),
 ('2026-10-23','Life After Stroke education session','10:30','Naenae Community Centre','Science'),
]
for d,title,tm,venue,cat in extra_hutt:
    add('hutt',d,title,cat,tm,venue,'Lower Hutt')
# The Fringe Bar official show guide — checked 13 October 2026.
# The linked organiser page is a general guide; clicking a refreshed event will
# take the user to the exact ticket listing when the dedicated indexer finds it.
F='fringebar'
FRINGE_VENUE='The Fringe Bar, 26 Allen Street, Wellington'
FRINGE_GUIDE='https://thefringebar.co.nz/'
fringe_performances=[
 ('2026-10-16','The Wellington Comedy Club with Joe Daymond and friends'),
 ('2026-10-17','The Wellington Comedy Club with Joe Daymond and friends'),
 ('2026-10-16','Work in Progress Laughs!'),
 ('2026-10-17','Work in Progress Laughs!'),
 ('2026-10-17','Q&A with Joe Daymond'),
 ('2026-10-23','Best In Class: NZ Comedy School Show'),
 ('2026-10-24','Burlesque Baby October'),
 ('2026-10-29','NZ Comedy School Graduation Showcase'),
 ('2026-10-29','Only The New Stuff: Game Show Edition'),
 ('2026-10-30','Lads, Lads, Lads — Spooky Boys: A Halloween Drag King Show'),
 ('2026-11-06','James Nokise: One Night Rant 2026'),
 ('2026-11-13','Circus of the Night — November'),
 ('2026-11-14','Circus of the Night — November'),
 ('2026-11-15','The Velvet Haven: Student Showcase'),
 ('2026-11-20','The Wellington Comedy Club with Wilson Dixon and Gabby Anderson'),
 ('2026-11-21','The Wellington Comedy Club with Wilson Dixon and Gabby Anderson'),
 ('2026-11-27','Red Ribbon Revue: A Cabaret for World AIDS Day'),
 ('2026-12-11','NZ Comedy School Graduation Showcase'),
 ('2026-12-12','Fruitcake: A Jolly Good Christmas Cabaret'),
 ('2026-12-19','The 2026 Wellington Comedy Club Christmas Showcase'),
 ('2027-01-24','The Wellington Comedy Club with Chris Parker and friends'),
]
for d,title in fringe_performances:
    add(F,d,title,'Arts','','The Fringe Bar, 26 Allen Street, Wellington','Wellington',url=FRINGE_GUIDE)
# Explicitly weekly recurring shows — do not infer daily events from long date spans.
from datetime import date,timedelta
for start,stop,title,weekday in [
    ('2026-10-14','2026-12-16','Fringe Bar Comedy Club',2),
    ('2026-10-19','2026-12-21','Raw Meat Monday — Live Stand Up Comedy',0)
]:
    dt=date.fromisoformat(start)
    finish=date.fromisoformat(stop)
    while dt<=finish:
        if dt.weekday()==weekday:
            add(F,dt.isoformat(),title,'Arts','','The Fringe Bar, 26 Allen Street, Wellington','Wellington',url=FRINGE_GUIDE)
        dt+=timedelta(days=1)

# dedupe by date and title across sources: leave Heritage Festival as its own organiser listing
(ROOT/'events.json').write_text(json.dumps({'updated':'2026-10-13','source':'Hand-checked initial snapshot, not a live feed','events':events},ensure_ascii=False,indent=2),encoding='utf-8')
print('Sources',len(src),'events',len(events))
