import requests
import re
import os

from bs4 import BeautifulSoup
from utils import Manga, Chapter, Interface
from urllib.parse import urljoin
from typing import (
    List
)

class Plugin(Interface):
    def __init__(self) -> None:
        self.url = 'https://h.mangabat.com'
        self.search_url = urljoin(self.url, '/search/manga/{}')

    def search(self, term: str) -> List[Manga]:
        term = re.sub(r'(?<=[a-zA-Z0-9])[^a-zA-Z0-9]+(?=[a-zA-Z0-9])', '_', term)
        term = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', term).lower()
        
        if term == '':
            return []

        request = requests.get(self.search_url.format(term))
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('div', class_='panel-list-story')

        mangas = []

        if root:
            manga_nodes = root.find_all_next('div', class_='list-story-item')

            for node in manga_nodes:
                url_node = node.find('a', class_='item-img')
                last_chapter_data = node.find_next('a', class_='item-chapter')
                last_chapter_data = last_chapter_data.get('title') if last_chapter_data else ''
                authors_data = node.find('span', class_='item-author')
                authors_data = authors_data.get('title') if authors_data else ''

                url = url_node.get('href')
                name = url_node.get('title')
                authors = re.split(r'\s*,\s*', authors_data)
                num_chapters = re.search(r'Chapter[ \t]+([\d.]+)', last_chapter_data)
                num_chapters = num_chapters.group(1) if num_chapters else None

                mangas.append(Manga(url, name, authors, num_chapters))

        return mangas

    def get_chapters(self, manga: Manga) -> List[Chapter]:
        request = requests.get(manga.url)
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('ul', class_='row-content-chapter')

        chapters = []
      
        if root:
            chapter_nodes = root.find_all_next('a', class_='chapter-name')

            for node in chapter_nodes:
                name_data = node.get('title')

                url = node.get('href')
                num = re.search(r'[Cc]hapter[ \t]+([\d.]+)', name_data)
                num = num.group(1) if num else None
                name = re.split(r'\s*:\s*', name_data, maxsplit=1)
                name = name[1] if len(name) > 1 else None

                chapters.append(Chapter(url, num, name))

        return chapters

    def download_chapter(self, chapter: Chapter, download_dir: str) -> None:
        if not chapter.url:
            raise RuntimeError

        request = requests.get(chapter.url)
        soup = BeautifulSoup(request.content, 'html.parser')
        root = soup.find('div', class_='container-chapter-reader')

        if root:
            os.chdir(download_dir)

            image_urls = [i.get('src') for i in root.find_all_next('img', class_='img-content')]
            headers = {'Referer': 'https://www.readmangabat.com'}
            
            for idx, url in enumerate(image_urls):
                image_data = requests.get(url, headers=headers).content
                with open(f'{str(idx+1).zfill(3)}.jpg', 'wb') as f:
                    f.write(image_data)
        else:
            raise RuntimeError