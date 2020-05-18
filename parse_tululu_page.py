import os
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


def main():
    base_url = 'http://tululu.org'
    book_download_url = os.path.join(base_url, 'txt.php')

    book_ids = range(1,11)
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


if __name__ == '__main__':
    main()
