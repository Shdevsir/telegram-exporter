from dataclasses import dataclass
from dataclasses import field

from src.utils.file_manager import FileManager


@dataclass
class StatItem:
    count: int = 0
    size: int = 0

    @property
    def formatted_size(self) -> str:
        return FileManager.format_size(self.size)


@dataclass
class ChatStats:
    total: StatItem = field(default_factory=StatItem)
    text: StatItem = field(default_factory=StatItem)
    photos: StatItem = field(default_factory=StatItem)
    videos: StatItem = field(default_factory=StatItem)
    voice: StatItem = field(default_factory=StatItem)
    rounds: StatItem = field(default_factory=StatItem)
    audios: StatItem = field(default_factory=StatItem)
    files: StatItem = field(default_factory=StatItem)
    stickers: StatItem = field(default_factory=StatItem)
    gifs: StatItem = field(default_factory=StatItem)
    links: int = 0
    service: int = 0

    def to_dict(self) -> dict:
        return {
            "Total Messages": [self.total.count, self.total.formatted_size],
            "Text/Captions": [self.text.count, self.text.formatted_size],
            "Photos": [self.photos.count, self.photos.formatted_size],
            "Videos": [self.videos.count, self.videos.formatted_size],
            "Voice Messages": [self.voice.count, self.voice.formatted_size],
            "Round Videos": [self.rounds.count, self.rounds.formatted_size],
            "Audios": [self.audios.count, self.audios.formatted_size],
            "Files": [self.files.count, self.files.formatted_size],
            "Stickers": [self.stickers.count, self.stickers.formatted_size],
            "GIFs": [self.gifs.count, self.gifs.formatted_size],
            "Links": [self.links, "-"],
            "Service Messages": [self.service, "-"],
        }
