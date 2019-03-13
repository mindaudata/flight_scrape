import requests
from bs4 import BeautifulSoup
import re
import pandas


user_agent = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'}


# Single request to api -> finding out which days have available flights
# Although api is disallowed in 'robots.txt' - this is only a single request and we are not using the data directly
daysAvailable = []
try:
    urlApi = 'https://www.norwegian.com/api/fare-calendar/calendar?adultCount=1&destinationAirportCode=RIX&originAirportCode=OSL&outboundDate=2019-04-01&tripType=1&currencyCode=EUR&languageCode=en-BZ'
    apiRequest = requests.get(urlApi, headers=user_agent)
    apiJson = apiRequest.json()['outbound']['days']

    for day in apiJson:
        if day['price'] > 0:
            daysAvailable.append(int(day['date'][8:10]))
except:
    print('Api request failed')
    daysAvailable = list(range(1, 31))


# There are no flights on Saturdays
# 26 Requests on available dates for cheapest price and time of the flight

url_begin = 'https://www.norwegian.com/en/ipc/availability/avaday?AdultCount=1&A_City=RIX&D_City=OSL&D_Month=201904&D_Day='
url_end = '&IncludeTransit=false&TripType=1&CurrencyCode=EUR&mode=ab'

aprilCheapest = {}

for day in daysAvailable:
    try:
        r = requests.get(url_begin+str(day)+url_end, headers=user_agent)
        soup = BeautifulSoup(r.content.decode('utf-8'), "lxml")
        avadaytable = soup.find('table', {'class': 'avadaytable'})
        row1 = avadaytable.find_all('tr', {'class': 'rowinfo1'})
        row2 = avadaytable.find_all('tr', {'class': 'rowinfo2'})

        aprilCheapest[day] = []
        for i in range(0, len(row1)):

            if not aprilCheapest[day] or (aprilCheapest[day]['Price']) > (row1[i].find('td', {'class': 'fareselect standardlowfare'}).text):

                flight = {}
                flight['FlightNumber'] = row1[i].find(
                    'td', {'class': 'fareselect standardlowfare'}).find('input').get('value').split("|")[1]
                flight['DepartPort'] = row2[i].find(
                    'td', {'class': 'depdest'}).find('div').text
                flight['DepartTime'] = row1[i].find(
                    'td', {'class': 'depdest'}).find('div').text
                flight['ArriveTime'] = row1[i].find(
                    'td', {'class': 'arrdest'}).text
                flight['ArrivePort'] = row2[i].find(
                    'td', {'class': 'arrdest'}).text
                flight['Currency'] = row1[i].find(
                    'td', {'class': 'fareselect standardlowfare'}).find('label').get('title')
                flight['Price'] = row1[i].find(
                    'td', {'class': 'fareselect standardlowfare'}).text

                aprilCheapest[day] = flight
    except:
        print('Price and time scrape failure on day #'+str(day))

scrape = pandas.DataFrame.from_dict(aprilCheapest, orient='index')
scrape.index.name = 'April'

# Making 26 requests for Flight Taxes

for index, row in scrape.iterrows():
    try:
        taxUrl = 'https://www.norwegian.com/en/ipc/availability/avaday?D_City=OSL&A_City=RIX&TripType=1&D_Day='+str(index)+'&D_Month=201904&D_SelectedDay='+str(index)+'&R_Day='+str(
            index)+'&R_Month=201904&R_SelectedDay='+str(index)+'&dFlight='+row['FlightNumber']+'&dCabinFareType=1&IncludeTransit=false&AgreementCodeFK=-1&CurrencyCode=EUR'
        taxRequest = requests.get(taxUrl, headers=user_agent)
        taxSoup = BeautifulSoup(taxRequest.content.decode('utf-8'), "lxml")
        selectiontable = taxSoup.find('table', {'class': 'selectiontable'})
        taxSum = selectiontable.find('span', text=re.compile(
            'Taxes, Fees and Charges')).parent.parent.parent.find('td', {'class': 'rightcell'}).text
        scrape.at[index, 'Tax'] = taxSum[1:]
        scrape.at[index, 'Date'] = "201904{0:0=2d}".format(index)
    except:
        print('Tax scrape failure on day #' + str(index))

# Taxes are fixed for this particular flight
# Making a single request instead of 26 would be a good practice

scrape = scrape[['Date', 'DepartPort', 'DepartTime',
                 'ArriveTime', 'ArrivePort', 'Price', 'Tax']]

with open('OSLRIX201904.json', 'w') as f:
    f.write(scrape.to_json(orient='records'))
