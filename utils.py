from typing import (
    List,
    Optional
)
from abc import ABC, abstractmethod

class Manga:
    def __init__(self, url: str, name: str, authors: List[str], num_chapters: str) -> None:
        self.url = url
        self.name = name
        self.authors = authors
        self.num_chapters = num_chapters

        self.name_str = self.name if self.name else '[Unknown]'
        self.authors_str = ', '.join(self.authors)

class Chapter:
    def __init__(self, url: str, num: str, name: str) -> None:
        self.url = url
        self.num = num
        self.name = name

        self.name_str = self.name if self.name else '[Unknown]'

class Interface(ABC):
    @abstractmethod
    def search(self, term: str) -> List[Manga]:
        pass

    @abstractmethod
    def get_chapters(self, manga: Manga) -> List[Chapter]:
        pass

    @abstractmethod
    def download_chapter(self, chapter: Chapter, download_dir: str) -> None:
        pass

class Column:
    def __init__(self, width: int, min_width: Optional[int] = None, max_width: Optional[int] = None, align: Optional[str] = 'l') -> None:
        self.width = width
        self.min_width = min_width
        self.max_width = max_width
        self.align = align