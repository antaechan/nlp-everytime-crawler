import os

import schedule
import time

from dotenv import load_dotenv

from bs4 import BeautifulSoup

from selenium import webdriver

from selenium.webdriver.common.by import By

from pymongo import MongoClient

import requests


load_dotenv()


login_url = "https://everytime.kr/login"

free_prefix = "https://everytime.kr/393753/p/"
politic_prefix = "https://everytime.kr/482694/p/"
secret_prefix = "https://everytime.kr/259098/p/"
newbie_prefix = "https://everytime.kr/412627/p/"


def crawling():
    browser = webdriver.Chrome(os.getenv("chromedriver_filepath"))
    login(browser)

    for collection_type, prefix in [
        ("free", free_prefix),
        ("politic", politic_prefix),
        ("secret", secret_prefix),
        ("newbie", newbie_prefix),
    ]:
        db_articles = connect_db(collection_type)
        update_db(browser, prefix, db_articles)


def login(browser):
    browser.get(login_url)

    # 로그인

    browser.find_element(By.NAME, "id").send_keys(os.getenv("everytime_id"))

    browser.find_element(By.NAME, "password").send_keys(os.getenv("everytime_password"))

    login_button = browser.find_element(By.XPATH, "/html/body/div/form/input")

    login_button.click()


def connect_db(collection_type):
    client = MongoClient(os.getenv("mongodb_uri"))

    db = client[os.getenv("db")]

    if not collection_type in db.list_collection_names():
        db_articles = db.create_collection(collection_type)

    db_articles = db[collection_type]

    return db_articles


def update_db(browser, prefix, db_articles):
    page_number = 10

    while page_number < 200:
        browser.get(prefix + str(page_number))
        time.sleep(1)

        taxi_page = browser.page_source

        soup = BeautifulSoup(taxi_page, "html5lib")

        wrap_articles = soup.find("div", attrs={"class": "wrap articles"})

        # 끝에 도달하는 거 의미
        # if wrap_articles.find("article", attrs={"class": "dialog"}) != None:
        #     break

        raw_articles = wrap_articles.find_all("article")

        for raw_article in raw_articles:
            user_id = raw_article.find("a", attrs={"class": "article"})["href"][-9:]

            date = raw_article.find("time").text

            context = raw_article.find("p", attrs={"class": "medium"}).text

            article = {
                "user_id": user_id,
                "date": date,
                "context": context,
            }

            if db_articles.find_one({"user_id": user_id}) == None:
                db_articles.insert_one(article)
                # post_message(context)

        page_number += 1


def post_message(context, channel="#taxi-crawler-bot"):
    token = os.getenv("slack_token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = f"text={context}&channel={channel}"

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage", headers=headers, data=data
        )

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    schedule.every(10).seconds.do(crawling)

    while True:
        schedule.run_pending()

        time.sleep(1)
