from __future__ import unicode_literals, division, absolute_import
import logging
import re

import guessit

from flexget.utils.titles.parser import TitleParser
from flexget.utils import qualities
from flexget.utils.tools import str_to_int

log = logging.getLogger('movieparser')


def diff_pos(string1, string2):
    """Returns first position where string1 and string2 differ."""
    for (count, c) in enumerate(string1):
        if len(string2) <= count:
            return count
        if string2[count] != c:
            return count


class MovieParser(TitleParser):

    def __init__(self):
        self.data = None
        self.reset()
        TitleParser.__init__(self)

    def reset(self):
        # parsing results
        self.name = None
        self.year = None
        self.quality = qualities.Quality()
        self.proper_count = 0

    def __str__(self):
        return "<MovieParser(name=%s,year=%s,quality=%s)>" % (self.name, self.year, self.quality)

    def parse(self, data=None):
        """Parse movie name. Populates name, year, quality and proper_count attributes"""

        # Reset before parsing, so the parser can be reused.
        self.reset()

        if data is None:
            data = self.data

        result = guessit.guess_movie_info(data, options={'name_only': True})
        self.name = result.get('title')
        self.year = result.get('year')
        self.quality = qualities.Quality(' '.join(filter(None, [result.get('screenSize'), result.get('format'), result.get('videoCodec'), result.get('audioCodec')])))
        for item in result.get('other', []):
            if item.lower() in self.propers:
                self.proper_count += 1
