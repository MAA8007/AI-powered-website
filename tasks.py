from concurrent.futures import ThreadPoolExecutor, as_completed
from .models import Article
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import pandas as pd
from dateutil.parser import parse
import requests
from bs4 import BeautifulSoup
from django.utils.dateparse import parse_datetime
from django.db import IntegrityError
import random
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import csv 



rss_feed_details = [
    ('http://www.thisisanfield.com/feed/', 'item', 'link', 'title', 'enclosure', 'url', 'Liverpool FC','This is Anfield', 'pubDate'),
    ('http://www.theguardian.com/football/rss', 'item', 'link', 'title', 'media:content', 'url', 'Football', 'The Guardian', 'pubDate'),
    ('https://theathletic.com/team/liverpool/?rss=1', 'item', 'link', 'title', 'media:content', 'href', 'Liverpool FC','The Athletic','pubDate'),
    ('https://theathletic.com/premier-league/?rss', 'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic', 'published'),
    ('https://theathletic.com/soccer/?rss',  'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic','published'),
    ('https://theathletic.com/champions-league/?rss',  'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic', 'published'),
    ('https://www.autosport.com/rss/feed/f1', 'item', 'link', 'title', 'enclosure', 'url', 'Formula 1', 'Autosport', 'pubDate'),
    ('https://the-race.com/category/formula-1/feed/', 'item', 'link', 'title','media:content', 'url', 'Formula 1', 'The Race', 'pubDate'),
    ('https://aeon.co/feed.rss', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "Aeon", 'pubDate'),
    ('https://psyche.co/feed', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "Psyche", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Opinion.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Magazine.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Science.xml', 'item', 'link', 'title', 'media:content', 'url', 'Science & Technology', "New York Times", 'pubDate'),
    ('http://www.smithsonianmag.com/rss/innovation/', 'item', 'link', 'title', 'enclosure', 'url', 'Science & Technology', "Smithsonian", 'pubDate'),
    ('http://www.smithsonianmag.com/rss/latest_articles/', 'item', 'link', 'title', 'enclosure', 'url', 'Science & Technology', "Smithsonian", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Travel.xml', 'item', 'link', 'title', 'media:content', 'url', 'Travel', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Style.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Technology.xml', 'item', 'link', 'title', 'media:content', 'url', 'Science & Technology', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Business.xml', 'item', 'link', 'title', 'media:content', 'url', 'Global News', "New York Times", 'pubDate'),
     ('http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'item', 'link', 'title', 'media:content', 'url', 'Global News', "New York Times", 'pubDate'),
    ('https://www.nytimes.com/wirecutter/rss/', 'item', 'link', 'title', 'description', 'src', 'Science & Technology', "New York Times Wirecutter", 'pubDate'),
     ('http://feeds.feedburner.com/dawn-news', 'item', 'link', 'title',  'media:content', 'url', 'Pakistan', "Dawn", 'pubDate'),
     ('https://feeds.feedburner.com/dawn-news-world', 'item', 'link', 'title',  'media:content', 'url', 'Global News', "Dawn", 'pubDate'),
    ('https://www.theverge.com/rss/reviews/index.xml', 'entry', 'id', 'title', 'media:content', 'url', 'Science & Technology', 'The Verge', 'published'),
]


def delete_images_for_specific_websites():
    target_websites = ["Psyche", "Aeon", "The Athletic", "New York Times", "Smithsonian"]
    articles = Article.objects.filter(website__in=target_websites)
    
    for article in articles:
        article.image = None
        article.save()
        print(f"Deleted image for article: {article.title} from {article.website}")

def reparse_rss_and_update_images():
    for url, main_tag, link_tag, title_tag, image_tag, image_attr, category, website, date_tag in rss_feed_details:
        print("WE REPARSING FR FR")
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml-xml')
            entries = []

            for entry in soup.find_all(main_tag):
                try:
                    title = entry.find(title_tag).text
                    link = entry.find(link_tag).text
                    date = entry.find(date_tag).text
                    published = normalize_datetime_to_django_format(date)

                    if image_tag:
                        if "Psyche" in website or "Aeon" in website:
                            description_content = entry.find('description').text
                            description_soup = BeautifulSoup(description_content, 'html.parser')
                            image_tag_obj = description_soup.find('img')
                            image = image_tag_obj.get('src') if image_tag_obj else None

                        elif "The Athletic" in website:
                            media_content = entry.find('media:content')
                            image = media_content.get('url') if media_content else None
                            if not image:
                                image = (
                                    'https://images.unsplash.com/photo-1518188049456-7a3a9e263ab2?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1674&q=80'
                                    if "liverpool" in url else
                                    'https://images.unsplash.com/photo-1486286701208-1d58e9338013?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1770&q=80'
                                )

                        elif "The Guardian" in website:
                            media_content_tags = entry.find_all('media:content')
                            max_width = 0
                            selected_image = None

                            for media_content in media_content_tags:
                                if 'url' in media_content.attrs and 'width' in media_content.attrs:
                                    width = int(media_content['width'])
                                    url = media_content['url']
                                    if width > max_width:
                                        max_width = width
                                        selected_image = url

                            image = selected_image or 'https://images.unsplash.com/photo-1555862124-94036092ab14?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1771&q=80'

                        elif "New York Times Wirecutter" in website:
                            description_content = entry.find('description').text
                            description_soup = BeautifulSoup(description_content, 'html.parser')
                            image_tag_obj = description_soup.find('img')
                            if image_tag_obj:
                                image = image_tag_obj['src']
                            else:
                                images = [
                                    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1772&q=80",
                                    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60",
                                    "https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60",
                                    "https://images.unsplash.com/photo-1550745165-9bc0b252726f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OHx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60",
                                    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60",
                                    "https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTF8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60",
                                    "https://images.unsplash.com/photo-1496065187959-7f07b8353c55?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTR8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60"
                                ]
                                image = random.choice(images)

                        elif "New York Times" in website:
                            media_content = entry.find('media:content')
                            image = media_content.get('url') if media_content else None
                            if not image:
                                images = {
                                    'Opinion': ["https://images.unsplash.com/photo-1506543277633-99deabfcd722?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=750&q=80"],
                                    'Magazine': ["https://images.unsplash.com/photo-1548706108-582111196a20?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1782&q=80"],
                                    'Business': [
                                        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2940&q=80",
                                        "https://images.unsplash.com/photo-1572883454114-1cf0031ede2a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YnVpbGRpbmdzfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60"
                                    ],
                                    'Home': ["https://images.unsplash.com/photo-1521295121783-8a321d551ad2?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1770&q=80"],
                                    'Travel': [
                                        "https://images.unsplash.com/photo-1488085061387-422e29b40080?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2231&q=80",
                                        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Nnx8dHJhdmVsfGVufDB8MHwwfHx8MA%3D%3D&auto=format&fit=crop&w=800&q=60"
                                    ]
                                }
                                image = random.choice(images.get(category, [])) if category in images else None

                        elif "Autosport" in website:
                            enclosure_tag = entry.find('enclosure')
                            image = enclosure_tag.get('url') if enclosure_tag else 'https://images.unsplash.com/photo-1656337449909-141091f4df4a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80'

                        elif website == 'The Race':
                            media_content = entry.find('media:content')
                            image = media_content.get('url') if media_content else 'https://images.unsplash.com/photo-1656337449909-141091f4df4a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80'

                        elif website == 'This is Anfield':
                            media_thumbnail = entry.find('media:thumbnail')
                            image = media_thumbnail.get('url') if media_thumbnail else 'https://images.unsplash.com/photo-1555862124-94036092ab14?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1771&q=80'

                        elif website == 'The Verge':
                            content = entry.find('content')
                            content_soup = BeautifulSoup(content.text, 'html.parser')
                            img_tag = content_soup.find('img')
                            image = img_tag.get('src') if img_tag else None

                        elif 'smithsonian' in url:
                            enclosure = entry.find('enclosure')
                            image = enclosure.get('url') if enclosure else random.choice([
                                "https://images.unsplash.com/photo-1451187580459-43490279c0fa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1772&q=80",
                                "https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60"
                            ])

                        elif "dawn" in link:
                            media_content = entry.find('media:content')
                            image = media_content.get('url') if media_content else 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'

                        else:
                            image = entry.find(image_tag, {image_attr: True})
                            if not image:
                                image = 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'

                    else:
                        image = 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'

                    # Update or create article with the new image
                    article, created = Article.objects.update_or_create(
                        link=link,
                        defaults={
                            'title': title,
                            'category': category,
                            'website': website,
                            'published': published,
                            'image': image
                        }
                    )

                except Exception as e:
                    print(f"Error processing an entry from {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching feed from {url}: {e}")
            
### Function to fetch RSS feed and update the database with progress updates
def update_url_database_function_with_yield():
    rss_feed_details = [
    ('http://www.thisisanfield.com/feed/', 'item', 'link', 'title', 'enclosure', 'url', 'Liverpool FC','This is Anfield', 'pubDate'),
    ('http://www.theguardian.com/football/rss', 'item', 'link', 'title', 'media:content', 'url', 'Football', 'The Guardian', 'pubDate'),
    ('https://theathletic.com/team/liverpool/?rss=1', 'item', 'link', 'title', 'media:content', 'href', 'Liverpool FC','The Athletic','pubDate'),
    ('https://theathletic.com/premier-league/?rss', 'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic', 'published'),
    ('https://theathletic.com/soccer/?rss',  'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic','published'),
    ('https://theathletic.com/champions-league/?rss',  'item', 'link', 'title', 'media:content', 'href', 'Football','The Athletic', 'published'),
    ('https://www.autosport.com/rss/feed/f1', 'item', 'link', 'title', 'enclosure', 'url', 'Formula 1', 'Autosport', 'pubDate'),
    ('https://the-race.com/category/formula-1/feed/', 'item', 'link', 'title','media:content', 'url', 'Formula 1', 'The Race', 'pubDate'),
    ('https://aeon.co/feed.rss', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "Aeon", 'pubDate'),
    ('https://psyche.co/feed', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "Psyche", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Opinion.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Magazine.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Science.xml', 'item', 'link', 'title', 'media:content', 'url', 'Science & Technology', "New York Times", 'pubDate'),
    ('http://www.smithsonianmag.com/rss/innovation/', 'item', 'link', 'title', 'enclosure', 'url', 'Science & Technology', "Smithsonian", 'pubDate'),
    ('http://www.smithsonianmag.com/rss/latest_articles/', 'item', 'link', 'title', 'enclosure', 'url', 'Science & Technology', "Smithsonian", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Travel.xml', 'item', 'link', 'title', 'media:content', 'url', 'Travel', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Style.xml', 'item', 'link', 'title', 'media:content', 'url', 'Self Dev', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Technology.xml', 'item', 'link', 'title', 'media:content', 'url', 'Science & Technology', "New York Times", 'pubDate'),
    ('http://www.nytimes.com/services/xml/rss/nyt/Business.xml', 'item', 'link', 'title', 'media:content', 'url', 'Global News', "New York Times", 'pubDate'),
     ('http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'item', 'link', 'title', 'media:content', 'url', 'Global News', "New York Times", 'pubDate'),
    ('https://www.nytimes.com/wirecutter/rss/', 'item', 'link', 'title', 'description', 'src', 'Science & Technology', "New York Times Wirecutter", 'pubDate'),
     ('http://feeds.feedburner.com/dawn-news', 'item', 'link', 'title',  'media:content', 'url', 'Pakistan', "Dawn", 'pubDate'),
     ('https://feeds.feedburner.com/dawn-news-world', 'item', 'link', 'title',  'media:content', 'url', 'Global News', "Dawn", 'pubDate'),
    ('https://www.theverge.com/rss/reviews/index.xml', 'entry', 'id', 'title', 'media:content', 'url', 'Science & Technology', 'The Verge', 'published'),
]



    yield "Starting the update process..."

    items = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_feed, *item) for item in rss_feed_details]
        for future in futures:
            try:
                items.extend(future.result())
            except Exception as e:
                print(f"Error fetching feed: {e}")
    
    yield "Checking and storing items in the database..."
    yield from check_and_store_items_with_yield(items)

    yield "Update process completed successfully."

    documents = get_documents_from_db()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2024, chunk_overlap=204)
    all_splits = text_splitter.split_documents(documents)
    
    vectorstore = FAISS.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(model="text-embedding-3-small"))
    filepath = os.path.join(os.path.dirname(__file__), 'vectorstore')
    vectorstore.save_local(filepath)

#('https://theathletic.com/team/liverpool/?rss=1', 'item', 'link', 'title', 'media:content', '', 'Liverpool FC','The Athletic','pubDate'),
def fetch_feed(url, main_tag, link_tag, title_tag, image_tag, image_attr, category, website, date_tag):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml-xml')
    entries = [] 

    for entry in soup.find_all(main_tag):
        try:
            title = entry.find(title_tag).text
            link = entry.find(link_tag).text
            date = entry.find(date_tag).text
            published = normalize_datetime_to_django_format(date)
            if image_tag:
                if "Psyche" in website or "Aeon" in website:
                    description_content = entry.find('description').text
                    description_soup = BeautifulSoup(description_content, 'html.parser')
                    image_tag_obj = description_soup.find('img')
                    image_url = image_tag_obj.get('src')
                
                elif "The Athletic" in website:
                    media_content = entry.find('media:content')
                    if media_content:
                        image = media_content.get('url')
                    else:
                        if "liverpool" in url:
                            image = 'https://images.unsplash.com/photo-1518188049456-7a3a9e263ab2?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1674&q=80'
                        else:
                            image = 'https://images.unsplash.com/photo-1486286701208-1d58e9338013?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1770&q=80'
                        
                elif "The Guardian" in website:
                    media_content_tags = entry.find_all('media:content')

                    # Initialize variables to store the URL with the highest width
                    max_width = 0
                    selected_image = None

                    # Iterate through the media content tags to find the one with the highest width
                    for media_content in media_content_tags:
                        if 'url' in media_content.attrs and 'width' in media_content.attrs:
                            width = int(media_content['width'])
                            url = media_content['url']
                            if width > max_width:
                                max_width = width
                                selected_image = url

                    # Use the selected image URL
                    if selected_image:
                        image = selected_image
                    else:
                        image = 'https://images.unsplash.com/photo-1555862124-94036092ab14?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1771&q=80'

                elif website == "New York Times Wirecutter":
                    description_content = entry.find('description').text
                    description_soup = BeautifulSoup(description_content, 'html.parser')
                    image_tag_obj = description_soup.find('img')
                    if image_tag_obj:
                        image = image_tag_obj['src']
                    else:
                        images = ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1772&q=80","https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550745165-9bc0b252726f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OHx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550751827-4bd374c3f58b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTF8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1496065187959-7f07b8353c55?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTR8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60"]
                        image = random.choice(images)


                elif "New York Times" in website:
                    image_url = entry.find('media:content').get('url')
                    if not image_url:
                        if 'Opinion' in url or 'Magazine' in url:
                            images = ["https://images.unsplash.com/photo-1506543277633-99deabfcd722?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=750&q=80","https://images.unsplash.com/photo-1548706108-582111196a20?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1782&q=80"]
                            image = random.choice(images)
                        
                        elif 'Business' in url:
                            images = ["https://images.unsplash.com/photo-1504711434969-e33886168f5c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2940&q=80",
                                    "https://images.unsplash.com/photo-1572883454114-1cf0031ede2a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YnVpbGRpbmdzfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60",
                                    "https://images.unsplash.com/photo-1543286386-2e659306cd6c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8ZmluYW5jaWFsfGVufDB8fDB8fHww&auto=format&fit=crop&w=800&q=60",
                                    "https://images.unsplash.com/photo-1634542984003-e0fb8e200e91?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTh8fGZpbmFuY2lhbHxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=800&q=60"]
                            image = random.choice(images)
                            
                        elif "Home" in url:
                            images = ["https://images.unsplash.com/photo-1521295121783-8a321d551ad2?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1770&q=80","https://images.unsplash.com/photo-1573812195421-50a396d17893?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MjR8fG5ld3N8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=800&q=60"]
                            image = random.choice(images)

                        elif "Travel" in url:
                            images = ["https://images.unsplash.com/photo-1488085061387-422e29b40080?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2231&q=80","https://images.unsplash.com/photo-1501785888041-af3ef285b470?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Nnx8dHJhdmVsfGVufDB8MHwwfHx8MA%3D%3D&auto=format&fit=crop&w=800&q=60","https://images.unsplash.com/photo-1530521954074-e64f6810b32d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1530789253388-582c481c54b0?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTJ8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1452421822248-d4c2b47f0c81?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTR8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1436491865332-7a61a109cc05?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTh8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1504609773096-104ff2c73ba4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MjZ8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1494783367193-149034c05e8f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MzJ8fHRyYXZlbHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60"]
                            image = random.choice(images)
                            
                        elif "Technology" in url:
                            images = ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1772&q=80","https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550745165-9bc0b252726f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OHx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550751827-4bd374c3f58b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTF8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1496065187959-7f07b8353c55?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTR8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60"]
                            image = random.choice(images)

                        elif "Style" in url:
                            image = 'https://images.unsplash.com/photo-1501127122-f385ca6ddd9d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=870&q=80'

                        else:
                            image ='https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'


                elif website == "Autosport":
                    enclosure_tag = entry.find('enclosure')
                    if enclosure_tag and 'url' in enclosure_tag.attrs:
                        image = enclosure_tag['url']
                    else:
                        image = 'https://images.unsplash.com/photo-1656337449909-141091f4df4a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80'

                elif website == 'The Race':
                    media_content = entry.find('media:content')
                    if media_content and 'url' in media_content.attrs:
                        image = media_content['url']
                    else:
                        image = 'https://images.unsplash.com/photo-1656337449909-141091f4df4a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=774&q=80'

                elif website == 'This is Anfield':
                    media_thumbnail = entry.find('media:thumbnail')
                    if media_thumbnail and 'url' in media_thumbnail.attrs:
                        image = media_thumbnail['url']
                    else:
                        image = 'https://images.unsplash.com/photo-1555862124-94036092ab14?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1771&q=80'

                elif website == 'The Verge':
                    content = soup.find('content')
                    content_soup = BeautifulSoup(content.text, 'html.parser')
                    img_tag = content_soup.find('img')
                    image_url = img_tag.get('src')
                
                elif 'smithsonian' in url:
                        enclosure = entry.find('enclosure')
                        image_url = enclosure.get('url') if enclosure else None
                        images = ["https://images.unsplash.com/photo-1451187580459-43490279c0fa?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1772&q=80","https://images.unsplash.com/photo-1531297484001-80022131f5a1?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NXx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550745165-9bc0b252726f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OHx8dGVjaHxlbnwwfDB8MHx8fDA%3D&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1550751827-4bd374c3f58b?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTB8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1518770660439-4636190af475?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTF8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60","https://images.unsplash.com/photo-1496065187959-7f07b8353c55?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTR8fHRlY2h8ZW58MHwwfDB8fHww&auto=format&fit=crop&w=1400&q=60"]
                        image = random.choice(images)

                elif "dawn" in link:
                    media_content = entry.find('media:content')
                    if media_content and 'url' in media_content.attrs:
                        image = media_content['url']
                    else:
                        image = 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'
            
                else:
                    image = entry.find(image_tag, {image_attr: True})
                    if not image:
                        image = 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'
            
            else:
                image = 'https://images.unsplash.com/photo-1588414884049-eb55cd4c72b4?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=776&q=80'
            
            entries.append([title, link, category, website, published, image])

        except Exception as e:
            print(f"Error processing an entry from {url}: {e}")
            continue

    return entries

def normalize_datetime_to_django_format(dt_str):
    dt = parse(dt_str)
    return dt.strftime('%Y-%m-%d %H:%M:%S%z')

def fetch_nyt(url):
    response = requests.get("https://r.jina.ai/"+url)
    return response.text

### Check and store new items in the database with progress updates

def process_item(item):
    title, link, category, website, published, image = item
    
    if not Article.objects.filter(link=link).exists():
        yield f"Fetching full text for: {title}"
        
        if "nytimes" in link or "www.nytimes.com/athletic" in link:
            full_text = fetch_nyt(link)
        else:
            full_text = fetch_full_article(link)
        
        yield f"Summarizing article: {title}"
        sum = summarize_text(full_text) if full_text else "No summary available"
        summary = "This is an article by "+ website + ". " + sum

        Article.objects.create(
            title=title,
            link=link,
            summary=summary,
            category=category,
            website=website,
            published=published,
            image=image,
        )
        yield f"Stored article: {title}"

    else:
        yield f"Article with link {link} already exists. Skipping..."

def check_and_store_items_with_yield(items):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_item, item) for item in items]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                for result in future.result():
                    yield result
            except Exception as e:
                yield f"An error occurred: {e}"

