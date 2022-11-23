from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from concurrent.futures import ProcessPoolExecutor
import re
from uvicorn import run
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Mobile App", version="0.1")


class Item(BaseModel):
    ids: List[int]


def parse_data(_id):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.headless = True
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "none"
    tmpDriver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver', options=options, desired_capabilities=caps)
    tmpDriver.implicitly_wait(5)
    tmpDriver.get("https://place.map.kakao.com/" + str(_id))
    tmpDriver.find_element(By.ID, 'kakaoContent')
    return _id, extract_one_info(tmpDriver.page_source)


def settings_t(ids):
    drivers = {}
    with ProcessPoolExecutor(max_workers=7) as executor:
        parsed_list = list(executor.map(parse_data, ids))
    for p in parsed_list:
        drivers[p[0]] = p[1]
    return drivers


def extract_one_info(src):
    result_t = {"menus": {}, "operation": []}
    bs_src = BeautifulSoup(src, 'lxml')
    info = bs_src.find('div', attrs={"data-viewid": "basicInfo", "class": "cont_essential"})
    result_t["phone"] = ' '.join(info.find("span", attrs={"class": "txt_contact"}).get_text().split())
    result_t["address"] = ' '.join(info.find("span", attrs={"class": "txt_address"}).get_text().split())
    operations = info.find("ul", attrs={"class": "list_operation"}).find_all("li")
    for operation in operations:
        result_t["operation"].append(' '.join(operation.find("span", attrs={"class": "txt_operation"}).get_text().split()))
    link_eval = info.find("a", attrs={"class": "link_evaluation"})
    link_eval.find("span", attrs={"class": "color_b"}).find("span", attrs={"class": "screen_out"}).decompose()
    result_t["rating"] = link_eval.find("span", attrs={"class": "color_b"}).get_text()
    link_eval.find("span", attrs={"class": "color_g"}).find("span", attrs={"class": "screen_out"}).decompose()
    result_t["number_of_ratings"] = re.sub("\D", "", link_eval.find("span", attrs={"class": "color_g"}).get_text())
    photo = bs_src.find('div', attrs={'class': 'photo_area'}).find('a', attrs={"class": "link_photo"})
    result_t["picture"] = photo.attrs["style"].replace("background-image:url('", "").replace("')", "")
    menus = bs_src.find('ul', attrs={"class": "list_menu"}).find_all('li')
    for menu in menus:
        try:
            menu.find('em', attrs={"class": "price_menu"}).find("span", attrs={"class": "screen_out"}).decompose()
            result_t["menus"][menu.find('span', attrs={"class": "loss_word"}).get_text()] \
                = re.sub("\D", "", menu.find('em', attrs={"class": "price_menu"}).get_text())
        except AttributeError:
            try:
                result_t["menus"][menu.find('span', attrs={"class": "loss_word"}).get_text()] = ""
            except AttributeError:
                result_t["menus"] = {}
    return result_t


@app.post("/parse/")
async def parse_items(datas: Item):
    return settings_t(datas.ids)


if __name__ == '__main__':
    host = "0.0.0.0"
    port = 8080
    workers = 1
    run("main:app", host=host, port=port, reload=True, workers=workers)
