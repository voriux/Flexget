from __future__ import unicode_literals, division, absolute_import
import logging

from requests.auth import AuthBase

from flexget import plugin
from flexget.entry import Entry
from flexget.event import event
from flexget.utils import requests
from flexget.utils.imdb import extract_id
from flexget.utils.soup import get_soup
from flexget.utils.search import torrent_availability

log = logging.getLogger('search_linkomanija')


class CookieAuth(AuthBase):
    def __init__(self, cookies):
        self.cookies = cookies

    def __call__(self, r):
        r.prepare_cookies(self.cookies)
        return r


categories = {
    'MoviesHD': 'c52',
    'MoviesLTHD': 'c61',
    'Movies': 'c29',
    'MoviesLT': 'c53',
    'TVHD': 'c60',
    'TVLTHD': 'c62',
    'TV': 'c30',
    'TVLT': 'c28'
}


class SearchLM(object):
    schema = {
        'type': 'object',
        'properties': {
            'username': {'type': 'string'},
            'password': {'type': 'string'},
            'categories': {
                'type': 'array',
                'items': {'type': 'string', 'enum': list(categories)}
            }
        },
        'required': ['username', 'password'],
        'additionalProperties': False
    }

    def search(self, entry, config):
        login_sess = requests.Session()
        login_params = {'username': config['username'],
                        'password': config['password']}
        try:
            login_sess.post('http://www.linkomanija.net/takelogin.php', data=login_params, verify=False)
        except requests.RequestException as e:
            log.error('Error while logging in to Linkomanija: %s', e)

        download_auth = CookieAuth(login_sess.cookies)
        # Default to searching by title (0=title 3=imdb_id)
        search_by = 0
        if 'imdb_id' in entry:
            searches = [entry['imdb_id']]
            search_by = 3
        elif 'movie_name' in entry:
            search = entry['movie_name']
            if 'movie_year' in entry:
                search += ' %s' % entry['movie_year']
            searches = [search]
        else:
            searches = entry.get('search_strings', [entry['title']])

        params = {'_by': search_by}
        if config.get('categories'):
            for cat in config['categories']:
                params[categories[cat]] = 1
        results = set()
        for search in searches:
            params['search'] = search
            try:
                r = login_sess.get('http://www.linkomanija.net/browse.php', params=params)
            except requests.RequestException as e:
                log.error('Error searching LM: %s' % e)
                continue
            soup = get_soup(r.text)
            if 'prisijungimas' in soup.head.title.text.lower():
                log.error('LM cookie info invalid')
                raise plugin.PluginError('LM cookie info invalid')
            try:
                results_table = soup.find_all('table', attrs={'border': '1'}, limit=1)[0]
            except IndexError:
                log.debug('No results found for `%s`' % search)
                continue
            for row in results_table.find_all('tr')[1:]:
                columns = row.find_all('td')
                entry = Entry()
                links = columns[1].find_all('a', recursive=False, limit=2)
                entry['title'] = links[0].text
                if len(links) > 1:
                    entry['imdb_id'] = extract_id(links[1].get('href'))
                entry['url'] = 'http://www.linkomanija.net/' + columns[2].a.get('href')
                entry['download_auth'] = download_auth
                entry['torrent_seeds'] = int(columns[7].text)
                entry['torrent_leeches'] = int(columns[8].text)
                entry['search_sort'] = torrent_availability(entry['torrent_seeds'], entry['torrent_leeches'])
                size = columns[5].find('br').previous_sibling
                unit = columns[5].find('br').next_sibling
                if unit == 'GB':
                    entry['content_size'] = int(float(size) * 1024)
                elif unit == 'MB':
                    entry['content_size'] = int(float(size))
                elif unit == 'KB':
                    entry['content_size'] = int(float(size) / 1024)
                results.add(entry)
        return results


@event('plugin.register')
def register_plugin():
    plugin.register(SearchLM, 'lm', groups=['search'], api_ver=2)
