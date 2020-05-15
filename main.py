import os
import requests
from pathlib import Path


MEDIA_URL = os.path.join("media",'')


def get_book_text(book_id):
    url = 'http://tululu.org/txt.php'
    payload = {'id':book_id}

    response = requests.get(url, params=payload, allow_redirects=False)
    response.raise_for_status()

    if response.status_code == 302:
        return None

    return response.text


def save_text_file_to_folder(text_file, filename, folder_path):
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    file_path = folder_path + filename
    with open(file_path, 'w') as file:
        file.write(text_file)


def main():
    book_ids = range(1,11)
    for book_id in book_ids:
        book_text = get_book_text(book_id)

        if book_text == None:
            continue

        book_name = 'book_{}.txt'.format(book_id)
        books_path = os.path.join(MEDIA_URL, 'books','')

        save_text_file_to_folder(book_text, book_name, books_path)


if __name__ == '__main__':
    main()
