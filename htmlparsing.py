import re
from pprint import pprint

from requests_html import HTMLSession

session = HTMLSession()
r = session.get('http://ignio.com/r/dailyanti')
print(r.html.text)
print('=======================================')
m = re.search("<!-- var ignioText.*1: new Array\('<p>(.*)</p>'\), 2:", r.html.text)
sent = m.group(1)
spl = sent.split("</p>','<p>")
print(spl[0])
signs = (
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
    'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
)
horoscope = {}
for i, sign in enumerate(signs):
    horoscope[sign] = spl[i]
pprint(horoscope, indent=2)
