import importlib
import os

from InquirerPy import inquirer, get_style
from InquirerPy.base.control import Choice
from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.list import BaseListPrompt
from InquirerPy.utils import patched_print

from utils import Column, Chapter
from math import floor
from textwrap import shorten
from typing import (
    List,
    Tuple,
)


STYLE = get_style(
    {
        'fuzzy_info': '#8e8e93',
        'fuzzy_match': 'bg:#3a3a3c',
        'fuzzy_prompt': '#8e8e93',
        'fuzzy_border': '#48484a',
        'marker': '',
        'input': '', 
        'answer': '',
        'question': '#8e8e93', 
        'pointer': 'bg:#0084ff',
        'validator': 'fg:#ff453a bg:',
        'answered_question': '#8e8e93', 
        'long_instructions': '#8e8e93',
    }, 
    style_override=False
)
SELECT_PARAMS = {
    'style': STYLE,
    'qmark': ' ',
    'amark': ' ',
    'pointer': '',
    'border': True,
}
WIDTH, _ = os.get_terminal_size()
GUTTER = '   '
MARGIN = '  '
MANDATORY_MESSAGE = MARGIN + '{} is required'
COLUMNS_MANGA = [
    Column(35, min_width=10, max_width=50),
    Column(40, min_width=10, max_width=50),
    Column(8, min_width=8, max_width=8, align='r'),
]
COLUMNS_CHAPTER = [
    Column(5, min_width=8, max_width=8, align='r'),
    Column(95, min_width=60, max_width=100),
]


def fmt_count_str(count: int, name_singular: str, name_plural: str) -> str:
    name_str = name_singular if count == 1 else name_plural
    return f'{count if count else "No"} {name_str}'


def fmt_count_match(count: int) -> str:
    return fmt_count_str(count, 'match', 'matches')


def fmt_count_result(count: int) -> str:
    return fmt_count_str(count, 'result', 'results')


def fmt_count_chapter(count: int) -> str:
    return fmt_count_str(count, 'chapter', 'chapters')


class ov_FuzzyPrompt(FuzzyPrompt, BaseListPrompt):
    def _generate_after_input(self) -> List[Tuple[str, str]]:
        display_message = []

        if self._info:
            match_count = fmt_count_match(self.content_control.choice_count)

            display_message.append(("", "   "))

            if not self.selected_choices:
                return display_message + [("class:fuzzy_info", f'({match_count})')]

            display_message.append(("class:fuzzy_info", f'({match_count}'))
            display_message.append(("class:fuzzy_info", f", {len(self.selected_choices)} selected)"))

        return display_message


def fmt_line(items: Tuple[str], columns: List[Column]) -> str:
    fmt_line = ''

    for col_string, col in zip(items, columns):
        if not col_string:
            col_string = ''

        str(col_string)

        width = floor(WIDTH * (col.width / 100))

        if width > col.max_width:
            width = col.max_width
        elif width < col.min_width:
            width = col.min_width
        
        col_string = shorten(col_string, width=width, placeholder='..')

        if col.align == 'l':
            col_string = col_string.ljust(width)
        elif col.align == 'r':
            col_string = col_string.rjust(width)
        
        fmt_line += col_string + GUTTER

    return fmt_line.ljust(WIDTH-3)


def print_status(status: str) -> str:
    hide_cursor()
    print(f'\n  {status}...', end='\r')


def clear_line() -> str:
    print('\x1b[2K', end='\r')


def hide_cursor() -> str:
    print('\033[?25l', end='\r')


def show_cursor() -> str:
    print('\033[?25h', end='\r')


def main() -> None:
    plugins = []

    for f in os.listdir('plugins'):
        if f.endswith('py'):
            plugins.append(os.path.splitext(f)[0])

    plugin = inquirer.select(
        message='Select plugin',
        choices=plugins,
        transformer=lambda x: f'\n{MARGIN}{x}',
        show_cursor=False,
        mandatory_message=MANDATORY_MESSAGE.format('Plugin'),
        long_instruction=MARGIN + fmt_count_result(len(plugins)),
        **SELECT_PARAMS
    ).execute()

    print_status('Loading plugin')

    plugin = importlib.import_module('plugins.' + plugin).Plugin()

    clear_line()

    search_term = inquirer.text(
        style=STYLE,
        message='  Search',
        qmark='',
        amark='',
        mandatory=True,
        mandatory_message=MANDATORY_MESSAGE.format('Search Term')
    ).execute()
    
    print_status('Fetching results')

    mangas = []

    for manga in plugin.search(search_term):
        fmt_item = fmt_line((manga.name_str, manga.authors_str, manga.num_chapters), COLUMNS_MANGA)
        mangas.append(Choice(manga, name=fmt_item))

    if not mangas:
        print(MARGIN + 'No results')
        return

    manga_headers = fmt_line(('Name', 'Author', 'Chapters'), COLUMNS_MANGA)

    clear_line()

    selected_manga = inquirer.select(
        message=manga_headers,
        choices=mangas,
        transformer=lambda x: '\n  ' + x,
        show_cursor=False,
        mandatory_message=MANDATORY_MESSAGE.format('Manga'),
        long_instruction=MARGIN + fmt_count_result(len(mangas)),
        **SELECT_PARAMS
    ).execute()

    print_status('Fetching chapters')

    if not selected_manga.num_chapters:
        print(MARGIN + 'No chapters')
        return

    chapters = []


    for chapter in plugin.get_chapters(selected_manga):
        fmt_item = fmt_line((chapter.num, chapter.name_str), COLUMNS_CHAPTER)
        chapters.append(Choice(chapter, name=fmt_item))

    chapter_headers = fmt_line(('Chapter', 'Name'), COLUMNS_CHAPTER)

    def _print_selected_chapters(chapters: List[Chapter]) -> str:
        fmt_string = f'\n{MARGIN}' + f'\n{MARGIN}'.join(chapters[:10])

        if len(chapters) > 10:
            fmt_string += '\n' + MARGIN * 2 + f'... {len(chapters)-9} more selected'

        return fmt_string
            
    clear_line()

    selected_chapters = ov_FuzzyPrompt(
        prompt=' Search',
        multiselect=True,
        marker='*',
        message=chapter_headers,
        choices=chapters,
        transformer=_print_selected_chapters,
        mandatory_message=MANDATORY_MESSAGE.format('Chapter'),
        long_instruction=MARGIN + fmt_count_chapter(len(chapters)),
        **SELECT_PARAMS
    ).execute()

    hide_cursor()

    print()

    failed_downloads = []

    for idx, chapter in enumerate(selected_chapters):
        print_status(f'Downloading {idx+1} of {fmt_count_chapter(len(selected_chapters))}')

        try:
            plugin.download_chapter(chapter, '.')
        except RuntimeError:
            failed_downloads.append(chapter)

    
    print(f'\x1b[2K  Downloaded {fmt_count_chapter(len(selected_chapters))}\033[?25h')

    if failed_downloads:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_line()
        show_cursor()