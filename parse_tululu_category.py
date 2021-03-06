import os
import sys
import json
import argparse
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from pathvalidate import sanitize_filepath
from tqdm import tqdm


def configurate_argparse(get_pages_count, category_url):
    parser = argparse.ArgumentParser(
        description='This script parse books from categories pages on tululu.org website'
    )
    parser.add_argument(
        '--start_page',
        type=int,
        default=1,
        help='id of start page books in category'
    )
    parser.add_argument(
        '--end_page',
        type=int,
        default=get_pages_count(category_url),
        help='id of end page books in category'
    )
    parser.add_argument(
        '--dest_folder',
        default='media',
        help='path to result of parsing'
    )
    parser.add_argument(
        '--skip_imgs',
        action='store_true',
        help='option to allow skip download book\'s images'
    )
    parser.add_argument(
        '--skip_txt',
        action='store_true',
        help='option to allow skip download book\'s text'
    )
    parser.add_argument(
        '--json_path',
        default='media',
        help='path to books description json file'
    )

    return parser


def parse_category(category_url, start_id, end_id):
    books_urls = []
    for page_id in range(start_id, end_id + 1):
        category_page_url = urljoin(category_url, str(page_id))

        response = requests.get(category_page_url, allow_redirects=False)
        response.raise_for_status()

        if response.status_code in [301, 302]:
            raise Exception(F'Wrong category page: {response.url}. Please check your start_page and end_page command line args')

        soup = BeautifulSoup(response.text, 'lxml')

        books_a_tag_selector = '.bookimage a[href]'
        books_a_tags = soup.select(books_a_tag_selector)
        books_hrefs = [book_a_tag.get('href') for book_a_tag in books_a_tags]

        books_page_urls = [urljoin(category_page_url, book_href) for book_href in books_hrefs]

        books_urls.extend(books_page_urls)

    return books_urls


def get_books_ids(books_urls):
    books_ids = [book_url.split('/b')[-1][:-1] for book_url in books_urls]

    return books_ids


def get_book_text(url, book_id):
    payload = {'id':book_id}

    response = requests.get(url, params=payload, allow_redirects=False)
    response.raise_for_status()

    if response.status_code in [301, 302]:
        raise Exception('No text to download')

    return response.text


def get_book_info(url):
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()

    if response.status_code in [301, 302]:
        raise Exception('No book info')

    soup = BeautifulSoup(response.text, 'lxml')

    h1_tag = soup.select_one('h1')

    title_text, author = h1_tag.text.split('::')
    title_text = sanitize_filename(title_text.strip())
    author = sanitize_filename(author.strip())

    image_tag_selector = '.bookimage img[src]'
    image_tag = soup.select_one(image_tag_selector)
    image_src = image_tag.get('src')
    image_url = urljoin(url, image_src)

    comments_tags_selector = '.texts span'
    comments_tags = soup.select(comments_tags_selector)
    comments = [comment_tag.text for comment_tag in comments_tags]

    genres_tags_selector = 'span.d_book a'
    genres_tags = soup.select(genres_tags_selector)
    genres = [genre_tag.text for genre_tag in genres_tags]

    book_info = {
        'title_text': title_text,
        'author': author,
        'image_url': image_url,
        'comments': comments,
        'genres': genres
    }

    return book_info


def get_pages_count(url):
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()

    if response.status_code in [301, 302]:
        sys.exit('Can\'t get pages count. Please check your url')

    soup = BeautifulSoup(response.text, 'lxml')

    paginator_last_element_selector = 'a:last-child.npage'
    paginator_last_element = soup.select_one(paginator_last_element_selector)

    try:
        category_pages_count = paginator_last_element.text
    except AttributeError:
        category_pages_count = 1

    return category_pages_count


def save_text_file_to_folder(text_file, filename, folder_path):
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'w') as file:
        file.write(text_file)


def create_image_name(book_id, book_info):
    image_name = '{}. {}.{}'.format(
        book_id,
        book_info['title_text'],
        book_info['image_url'].split('/')[-1].split('.')[-1]
    )

    return image_name


def download_image(url, filename, folder_path):
    response = requests.get(url, allow_redirects=False)
    response.raise_for_status()

    if response.status_code in [301, 302]:
        raise Exception('No image for download')

    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'wb') as file:
        file.write(response.content)


def parse_book_page(book_id, base_url, book_download_url, args):
    if not args.skip_txt:
        book_text = get_book_text(book_download_url, book_id)

    book_info_url = urljoin(base_url, 'b{}/'.format(book_id))
    book_info = get_book_info(book_info_url)
    book_name = '{}. {}.txt'.format(book_id, book_info['title_text'])

    books_path = os.path.join(args.dest_folder, 'books')
    if not args.skip_txt:
        save_text_file_to_folder(book_text, book_name, books_path)

    if not args.skip_imgs:
        book_image_path = os.path.join(args.dest_folder, 'images')
        image_name = create_image_name(book_id, book_info)
        download_image(book_info['image_url'], image_name, book_image_path)

    img_path = os.path.join(book_image_path, image_name)
    book_info['img_path'] = img_path

    book_path = os.path.join(books_path, book_name)
    book_info['book_path'] = book_path

    return book_info


def save_books_description(books_description, args):
    Path(args.json_path).mkdir(parents=True, exist_ok=True)
    books_description_path = os.path.join(args.json_path, 'books_description.json')

    with open(books_description_path, "w", encoding='utf8') as my_file:
        json.dump(books_description, my_file, ensure_ascii=False)


def main():
    base_url = 'http://tululu.org'
    category_path_url = 'l55/'
    category_url = urljoin(base_url, category_path_url)
    book_download_url = urljoin(base_url, 'txt.php')

    parser = configurate_argparse(get_pages_count, category_url)
    args = parser.parse_args()

    books_urls = parse_category(category_url, args.start_page, args.end_page)
    books_ids = get_books_ids(books_urls)

    books_description = []
    for book_id in tqdm(books_ids):
        try:
            book_info = parse_book_page(book_id, base_url, book_download_url, args)
        except Exception as err:
            logging.error(err)
            continue

        books_description.append(book_info)

    save_books_description(books_description, args)


if __name__ == '__main__':
    main()
