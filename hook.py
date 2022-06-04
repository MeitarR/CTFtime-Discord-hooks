import os
from time import timezone
from typing import List, Union
from datetime import datetime, timedelta
import requests
from DiscordHooks import Hook, Embed, EmbedThumbnail, EmbedFooter

DEFAULT_ICON = (
    "https://pbs.twimg.com/profile_images/2189766987/ctftime-logo-avatar_400x400.png"
)
TIME_FORMAT = "%Y-%m-%dT%H%M%S%z"
BASE_URL = "https://ctftime.org"

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

    def __init__(self, json_obj: dict):
        self.cid = json_obj.get("id", 0)
        self.url = json_obj.get("url", "")
        if self.url == "":
            self.url = json_obj.get("ctftime_url", "")
        self.name = json_obj.get("title")
        if self.name is None or self.name == "":
            self.name = "Unnamed"
        self.logo = CTF.parse_logo_url(json_obj.get("logo", ""))
        self.format = json_obj.get("format")
        if self.format is None or self.format == "":
            self.format = "Unknown"
        if json_obj.get("onsite", False):
            self.location = json_obj.get("location")
            if self.location is None or self.location == "":
                self.location = "Unknown"
        else:
            self.location = "online"
        self.start = CTF.parse_time(json_obj.get("start", "1970-01-01T00:00:00+00:00"))

        self.description = json_obj.get("description")
        if self.description is None or self.description == "":
            self.description = "No description :shrug:"
        elif len(self.description) > 2048:
            self.description = self.description[:2044] + "..."

        self.restrictions = json_obj.get("restrictions")
        if self.restrictions is None or self.restrictions == "":
            self.restrictions = "Unknown"
        self.duration = timedelta(**json_obj.get("duration", dict()))

    def generate_embed(self):
        return Embed(
            title=self.name,
            color=0xFF0035,
            url=self.url,
            description=self.description,
            timestamp=self.start,
            thumbnail=EmbedThumbnail(url=self.logo),
            footer=EmbedFooter(
                text=f" ⏳ {self.duration} | 📌 {self.location} |"
                f" ⛳ {self.format} | 👮 {self.restrictions}"
            ),
        )

    @staticmethod
    def parse_logo_url(url: str) -> str:
        if url is None or url == "":
            return DEFAULT_ICON
        elif url.startswith("/"):
            return BASE_URL + url
        else:
            return url

    @staticmethod
    def parse_time(time: str) -> datetime:
        if time is None or time == "":
            time = "1970-01-01T00:00:00+00:00"
        return datetime.strptime(time.replace(":", ""), TIME_FORMAT)


def get_ctfs(max_ctfs: int, days: int) -> List[CTF]:
    start = datetime.now()
    end = start + timedelta(days=days)
    url = (
        f"https://ctftime.org/api/v1/events/?limit={max_ctfs}"
        f"&start={int(start.timestamp())}&finish={int(end.timestamp())}"
    )

    return [
        CTF(entry) for entry in requests.get(url, headers={"user-agent": ""}).json()
    ]


def build_message(max_ctfs: int, days: int) -> Union[Hook, None]:
    ctfs = get_ctfs(max_ctfs, days)
    embeds = [ctf.generate_embed() for ctf in ctfs]
    return Hook(
        username="CTFTime",
        content=f"CTFs during the upcoming {days} days:",
        embeds=embeds,
        avatar_url=DEFAULT_ICON,
    )

def send_updates(webhooks: List[str], max_ctfs: int, days: int):
    message = build_message(max_ctfs=max_ctfs, days=days)
    if message is not None:
        for webhook in webhooks:
            message.execute(hook_url=webhook)

def handler(event=None, context=None):
    webhook = os.getenv("DISCORD_WEBHOOK")
    max_ctfs = int(os.getenv("MAX_CTFS"))
    days = int(os.getenv("DAYS"))
    send_updates([webhook], max_ctfs, days)
