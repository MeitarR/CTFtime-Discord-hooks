import argparse
import requests
import datetime

from typing import List, Union
from datetime import datetime, timedelta
from DiscordHooks import Hook, Embed, EmbedThumbnail, EmbedFooter, EmbedField
from numpy import datetime64

DEFAULT_ICON = 'https://pbs.twimg.com/profile_images/2189766987/ctftime-logo-avatar_400x400.png'
TIME_FORMAT = '%Y-%m-%dT%H%M%S%z'
BASE_URL = 'https://ctftime.org'


class CTF:
    cid: int
    url: str
    name: str
    logo: str
    format: str
    location: str
    start: datetime
    description: str
    restrictions: str
    duration: timedelta
    fields: dict

    def __init__(self, json_obj: dict):
        self.cid = json_obj.get('id', 0)
        self.url = json_obj.get('url', '')
        if self.url == '':
            self.url = json_obj.get('ctftime_url', '')
        self.name = json_obj.get('title')
        if self.name is None or self.name == '':
            self.name = 'Unnamed'
        self.logo = CTF.parse_logo_url(json_obj.get('logo', ''))
        self.format = json_obj.get('format')
        if self.format is None or self.format == '':
            self.format = 'Unknown'
        if json_obj.get('onsite', False):
            self.location = json_obj.get('location')
            if self.location is None or self.location == '':
                self.location = 'Unknown'
        else:
            self.location = 'online'
        self.start = CTF.parse_time(json_obj.get('start', '1970-01-01T00:00:00+00:00'))
        self.finish = CTF.parse_time(json_obj.get('finish', '1970-01-01T00:00:00+00:00'))

        self.description = json_obj.get('description')
        if self.description is None or self.description == '':
            self.description = 'No description :shrug:'
        elif len(self.description) > 2048:
            self.description = self.description[:2044] + '...'

        self.restrictions = json_obj.get('restrictions')
        if self.restrictions is None or self.restrictions == '':
            self.restrictions = 'Unknown'
        self.duration = timedelta(**json_obj.get('duration', dict()))
        
        self.fields = [{
            "name": "Weight",
            "value": str(json_obj.get('weight', 0.0))
        },{
            "name": "Interested teams",
            "value": str(json_obj.get('participants', 0))
        }]

    def generate_embed(self):
        return Embed(
                        title=self.name, color=0xFF0035, url=self.url, description=self.description,
                        timestamp=self.start, thumbnail=EmbedThumbnail(url=self.logo), fields=self.fields,
                        footer=EmbedFooter(text=f' ⏳ {self.duration} | 📌 {self.location} |'
                                             f' ⛳ {self.format} | 👮 {self.restrictions} | '
                                          )
                    )

    @staticmethod
    def parse_logo_url(url: str) -> str:
        if url is None or url == '':
            return DEFAULT_ICON
        elif url.startswith('/'):
            return BASE_URL + url
        else:
            return url

    @staticmethod
    def parse_time(time: str) -> datetime:
        if time is None or time == '':
            time = '1970-01-01T00:00:00+00:00'
        return datetime.strptime(time.replace(':', ''), TIME_FORMAT)

def get_ctfs(max_ctfs: int, days: int) -> List[CTF]:
    start = datetime.now()
    end = start + timedelta(days=days)
    url = f'https://ctftime.org/api/v1/events/?limit={max_ctfs}' \
          f'&start={int(start.timestamp())}&finish={int(end.timestamp())}'

    return [CTF(entry) for entry in requests.get(url, headers={'user-agent': ''}).json()]


def build_message(max_ctfs: int, days: int, cache_path: str) -> Union[Hook, None]:
    cache = ''
    if cache_path:
        with open(cache_path) as f:
            cache = f.read().strip()

    ctfs = get_ctfs(max_ctfs, days)
    embeds = [ctf.generate_embed() for ctf in ctfs]
    ids = ','.join([str(ctf.cid) for ctf in ctfs])
    if cache == ids:
        return None
    else:
        if cache_path:
            with open(cache_path, 'w') as f:
                f.write(ids)
        return Hook(username='CTFtime', content=f'There are {len(embeds)} CTFs during the upcoming {days} days', embeds=embeds, avatar_url=DEFAULT_ICON)


def send_updates(webhooks: List[str], max_ctfs: int, days: int, cache_path: str):
    message = build_message(max_ctfs=max_ctfs, days=days, cache_path=cache_path)
    if message is not None:
        for webhook in webhooks:
            message.execute(hook_url=webhook)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    webhooks_group = parser.add_mutually_exclusive_group(required=True)
    webhooks_group.add_argument('-w', '--webhooks', metavar='url', nargs='+',
                                help='a discord webhook which the data will be send to')
    webhooks_group.add_argument('-W', '--webhooks-file', metavar='path',
                                help='a path to file with discord webhooks (line separated)')

    parser.add_argument('-c', '--cache-file', metavar='path', default=None,
                        help='a path to file that will be used to cache sent entries')

    parser.add_argument('-m', '--max-entries', metavar='number', type=int, default=3,
                        help='the maximum number of CTFs that will be sent')
    parser.add_argument('-d', '--days', metavar='number', type=int, default=10,
                        help='days from today to search CTFs within')
    args = parser.parse_args()

    if args.webhooks_file:
        with open(args.webhooks_file) as f:
            args_webhooks = [line.strip() for line in f]
    else:
        args_webhooks = args.webhooks

    if args.cache_file:
        try:
            open(args.cache_file, "x").close()
        except FileExistsError:
            pass

    send_updates(webhooks=args_webhooks, max_ctfs=args.max_entries, days=args.days, cache_path=args.cache_file)
