"""Generate goship_ref_secs.html

Original spreadsheet
https://docs.google.com/spreadsheet/ccc?key=0Aj_B1luotypidDlVSGF2TTNQYmVQMXhTRTlNT2VwMWc&usp=sharing

"""
import os.path
import re
from csv import reader as csv_reader
from operator import attrgetter
from collections import OrderedDict

from jinja2 import Environment, FileSystemLoader, contextfunction
from hyde.plugin import Plugin
from hyde.ext.templates.jinja import Jinja2Template

import translitcodec


# http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = word.encode('translit/long')
        if word:
            result.append(word)
    return unicode(delim.join(result))


known_sections = {
    'A01E/AR7E': 'A01E',
    'A01W / AR7W': 'A01W',
    'A02 (SFB-460)': 'A02',
    'A9 1/2': 'AO95',
    'FICARAM (A17)': 'A17',
    'I02 + I10': 'I02',
    'OVIDE (A25)': 'A25',
    'P14S/C': 'P14S',
    'S04P (modified)': 'S04P',
    'SR1b (eastern\npassage)': 'SR01',
}


class Section(object):
    def __init__(self, section=u'', decadally=False, description=u'', past=None,
                 future=None):
        self.section = section
        self.decadally = decadally
        self.description = description
        if past is None:
            past = []
        if future is None:
            future = []
        self.past = past
        self.future = future

    @property
    def nice_section(self):
        try:
            return known_sections[self.section]
        except KeyError:
            return self.section

    def __eq__(self, other):
        return self.nice_section == other.nice_section

    def __lt__(self, other):
        return self.nice_section < other.nice_section

    def __repr__(self):
        return u'Section({0!r}, {1!r}, {2!r})'.format(
            self.section, self.decadally, self.description)


class Cruise(object):
    def __init__(self, year=u'', chisci=u'', country=u'', last=u'', expos=None):
        self.year = year
        self.chisci = chisci
        self.country = country
        self.last = last
        if expos is None:
            expos = []
        self.expos = expos

    @property
    def intyear(self):
        try:
            return int(self.year)
        except ValueError:
            return None

    def __repr__(self):
        return u'Cruise({0!r}, {1!r}, {2!r}, {3!r}, {4!r})'.format(
            self.year, self.chisci, self.country, self.last, self.expos)


class Basin(list):
    def __init__(self, name):
        self.name = name


def find_first_spot(l, x):
    for i, y in enumerate(l):
        if x >= y:
            return i
    return -1


def find_first(l, x):
    for i, y in enumerate(l):
        if y.nice_section == x:
            return i
    return -1


@contextfunction
def get_basins():
    csv_path = os.path.join(os.path.dirname(__file__), 'goship_ref_secs.csv')

    basins = OrderedDict()
    with open(csv_path) as f:
        reader = csv_reader(f)
        reader.next()

        basin = None
        section = None
        for row in reader:
            row = [unicode(c, 'utf-8') for c in row]
            if not any(row[1:]):
                # basin header
                basin = Basin(row[0])
                basins[row[0]] = basin
            elif row[0] == 'Section':
                # header, ignore
                continue
            else:
                if basin is None:
                    raise ValueError('reached cruise before basin')
                name, dec, descr, year, chisci, country, past, expos = row
                dec = dec.startswith('y')
                past = past.startswith('y')
                if not expos:
                    expos = []
                else:
                    expos = [x.strip() for x in expos.split(',')]

                cruise = Cruise(year, chisci, country, past, expos)
                if not any(row[0:3]):
                    # same section as previous
                    if section is None:
                        raise ValueError('reached cruise before section')
                else:
                    section = Section(name, dec, descr)
                    basin.append(section)
                if past:
                    section.past.append(cruise)
                else:
                    section.future.append(cruise)

    # Move older cruises out of next occupation into recent and limit the number
    # of recent to 2
    for basin in basins.values():
        for section in basin:
            cs_in_past = []
            for c in section.future:
                if c.intyear is None:
                    continue
                if c.intyear <= 2011:
                    cs_in_past.append(c)
            for c in cs_in_past:
                section.future.remove(c)
            section.past.extend(cs_in_past)
            section.past = sorted(section.past, key=attrgetter('intyear'))[-2:]

    updates_from_agu_2012 = {
        'AR07W': Cruise('2014'),
        'A05': Cruise('2015'),

        'SR01': [Cruise(year=u'2013'), Cruise(year=u'2014')],
        'P15S': Cruise(year=u'2015/2016', country=u'Australia'),
        'I09S': Cruise(year=u'2013'),
        'P01': Cruise(year=u'2014'),
        'P10': Cruise(year=u'2011', expos=[]),
    }

    atlantic = basins['Atlantic']
    sec_ar7w = atlantic[find_first(atlantic, 'A01W')]
    sec_ar7w.past.extend(sec_ar7w.future)
    sec_ar7w.past = sec_ar7w.past[-2:]
    sec_ar7w.future = [Cruise(u'2014')]

    atlantic[find_first(atlantic, 'A05')].future.append(Cruise(u'2015'))
    atlantic[find_first(atlantic, 'SR01')].future.append(Cruise(u'2013/2014'))

    pacific = basins['Pacific']
    pacific[find_first(pacific, 'P15S')].future = [
        Cruise(u'2015/2016', country=u'Australia')]
    pacific[find_first(pacific, 'P01')].future = [Cruise(u'2014')]
    pacific[find_first(pacific, 'P10')].future = [
        Cruise(u'2011', country=u'Japan', expos=[
            '49NZ20111220', '49NZ20120113'])]

    indian = basins['Indian']
    indian[find_first(indian, 'I09S')].future[0].year = u'2013'
    return basins.values()


class RefSecsPlugin(Plugin):
    def __init__(self, site):
        super(RefSecsPlugin, self).__init__(site)

    def begin_text_resource(self, resource, text):
        env = self.template.env
        env.globals['slugify'] = slugify
        env.globals['basins'] = get_basins()
