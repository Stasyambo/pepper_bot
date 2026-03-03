import requests
from bs4 import BeautifulSoup
import hashlib


def create_deal_id(deal):
    """Создает уникальный ID для сделки на основе заголовка и ссылки"""
    unique_string = f"{deal['title']}_{deal['link']}"
    return hashlib.md5(unique_string.encode()).hexdigest()


def parse_pepper():
    """
    Рабочий парсер Pepper.ru
    """
    url = "https://www.pepper.ru/new"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        deals = []

        # Ищем статьи с deals
        articles = soup.find_all('article', class_='deal-card')

        for article in articles:
            try:
                # Извлекаем данные из структуры
                title_elem = article.find('a', class_=lambda x: x and 'visited' in str(x))
                title = title_elem.get_text(strip=True) if title_elem else "Без названия"

                # Ссылка из заголовка
                link = title_elem.get('href', '') if title_elem else ''
                if link and link.startswith('/'):
                    link = 'https://www.pepper.ru' + link

                # Цена
                price_elem = article.find('div',
                                          class_=lambda x: x and 'text-primary' in str(x) and 'font-bold' in str(x))
                price = price_elem.get_text(strip=True) if price_elem else "Цена не указана"

                # Температура (лайки)
                temp_elem = article.find('span', class_=lambda x: x and 'hotness_value' in str(x))
                temperature = temp_elem.get_text(strip=True) if temp_elem else "0"

                # Магазин
                store_elem = article.find('a', class_='gtm_store_visit_homepage')
                store = store_elem.get_text(strip=True) if store_elem else "Неизвестный магазин"

                if title and link:
                    deal_data = {
                        'title': title,
                        'link': link,
                        'temperature': temperature,
                        'price': price,
                        'store': store
                    }
                    # Добавляем уникальный ID
                    deal_data['id'] = create_deal_id(deal_data)
                    deals.append(deal_data)

            except Exception as e:
                print(f"Ошибка в обработке статьи: {e}")
                continue

        return deals

    except Exception as e:
        print(f"Ошибка парсера: {e}")
        return []
