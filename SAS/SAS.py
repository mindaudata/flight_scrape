import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import re
import pickle

options = Options()
# options.add_argument('-headless')
driver = webdriver.Firefox(options=options)

# profile = webdriver.FirefoxProfile()
# profile.set_preference("permissions.default.image", 2)
# profile.set_preference('permissions.default.stylesheet', 2)
# driver = webdriver.Firefox(firefox_profile=profile)

wait = WebDriverWait(driver, timeout=180)
url = 'https://classic.flysas.com/en/de/'
driver.get(url)

# dump cookies
# pickle.dump(driver.get_cookies() , open("SAS.pkl","wb"))

# load cookies
# for cookie in pickle.load(open("SAS.pkl", "rb")):
#     driver.add_cookie(cookie)

arnId = 'ctl00_FullRegion_MainRegion_ContentRegion_ContentFullRegion_ContentLeftRegion_CEPGroup1_CEPActive_cepNDPRevBookingArea_predictiveSearch_txtFrom'
arnClickId = 'resultFrom'
lhrId = 'ctl00_FullRegion_MainRegion_ContentRegion_ContentFullRegion_ContentLeftRegion_CEPGroup1_CEPActive_cepNDPRevBookingArea_predictiveSearch_txtTo'
lhrClickId = 'resultTo'

wait.until(EC.visibility_of_element_located((By.ID, arnId))).send_keys("ARN")
wait.until(EC.visibility_of_element_located((By.ID, arnClickId))).click()
wait.until(EC.visibility_of_element_located((By.ID, lhrId))).send_keys("LHR")
wait.until(EC.visibility_of_element_located((By.ID, lhrClickId))).click()

# Calendar selection not implemented
# Search button click commented out
# wait.until(EC.visibility_of_element_located((By.ID, 'ctl00_FullRegion_MainRegion_ContentRegion_ContentFullRegion_ContentLeftRegion_CEPGroup1_CEPActive_cepNDPRevBookingArea_Searchbtn'))).click()

###
# Captcha
###


page = BeautifulSoup(driver.page_source, 'lxml')


def read_table(table):
    flights = []

    row1 = table.find_all("tr", {'class': 'segmented'})
    row2 = table.find_all('tr', {'class': 'segments'})

    for i in range(0, len(row1)):
        if (len(row2[i].find_all('td', {'class': 'route last'})) < 3 or
            len(row2[i].find_all('td', {'class': 'route last'})) > 3 and
                row2[i].find_all('td', {'class': 'route last'})[2].text.strip()[0:4] == 'Oslo'):

            flight = {
                'priceId': '',
                'price': 0.0,
                'depart': '',
                'stop': '',
                'arrive': '',
                'time': ''}

            for item in row1[i].find_all('span', id=re.compile("^price_\d_")):
                if flight['priceId'] == '' or flight['price'] > float(item.get('data-price')):
                    flight['priceId'] = item.get('id')
                    flight['price'] = float(item.get('data-price'))

            for item in row1[i].find_all('td', {'class': 'time'}):
                flight['time'] = item.text.replace(" ", "")

            flight['depart'] = row1[i].find_all(
                'acronym', {'class': 'airport'})[0].text.strip()
            flight['arrive'] = row1[i].find_all(
                'acronym', {'class': 'airport'})[1].text.strip()
            try:
                flight['stop'] = row2[i].find_all('td', {'class': 'route last'})[
                    2].text.strip()[0:4]
            except:
                pass

            flights.append(flight)

    return flights


def get_tax():
    tax = wait.until(EC.visibility_of_element_located((By.ID, 'taxesAndFees')))
    return(tax.get_attribute('innerHTML').replace(',', '.'))


def get_total():
    totalprice = wait.until(
        EC.visibility_of_element_located((By.ID, 'totalPriceCash')))
    return(totalprice.get_attribute('innerHTML').replace(',', '.'))


def click_by_id(click_id):
    wait.until(EC.visibility_of_element_located((By.ID, click_id))).click()


table1 = page.find('table', {'id': 'WDSEffect_table_0'})
table2 = page.find('table', {'id': 'WDSEffect_table_1'})

outboundFlights = read_table(table1)
returningFlights = read_table(table2)

data = []
for outbound in outboundFlights:
    click_by_id(outbound['priceId'])
    for returning in returningFlights:
        click_by_id(returning['priceId'])
        data.append({'totalPrice': get_total(),
                     'totalTax': get_tax(),
                     '20190408': outbound,
                     '20190414': returning})

with open('ARLLHR20190408-LHRARL20190414.json', 'w') as outfile:
    json.dump(data, outfile)

driver.quit()
