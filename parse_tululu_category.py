import os
import json
import argparse
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from pathvalidate import sanitize_filepath


MEDIA_URL = os.path.join("media",'')


def get_book_text(url, book_id):
    payload = {'id':book_id}

    response = requests.get(url, params=payload, allow_redirects=False)
    response.raise_for_status()

    if response.status_code == 302:
        return None

    return response.text


def get_book_info(url):
    response = requests.get(url)
    response.raise_for_status()

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


def save_text_file_to_folder(text_file, filename, folder_path):
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'w') as file:
        file.write(text_file)


def download_image(url, filename, folder_path):
    response = requests.get(url)
    response.raise_for_status()

    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'wb') as file:
        file.write(response.content)


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
        type=int,
        default=1,
        help='id of start page books in category'
    )
    parser.add_argument(
        '--end_page',
        type=int,
        default=701,
        help='id of end page books in category'
    )
    parser.add_argument(
        '--dest_folder',
        default=MEDIA_URL,
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
        default=MEDIA_URL,
        help='path to books description json file'
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
        if not args.skip_txt:
            book_text = get_book_text(book_download_url, book_id)

            if book_text == None:
                continue

        book_info_url = os.path.join(base_url, 'b{}/'.format(book_id))
        book_info = get_book_info(book_info_url)
        book_name = '{}. {}.txt'.format(book_id, book_info['title_text'])

        books_path = os.path.join(args.dest_folder, 'books', '')
        if not args.skip_txt:
            save_text_file_to_folder(book_text, book_name, books_path)

        if not args.skip_imgs:
            book_image_path = os.path.join(args.dest_folder, 'images', '')
            image_name = book_info['image_url'].split('/')[-1]
            download_image(book_info['image_url'], image_name, book_image_path)

        img_path = os.path.join(book_image_path, image_name)
        book_info['img_path'] = img_path

        book_path = os.path.join(books_path, book_name)
        book_info['book_path'] = book_path

        books_description.append(book_info)

        print(book_path)

    Path(args.json_path).mkdir(parents=True, exist_ok=True)
    books_description_path = os.path.join(args.json_path, 'books_description.json')
    with open(books_description_path, "w", encoding='utf8') as my_file:
        json.dump(books_description, my_file, ensure_ascii=False)


if __name__ == '__main__':
    main()
