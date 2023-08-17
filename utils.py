import os

from InquirerPy import get_style
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
    def __init__(self, manga: Manga, url: str, num: str, name: str) -> None:
        self.manga = manga
        self.url = url
        self.num = num
        self.name = name

        self.num_str = ''

        if self.num:
            ch_nums = self.num.split('.')
            self.num_str = f'c{ch_nums[0].zfill(4)}{"".join(ch_nums[:-1])}'
        self.name_str = self.name if self.name else '[Unknown]'

class Interface(ABC):
    @abstractmethod
    def search(self, term: str) -> List[Manga]:
        pass

    @abstractmethod
    def get_chapters(self, manga: Manga) -> List[Chapter]:
        pass

    @abstractmethod
    def fetch_chapter_images(self, chapter: Chapter) -> None:
        pass

class Column:
    def __init__(self, width: int, name: str, min_width: Optional[int] = None, max_width: Optional[int] = None, align: Optional[str] = 'l') -> None:
        self.width = width
        self.name = name
        self.min_width = min_width
        self.max_width = max_width
        self.align = align


CONFIG_DIR = '.config'
CLASSES = {
    'faded': '#8e8e93',
    'extra_faded' : '#636366',
    'really_faded': '#48484a',
}
STYLE = get_style(
    {
        'fuzzy_info': CLASSES['faded'],
        'fuzzy_match': 'bg:#3a3a3c',
        'fuzzy_prompt': CLASSES['faded'],
        'fuzzy_border': CLASSES['really_faded'],
        'marker': '',
        'input': '', 
        'answer': '',
        'question': CLASSES['faded'], 
        'pointer': 'bg:#0084ff',
        'validator': 'fg:#ff453a bg:',
        'answered_question': CLASSES['faded'], 
        'long_instructions': CLASSES['faded'],
    }, 
    style_override=False
)
WIDTH, _ = os.get_terminal_size()
GUTTER = '   '
MARGIN = '  '
MANDATORY_MESSAGE = MARGIN + 'This field is required'
COLUMNS_MANGA = [
    Column(35, min_width=10, max_width=50, name='Name'),
    Column(40, min_width=10, max_width=50, name='Author'),
    Column(8, min_width=8, max_width=8, align='r', name='Chapters'),
]
COLUMNS_CHAPTER = [
    Column(5, min_width=8, max_width=8, align='r', name='Chapter'),
    Column(95, min_width=60, max_width=100, name='Name'),
]