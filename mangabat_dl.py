import InquirerPy
import requests
import os
import sys
import re
import zipfile

from InquirerPy.utils import get_style
from InquirerPy.base.control import Choice
from InquirerPy.validator import EmptyInputValidator
from InquirerPy.prompts.input import InputPrompt
from InquirerPy.prompts.fuzzy import FuzzyPrompt, InquirerPyFuzzyControl
from InquirerPy.prompts.list import ListPrompt, InquirerPyListControl

from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import (
    List,
    Tuple,
    Optional,
    Union,
    Callable,
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
WIDTH, _ = os.get_terminal_size()

SANITIZE_FILENAME = lambda x: os.path.basename(x)
ABSOLUTE_PATH = lambda x: os.path.abspath(os.path.expanduser(x))
IMAGE_FILENAME = lambda idx, ext: f'{str(idx+1).zfill(3)}{ext if ext else ".jpg"}'


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
        display_choices.append(("class:pointer", choice["name"].ljust(WIDTH)))
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
        display_choices.append(("class:pointer", choice["name"].ljust(WIDTH)))
        return display_choices


InquirerPy.prompts.list.InquirerPyListControl = _InquirerPyListControl
InquirerPy.prompts.fuzzy.InquirerPyFuzzyControl = _InquirerPyFuzzyControl


class _FuzzyPrompt(FuzzyPrompt):
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

    def fetch_chapter_images(self, chapter: Chapter) -> List[Tuple[bytes, str]]:
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
                path = urlparse(url).path
                ext = os.path.splitext(path)[1]
                binary_images.append((requests.get(url, headers=headers).content, ext))

        return binary_images
  

class UI:
    def _fmt_selected_items(self, items: List[str]) -> str:
        fmt_string = f'\n{MARGIN}' + f'\n{MARGIN}'.join(items[:10])

        if len(items) > 10:
            fmt_string += '\n' + MARGIN * 2 + f'...{len(items)-10} more'

        return fmt_string
    
    def select(self, items: List[Union[Choice, str]], title: str, item_count_singular: str, item_count_plural: str, message: Optional[str] = None) -> ListPrompt:
        return ListPrompt(
            message=message if message else title,
            choices=items,
            style=STYLE,
            qmark=' ',
            amark=' ',
            pointer='',
            long_instruction=MARGIN + self.fmt_count(len(items), item_count_singular, item_count_plural),
            transformer=lambda x: f'\n{MARGIN}{x}',
            border=True,
            show_cursor=False,
            cycle=False,
            mandatory_message=MANDATORY_MESSAGE,
        )
    
    def fuzzy(self, items: List[Union[Choice, str]], title: str, item_count_singular: str, item_count_plural: str) -> _FuzzyPrompt:
        return _FuzzyPrompt(
            message=title,
            choices=items,
            pointer='',
            style=STYLE,
            qmark=' ',
            amark=' ',
            transformer=self._fmt_selected_items,
            long_instruction=MARGIN + self.fmt_count(len(items), item_count_singular, item_count_plural),
            multiselect=True,
            prompt='',
            marker='✔ ',
            marker_pl='  ',
            border=True,
            mandatory_message=MANDATORY_MESSAGE,
            cycle=False,
            keybindings=FUZZY_KEYBINDINGS,
        )

    def text(self, title: str) -> InputPrompt:
        return InputPrompt(
            message=MARGIN + title,
            style=STYLE,
            qmark='',
            amark='',
            validate=EmptyInputValidator(message=MANDATORY_MESSAGE),
            mandatory_message=MANDATORY_MESSAGE,
        )

    def fmt_count(self, count: int, name_singular: str, name_plural: str) -> str:
        name_str = name_singular if count == 1 else name_plural
        return f'{count if count else "No"} {name_str}'

    def clear_line(self) -> None:
        print('\x1b[2K', end='\r')

    def hide_cursor(self) -> None:
        print('\033[?25l', end='\r')

    def show_cursor(self) -> None:
        print('\033[?25h', end='\r')

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

    def print_status(self, status: str, new_line_before: bool = True, ellipsis: bool = True) -> str:
        new_line = '\n' if new_line_before else ''
        line = f'{new_line}{MARGIN}{status}{"..." if ellipsis else ""}'

        self.print([('extra_faded', line)], margin=False, end='\r')
    
    def print_error(self, error: str) -> None:
        self.print([('extra_faded', error)])


class Main:
    def __init__(self) -> None:
        self.interface = Interface()
        self.ui = UI()
        self.download_path = ABSOLUTE_PATH('.')
        self.download_formats = [
            {'ext': '.zip', 'name': 'ZIP', 'method': self.download_as_archive},
            {'ext': '.cbz', 'name': 'CBZ', 'method': self.download_as_archive},
            {'ext': '.jpg', 'name': 'JPEG', 'method': self.download_as_images},
        ]

        args = sys.argv[1:]

        if len(args) == 1:
            path = args[0]

            if not os.path.isdir(path):
                self.ui.print_error('Invalid path')
                self.exit()

            self.download_path = ABSOLUTE_PATH(path)
    
    def exit(self) -> None:
        self.ui.clear_line()
        self.ui.show_cursor()
        sys.exit(1)

    def _fmt_chapter_line(self, chapter: Chapter) -> str:
        line = []
        line.append(chapter.chapter.ljust(8))
        line.append(chapter.title)
        return '  '.join(line).rstrip()

    def _chapter_dirname(self, chapter: Chapter) -> str:
        if chapter.chapter:
            num_split = chapter.chapter.split('.')
            dirname = f'c{num_split[0].zfill(4)}'
            if len(num_split) > 1:
                dirname += f'{"." + ".".join(num_split[1:])}'
        else:
            dirname = chapter.title

        return SANITIZE_FILENAME(dirname)

    def download_as_archive(self, chapters: List[Chapter], ext: str, on_each: Optional[Callable[[int], None]] = lambda x: None) -> None:
        os.chdir(self.download_path)

        arcname = SANITIZE_FILENAME(chapters[0].manga.title) + ext
        failed_downloads = []

        if os.path.exists(arcname):
            name, _ = os.path.splitext(arcname)
            i = 1

            while os.path.exists(f"{name} ({i}){ext}"):
                i += 1
            
            arcname = f'{name} ({i}){ext}'

        for idx, chapter in enumerate(chapters):
            on_each(idx)

            images = self.interface.fetch_chapter_images(chapter)

            if not images:
                failed_downloads.append(chapter)
                continue

            with zipfile.ZipFile(arcname, 'a') as archive:
                for idx, (image, ext) in enumerate(images):
                    archive.writestr(os.path.join(self._chapter_dirname(chapter), IMAGE_FILENAME(idx, ext)), image)
        
        return failed_downloads

    def download_as_images(self, chapters: List[Chapter], ext: str, on_each: Optional[Callable[[int], None]] = lambda x: None) -> None:
        failed_downloads = []

        for idx, chapter in enumerate(chapters):
            on_each(idx)

            images = self.interface.fetch_chapter_images(chapter)

            if not images:
                failed_downloads.append(chapter)
                continue

            local_download_path = os.path.join(self.download_path, SANITIZE_FILENAME(chapter.manga.title), self._chapter_dirname(chapter))

            os.makedirs(local_download_path, exist_ok=True)
            os.chdir(local_download_path)

            for idx, (image, ext) in enumerate(images):
                with open(IMAGE_FILENAME(idx, ext), 'wb') as f:
                    f.write(image)
        
        return failed_downloads
    
    def run(self) -> None:
        search_term = self.ui.text(
            title='Search',
        ).execute()
        
        self.ui.print_status('Fetching results')

        mangas = []

        for manga in self.interface.search(search_term):
            mangas.append(Choice(manga, manga.title))
        
        self.ui.clear_line()

        if not mangas:
            self.ui.print_error('No results found')
            self.exit()

        selected_manga = self.ui.select(
            title='Manga',
            items=mangas,
            item_count_singular='result',
            item_count_plural='results',
        ).execute()

        self.ui.print_status('Fetching chapters')

        chapters = []

        for chapter in self.interface.get_chapters(selected_manga):
            line = self._fmt_chapter_line(chapter)
            if line:
                chapters.append(Choice(chapter, line))

        self.ui.clear_line()

        if not mangas:
            self.ui.print_error('No chapters found')
            self.exit()

        selected_chapters = self.ui.fuzzy(
            title='Chapters',
            items=chapters,
            item_count_singular='chapter',
            item_count_plural='chapters',
        ).execute()

        self.ui.hide_cursor()
        print()

        selected_format = self.ui.select(
            title='Format',
            items=[Choice(format, format['name']) for format in self.download_formats],
            item_count_singular='format',
            item_count_plural='formats',
        ).execute()

        print()

        chapter_count = self.ui.fmt_count(len(selected_chapters), "chapter", "chapters")
        on_chapter_download = lambda idx: self.ui.print_status(f'Downloading {idx+1} of {chapter_count}', new_line_before=False)
        failed_downloads = selected_format['method'](selected_chapters, selected_format['ext'], on_chapter_download)

        if failed_downloads:
            ui.print([('faded', 'Failed')])

            for chapter in failed_downloads:
                ui.print([('', self._fmt_chapter_line(chapter))])

            print()

        download_count = len(selected_chapters)-len(failed_downloads)

        self.ui.print_status(f'Downloaded {download_count} of {chapter_count}', new_line_before=False, ellipsis=False)

        print()


if __name__ == "__main__":
    try:
        Main().run()
    except KeyboardInterrupt:
        pass
    finally:
        ui = UI()
        ui.clear_line()
        ui.show_cursor()