### Function to summarize text using OpenAI
def summarize_text(text):
    """ llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    ) """

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        )
    messages = [
        (
            "system",
            "You are a text processing model. Your task is to extract and return the main body of text from the provided content. Focus on the core text of the article, preserving its paragraph structure. Ignore any extraneous elements such as advertisements, navigation links, or non-article content. Do not exceed the length of 10 sentences.",
        ),
        ("human", text),
    ]
    summarized_text = llm.invoke(messages)
    return summarized_text.content

### Function to fetch full article content
def fetch_full_article(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        article_text = ' '.join(p.text for p in soup.find_all('p'))
        return article_text
    return None


### Function to get documents from the database for RAG
def get_documents_from_db():
    articles = Article.objects.all()
    documents = []
    for article in articles:
        metadata = {
            'source': article.link,
            'title': article.title,
            'description': article.summary,
            'category': article.category,
            'website': article.website,
            'published': article.published.strftime('%Y-%m-%d %H:%M:%S%z'),
            'language': 'en-US'  # Assuming the language is English
        }
        doc = Document(page_content=article.summary, metadata=metadata)
        documents.append(doc)
    return documents

### Function to generate a response using RAG
def get_rag_response(query):
    filepath = os.path.join(os.path.dirname(__file__), 'vectorstore')
    vectorstore = FAISS.load_local(filepath, OpenAIEmbeddings(model="text-embedding-3-small"), allow_dangerous_deserialization=True)

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
    
    llm = ChatOpenAI(model="gpt-4o-mini")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    

    template = """Use the following pieces of context to answer the question at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Use 10 sentences maximum and keep the answer as concise as possible.

    {context}

    Question: {question}

    Helpful Answer:"""
    custom_rag_prompt = PromptTemplate.from_template(template)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )

    answer = rag_chain.invoke(query)
    return answer

