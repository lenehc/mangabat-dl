import importlib
import os
import configparser
import argparse
import sys

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.prompts.fuzzy import FuzzyPrompt
from InquirerPy.base.list import BaseListPrompt

from prompt_toolkit import print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText

from utils import (
    Column,
    Chapter,
    CONFIG_DIR,
    CLASSES,
    STYLE,
    WIDTH,
    GUTTER,
    MARGIN,
    MANDATORY_MESSAGE,
    COLUMNS_MANGA,
    COLUMNS_CHAPTER,
)
from math import floor
from textwrap import shorten
from typing import (
    List,
    Tuple,
    Optional
)


class Fuzzy(FuzzyPrompt, BaseListPrompt):
    def _generate_after_input(self) -> List[Tuple[str, str]]:
        display_message = []

        if self._info:
            match_count = UI().fmt_count_match(self.content_control.choice_count)

            display_message.append(("", "   "))

            if not self.selected_choices:
                return display_message + [("class:fuzzy_info", f'({match_count})')]

            display_message.append(("class:fuzzy_info", f'({match_count}'))
            display_message.append(("class:fuzzy_info", f", {len(self.selected_choices)} selected)"))

        return display_message


class UI:
    def _fmt_selected_items(self, items: List[Chapter]) -> str:
        fmt_string = f'\n{MARGIN}' + f'\n{MARGIN}'.join(items[:10])

        if len(items) > 10:
            fmt_string += '\n' + MARGIN * 2 + f'... {len(items)-10} more selected'

        return fmt_string
    
    def _not_empty(self, value):
        if not value:
            return False
        return True

    def table(self, columns, type='select', **kwargs):
        headers_str = self.fmt_line([c.name for c in columns], columns)

        if type == 'select':
            return self.select(
                message=headers_str,
                **kwargs,
            )
        elif type == 'fuzzy':
            return self.fuzzy(
                message=headers_str,
                **kwargs,
            )

    def select(self, items, title, item_count_singular, item_count_plural, message=None):
        return inquirer.select(
            message=message if message else title,
            choices=items,
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
    
    def fuzzy(self, items, title, item_count_singular, item_count_plural, message=None):
        return Fuzzy(
            prompt=MARGIN + title,
            multiselect=True,
            marker='*',
            message=message,
            choices=items,
            transformer=self._fmt_selected_items,
            mandatory_message=MANDATORY_MESSAGE,
            long_instruction=MARGIN + self.fmt_count_str(len(items), item_count_singular, item_count_plural),
            style=STYLE,
            qmark=' ',
            amark=' ',
            pointer='',
            border=True,
            cycle=False,
        )

    def text(self, title):
        return inquirer.text(
            style=STYLE,
            message=MARGIN + title,
            qmark='',
            amark='',
            mandatory_message=MANDATORY_MESSAGE,
            validate=self._not_empty,
            invalid_message=MANDATORY_MESSAGE,
        )

    def fmt_line(self, items: Tuple[str], columns: List[Column]) -> str:
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
    
    def print_status(self, status: str, new_line_before: Optional[bool] = True, ellipsis: Optional[bool] = True) -> str:
        new_line = '\n' if new_line_before else ''

        self.clear_line()
        self.hide_cursor()
        print_formatted_text(
                FormattedText([('class:extra_faded', f'{new_line}{MARGIN}{status}{"..." if ellipsis else ""}')]),
                style=Style.from_dict(CLASSES),
                end='\r',
            )

    def print_usage(self) -> None:
        pass


class Main:
    def __init__(self) -> None:
        self.ui = UI()
    
    def _download_images(self, images):
        for idx, image in enumerate(images):
            with open(f'{str(idx+1).zfill(3)}.jpg', 'wb') as f:
                f.write(image)

    def run(self) -> None:
        config_dir = os.path.join(os.path.expanduser('~'), CONFIG_DIR, 'mangadl')

        os.makedirs(config_dir, exist_ok=True)

        config_path = os.path.join(config_dir, 'config')
        config = configparser.ConfigParser()

        if not os.path.exists(config_path):
            with open(config_path, 'w'):
                pass
        
        config.read(config_path)

        if 'Settings' not in config:
            config['Settings'] = {
                'download_dir': '',
                'plugin_dir': '',
            }

            with open(config_path, 'w') as config_file:
                config.write(config_file)
        
        download_dir = config['Settings'].get('download_dir', '.')
        plugin_dir = os.path.join(config['Settings'].get('plugin_dir', '.'), 'plugins')

        plugins = []

        for f in os.listdir('plugins'):
            if f.endswith('py'):
                plugins.append(os.path.splitext(f)[0])
            
        if not plugins:
            print(MARGIN + 'No plugins found')
            return

        selected_plugin = self.ui.select(
            title='Plugin',
            items=plugins,
            item_count_singular='plugin',
            item_count_plural='plugins',
        ).execute()

        self.ui.print_status('Loading plugin')

        plugin = importlib.import_module('plugins.' + selected_plugin).Plugin()

        self.ui.clear_line()

        search_term = self.ui.text(
            title='Search',
        ).execute()
        
        self.ui.print_status('Fetching results')

        mangas = []

        for manga in plugin.search(search_term):
            fmt_item = self.ui.fmt_line((manga.name_str, manga.authors_str, manga.num_chapters), COLUMNS_MANGA)
            mangas.append(Choice(manga, name=fmt_item))
        
        self.ui.clear_line()

        if not mangas:
            print(MARGIN + 'No results found')
            return

        selected_manga = self.ui.table(
            title='Manga',
            columns=COLUMNS_MANGA,
            items=mangas,
            item_count_singular='result',
            item_count_plural='results',
        ).execute()

        self.ui.print_status('Fetching chapters')

        if not selected_manga.num_chapters:
            print(MARGIN + 'No chapters')
            return

        chapters = []

        for chapter in plugin.get_chapters(selected_manga):
            fmt_item = self.ui.fmt_line((chapter.num, chapter.name_str), COLUMNS_CHAPTER)
            chapters.append(Choice(chapter, name=fmt_item))

        self.ui.clear_line()

        selected_chapters = self.ui.table(
            title='Search',
            columns=COLUMNS_CHAPTER,
            items=chapters,
            item_count_singular='chapter',
            item_count_plural='chapters',
            type='fuzzy',
        ).execute()

        self.ui.hide_cursor()
        print()

        failed_downloads = []

        for idx, chapter in enumerate(selected_chapters):
            self.ui.print_status(f'Downloading {idx+1} of {self.ui.fmt_count_chapter(len(selected_chapters))}', new_line_before=False)

            images = plugin.fetch_chapter_images(chapter)
            download_dir = os.path.join(download_dir, plugin.name, chapter.manga.name_str, chapter.num_str if chapter.num_str else chapter.name_str)

            os.makedirs(download_dir, exist_ok=True)
            os.chdir(download_dir)

            if not images:
                failed_downloads.append(chapter)
            
            self._download_images(images)
        
        self.ui.print_status(f'Downloaded {self.ui.fmt_count_chapter(len(selected_chapters))}', new_line_before=False, ellipsis=False)

        print()

        if failed_downloads:
            pass


commands = {
#    'p': ManagePlugins,
}

def main(ui: UI) -> None:
    args = sys.argv[1:]

    if not args:
        Main().run()
        return
    elif len(args) != 1:
        ui.print_usage()

    cmd_name = sys.argv[1]

    if cmd_name == 'h':
        ui.print_usage()

    cmd = commands.get(cmd_name)

    if not cmd:
        ui.print_usage()
    
    cmd.run()
    
    
if __name__ == "__main__":
    ui = UI()
    try:
        main(ui)
    except KeyboardInterrupt:
        pass
    finally:
        ui.clear_line()
        ui.show_cursor()
