import InquirerPy
import requests
import os
import sys
import re

from bs4 import BeautifulSoup

from InquirerPy.utils import get_style
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.fuzzy import FuzzyPrompt, InquirerPyFuzzyControl
from InquirerPy.prompts.list import ListPrompt, InquirerPyListControl

from prompt_toolkit import print_formatted_text
from prompt_toolkit.validation import Validator
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText

from typing import (
    List,
    Tuple,
    Optional,
    Union,
)


CLASSES = {
    'faded': '#8e8e93',
    'extra_faded' : '#636366',
    'really_faded': '#48484a',
}
STYLE = get_style(
    {
        'fuzzy_info': CLASSES['faded'],
        'fuzzy_match': '',
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
FUZZY_KEYBINDINGS = {
    'down': [
        {'key': 'down'},
    ],
    'up': [
        {'key': 'up'},
    ],
    'toggle': [
        {'key': 'tab'},
    ],
    'toggle-down': [],
    'toggle-up': [],
    'toggle-all': [
        {'key': 'c-r'},
    ],
    'toggle-all-true': [
        {'key': 'c-a'},
    ],
    'toggle-all-false': [],
}
MARGIN = '  '
MANDATORY_MESSAGE = MARGIN + 'This field is required'


class _InquirerPyFuzzyControl(InquirerPyFuzzyControl):
    def _get_hover_text(self, choice) -> List[Tuple[str, str]]:
        display_choices = []
        display_choices.append(("class:pointer", self._pointer))
        display_choices.append(
            (
                "class:pointer",
                self._marker
                if self.choices[choice["index"]]["enabled"]
                else self._marker_pl,
            )
        )
        display_choices.append(("[SetCursorPosition]", ""))
        display_choices.append(("class:pointer", choice["name"]))
        return display_choices


class _InquirerPyListControl(InquirerPyListControl):
    def _get_hover_text(self, choice) -> List[Tuple[str, str]]:
        display_choices = []
        display_choices.append(("class:pointer", self._pointer))
        display_choices.append(
            (
                "class:pointer",
                self._marker
                if choice["enabled"]
                else self._marker_pl,
            )
        )
        display_choices.append(("[SetCursorPosition]", ""))
        display_choices.append(("class:pointer", choice["name"]))
        return display_choices


InquirerPy.prompts.list.InquirerPyListControl = _InquirerPyListControl
InquirerPy.prompts.fuzzy.InquirerPyFuzzyControl = _InquirerPyFuzzyControl


class Fuzzy(FuzzyPrompt):
    def _generate_after_input(self) -> List[Tuple[str, str]]:
        display_message = []

        if self._info:
            if self._multiselect and self.selected_choices:
                display_message.append(("", "   "))
                display_message.append(("class:fuzzy_info", f"({len(self.selected_choices)} selected)"))

        return display_message
 

class Manga:
    def __init__(self, url: str, title: str) -> None:
        self.url = url
        self.title = title


class Chapter:
    def __init__(self, manga: Manga, url: str, chapter: str, title: str) -> None:
        self.manga = manga
        self.url = url
        self.chapter = chapter
        self.title = title


class Interface:
    def search(self, term: str) -> List[Manga]:
        term = re.sub(r'(?<=[a-zA-Z0-9])[^a-zA-Z0-9]+(?=[a-zA-Z0-9])', '_', term)
        term = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', term).lower()
        
        if term == '':
            return []

        request = requests.get(f'https://h.mangabat.com/search/manga/{term}')
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('div', class_='panel-list-story')

        mangas = []

        if root:
            manga_nodes = root.find_all_next('div', class_='list-story-item')

            for node in manga_nodes:
                url_node = node.find('a', class_='item-img')

                url = url_node.get('href') or ''
                title = url_node.get('title') or ''

                mangas.append(Manga(url, title))

        return mangas

    def get_chapters(self, manga: Manga) -> List[Chapter]:
        request = requests.get(manga.url)
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('ul', class_='row-content-chapter')

        chapters = []
      
        if root:
            chapter_nodes = root.find_all_next('a', class_='chapter-name')

            for node in chapter_nodes:
                title_data = node.get('title')

                url = node.get('href')
                chapter = re.search(r'[Cc]hapter[ \t]+([\d.]+)', title_data)
                chapter = chapter.group(1) if chapter else ''
                title = re.split(r'\s*:\s*', title_data, maxsplit=1)
                title = title[1] if len(title) > 1 else ''

                chapters.append(Chapter(manga, url, chapter, title))

        return chapters

    def fetch_chapter_images(self, chapter: Chapter) -> List[bytes]:
        if not chapter.url:
            return []

        request = requests.get(chapter.url)
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('div', class_='container-chapter-reader')

        binary_images = []

        if root:

            image_urls = [i.get('src') for i in root.find_all_next('img', class_='img-content')]
            headers = {'Referer': 'https://www.readmangabat.com'}
            
            for url in image_urls:
                binary_images.append(requests.get(url, headers=headers).content)

        return binary_images
  

class UI:
    def _fmt_selected_items(self, items: List[Chapter]) -> str:
        fmt_string = f'\n{MARGIN}' + f'\n{MARGIN}'.join(items[:10])

        if len(items) > 10:
            fmt_string += '\n' + MARGIN * 2 + f'...{len(items)-10} more'

        return fmt_string
    
    def _full_just_items(self, items: List[Union[Choice, str]]) -> List[Union[Choice, str]]:
        width, _ = os.get_terminal_size()
        full_just = lambda x: x.ljust(width-2)
        fmt_items = []

        for item in items:
            if type(item) == Choice:
                fmt_line = full_just(item.name)
                fmt_items.append(Choice(name=fmt_line, value=item.value, enabled=item.enabled))
            else:
                fmt_items.append(full_just(item))
        
        return fmt_items

    def select(self, items: List[Union[Choice, str]], title: str, item_count_singular: str, item_count_plural: str, message: Optional[str] = None) -> ListPrompt:
        return ListPrompt(
            message=message if message else title,
            choices=self._full_just_items(items),
            transformer=lambda x: f'\n{MARGIN}{x}',
            show_cursor=False,
            mandatory_message=MANDATORY_MESSAGE,
            long_instruction=MARGIN + self.fmt_count_str(len(items), item_count_singular, item_count_plural),
            style=STYLE,
            qmark=' ',
            amark=' ',
            pointer='',
            border=True,
            cycle=False,
        )
    
    def fuzzy(self, items: List[Union[Choice, str]], title: str, item_count_singular: str, item_count_plural: str) -> Fuzzy:
        return Fuzzy(
            prompt='',
            multiselect=True,
            marker='✔ ',
            marker_pl='  ',
            message=title,
            choices=self._full_just_items(items),
            transformer=self._fmt_selected_items,
            mandatory_message=MANDATORY_MESSAGE,
            long_instruction=MARGIN + self.fmt_count_str(len(items), item_count_singular, item_count_plural),
            style=STYLE,
            qmark=' ',
            amark=' ',
            pointer='',
            border=True,
            cycle=False,
            keybindings=FUZZY_KEYBINDINGS,
        )

    def text(self, title: str, validate: Optional[Validator] = None) -> InputPrompt:
        return InputPrompt(
            style=STYLE,
            message=MARGIN + title,
            qmark='',
            amark='',
            mandatory_message=MANDATORY_MESSAGE,
            validate=validate if validate else EmptyInputValidator(message=MANDATORY_MESSAGE),
        )

    def fmt_count_str(self, count: int, name_singular: str, name_plural: str) -> str:
        name_str = name_singular if count == 1 else name_plural
        return f'{count if count else "No"} {name_str}'

    def fmt_count_match(self, count: int) -> str:
        return self.fmt_count_str(count, 'match', 'matches')

    def fmt_count_result(self, count: int) -> str:
        return self.fmt_count_str(count, 'result', 'results')

    def fmt_count_chapter(self, count: int) -> str:
        return self.fmt_count_str(count, 'chapter', 'chapters')

    def clear_line(self) -> str:
        print('\x1b[2K', end='\r')

    def hide_cursor(self) -> str:
        print('\033[?25l', end='\r')

    def show_cursor(self) -> str:
        print('\033[?25h', end='\r')
    
    def print_status(self, status: str, new_line_before: bool = True, ellipsis: bool = True) -> str:
        new_line = '\n' if new_line_before else ''

        self.print([('extra_faded', f'{new_line}{MARGIN}{status}{"..." if ellipsis else ""}')],  margin=False, end='\r')
    
    def print_error(self, error: str) -> None:
        self.print([('extra_faded', error)])

    def print(self, items: List[Tuple[str, str]], clear_line: bool = True, hide_cursor: bool = True, margin: bool = True, **kwargs) -> None:
        if hide_cursor:
            self.hide_cursor()

        if clear_line:
            self.clear_line()

        print_formatted_text(
                FormattedText([(f'class:{class_name}', f'{MARGIN if margin else ""}{line}') for class_name, line in items]),
                style=Style.from_dict(CLASSES),
                **kwargs,
            )


def main():
    interface = Interface()
    ui = UI()

    full_path = lambda x: os.path.abspath(os.path.expanduser(x))
    args = sys.argv[1:]
    download_dir = full_path('.')

    if len(args) == 1:
        download_dir = args[0]

        if not os.path.isdir(download_dir):
            ui.print_error('Invalid path')
            return

        download_dir = full_path(download_dir)

    ui.clear_line()

    search_term = ui.text(
        title='Search',
    ).execute()
    
    ui.print_status('Fetching results')

    mangas = []

    for manga in interface.search(search_term):
        mangas.append(Choice(value=manga, name=manga.title))
    
    ui.clear_line()

    if not mangas:
        ui.print_error('No results found')
        return

    selected_manga = ui.select(
        title='Manga',
        items=mangas,
        item_count_singular='result',
        item_count_plural='results',
    ).execute()

    ui.print_status('Fetching chapters')

    chapters = []

    def fmt_chapter_line(chapter):
        line = []

        if chapter.chapter:
            line.append(chapter.chapter.ljust(8))
        else:
            line.append(''.ljust(8))
        
        if chapter.title:
            line.append(chapter.title)
        
        if not line:
            return ''
        
        return '   '.join(line)


    for chapter in interface.get_chapters(selected_manga):
        line = fmt_chapter_line(chapter)

        if not line:
            continue

        chapters.append(Choice(value=chapter, name=line))

    ui.clear_line()

    if not mangas:
        ui.print_error('No chapters found')
        return

    selected_chapters = ui.fuzzy(
        title='Chapters',
        items=chapters,
        item_count_singular='chapter',
        item_count_plural='chapters',
    ).execute()

    ui.hide_cursor()
    print()

    failed_downloads = []

    def download_images(images):
        for idx, image in enumerate(images):
            with open(f'{str(idx+1).zfill(3)}.jpg', 'wb') as f:
                f.write(image)

    for idx, chapter in enumerate(selected_chapters):
        ui.print_status(f'Downloading {idx+1} of {ui.fmt_count_chapter(len(selected_chapters))}', new_line_before=False)


        if chapter.chapter:
            num_split = chapter.chapter.split('.')
            chapter_dir_name = f'c{num_split[0].zfill(4)}'
            if len(num_split) > 1:
                chapter_dir_name += f'{"." + ".".join(num_split[1:])}'
        else:
            chapter_dir_name = chapter.title

        images = interface.fetch_chapter_images(chapter)

        if not images:
            failed_downloads.append(chapter)
        else:
            local_download_dir = os.path.join(download_dir, chapter.manga.title, os.path.basename(chapter_dir_name))

            os.makedirs(local_download_dir, exist_ok=True)
            os.chdir(local_download_dir)

            download_images(images)
    
    if failed_downloads:
        ui.print([('faded', 'Failed')])
        for chapter in failed_downloads:
            ui.print([('', fmt_chapter_line(chapter))])
        print()

    download_count = len(selected_chapters)-len(failed_downloads)
    ui.print_status(f'Downloaded {download_count} of {ui.fmt_count_chapter(len(selected_chapters))}', new_line_before=False, ellipsis=False)

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        ui = UI()
        ui.clear_line()
        ui.show_cursor()
