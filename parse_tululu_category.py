import os
import json
import argparse
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from parse_tululu_page import get_book_text, get_book_info
from parse_tululu_page import MEDIA_URL, save_text_file_to_folder, download_image


def parse_category(category_url, start_id, end_id):
    books_urls = []
    for page_id in range(start_id, end_id + 1):
        category_page_url = os.path.join(category_url, '{}'.format(page_id))

        response = requests.get(category_page_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        books_a_tag_selector = '.bookimage a[href]'
        books_a_tags = soup.select(books_a_tag_selector)
        books_hrefs = [book_a_tag.get('href') for book_a_tag in books_a_tags]

        books_page_urls = [urljoin('http://tululu.org', book_href) for book_href in books_hrefs]

        for book_page_url in books_page_urls:
            books_urls.append(book_page_url)

    return books_urls


def main():
    parser = argparse.ArgumentParser(
        description='This script parse books from categories pages on tululu.org website'
    )
    parser.add_argument(
        '--start_page',
        default=1,
        help='Input id of start page books in category'
    )
    parser.add_argument(
        '--end_page',
        default=701,
        help='Input id of end page books in category'
    )
    args = parser.parse_args()

    base_url = 'http://tululu.org'
    category_path_url = 'l55'
    category_url = os.path.join(base_url, category_path_url)

    start_id = int(args.start_page)
    end_id = int(args.end_page)
    books_urls = parse_category(category_url, start_id, end_id)

    book_download_url = os.path.join(base_url, 'txt.php')

    books_description = []

    book_ids = [books_url.split('/b')[-1][:-1] for books_url in books_urls]
    for book_id in book_ids:
        book_text = get_book_text(book_download_url, book_id)

        if book_text == None:
            continue

        book_info_url = os.path.join(base_url, 'b{}/'.format(book_id))
        book_info = get_book_info(book_info_url)
        book_name = '{}. {}.txt'.format(book_id, book_info['title_text'])

        books_path = os.path.join(MEDIA_URL, 'books', '')
        save_text_file_to_folder(book_text, book_name, books_path)

        book_image_path = os.path.join(MEDIA_URL, 'images', '')
        image_name = book_info['image_url'].split('/')[-1]
        download_image(book_info['image_url'], image_name, book_image_path)

        book_path = os.path.join(books_path, book_name)
        book_info['book_path'] = book_path
        books_description.append(book_info)

        print(book_path)

    books_description_path = os.path.join(MEDIA_URL, 'books_description.json')
    with open(books_description_path, "w", encoding='utf8') as my_file:
        json.dump(books_description, my_file, ensure_ascii=False)


if __name__ == '__main__':
    main()
