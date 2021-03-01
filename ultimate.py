import sqlite3
import urllib.error
import ssl
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import re
import os
import json
import matplotlib.pyplot as plt

# Ignore SSL    errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

#Preping the database

conn = sqlite3.connect('economydata.sqlite')
cur = conn.cursor()

cur.execute(''' CREATE TABLE IF NOT EXISTS Countries
     (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE , name TEXT UNIQUE , iso TEXT, ok TEXT)''')

cur.execute(''' CREATE TABLE IF NOT EXISTS Dados
     (country TEXT, gdp FLOAT, gdpc FLOAT, gdpg FLOAT, gdpcg FLOAT)''')

#Getting the pre-data for the API

isos = dict()

helper = 0
req = Request('https://www.nationsonline.org/oneworld/country_code_list.htm', headers={'User-Agent': 'Mozilla/5.0'})
pais = list()
site = urlopen(req, context = ctx).read()
soup = BeautifulSoup(site, 'html.parser')
tags = soup('tr')
for tag in tags:
    tag = str(tag)
    pais.append(tag)
for item in pais:
    if re.search('''<tr class="border1">
<td><div class="flag" id="[A-Z]+"></div></td>
<td class="abs"><a href=.+>.+</td>
<td style="text-align:center">[A-Z]{2}</td>
<td style="text-align:center">[A-Z]{3}</td>
<td style="text-align:center">[0-9]+</td>
</tr>''', item) is not None:
        name = re.findall('''<tr class="border1">
<td><div class="flag" id=".+"></div></td>
<td class="abs"><a href=.+>(.+)<.+</td>
<td style="text-align:center">[A-Z]{2}</td>
<td style="text-align:center">[A-Z]{3}</td>
<td style="text-align:center">[0-9]+</td>
</tr>''', item)[0]
        iso = re.findall('''<tr class="border1">
<td><div class="flag" id=".+"></div></td>
<td class="abs"><a href=.+>.+<.+</td>
<td style="text-align:center">([A-Z]{2})</td>
<td style="text-align:center">[A-Z]{3}</td>
<td style="text-align:center">[0-9]+</td>
</tr>''', item)[0]
        isos[str(name)] = str(iso).lower()
        helper = helper + 1

for item in isos:
    cur.execute(' INSERT OR IGNORE INTO Countries (name) VALUES (?)' , (item,))
    cur.execute(' UPDATE Countries SET iso = ? WHERE name = ?' , (isos[item], item))
    cur.execute('')
conn.commit()

while True:
    cur.execute("SELECT * FROM Countries WHERE iso is not NULL and ok is NULL ORDER BY name LIMIT 1")
    try:
        id_share = cur.fetchone()[0]
        cur.execute("INSERT INTO Dados (country) VALUES (?)", (id_share,))
        cur.execute("UPDATE Countries SET ok = ? WHERE id = ?", ("Sim", id_share))
        continue
    except:
        break

    conn.commit()

dic = dict()
dic["gdp"] = "NY.GDP.MKTP.CD"
dic["gdpc"] = "NY.GDP.PCAP.CD"
dic["gdpg"] = "NY.GDP.MKTP.KD.ZG"
dic["gdpcg"] = "NY.GDP.PCAP.KD.ZG"

cur.execute('SELECT * FROM Countries WHERE iso is not NULL ORDER BY id')
list1 = cur.fetchall()

print('TOTAL DE PAÍSES ANALISADOS:  ', len(list1))

print("\n")


request = input("Quer os dados agora?  ")
if len(request) == 0:
    for indicator in dic:
        for conjunt in list1:
            suffix = conjunt[2]
            new_id = conjunt[0]
            try:
                url = "http://api.worldbank.org/v2/country/" + suffix + "/indicator/" + dic[indicator] + "?date=2008:2018&format=json"
                api = urlopen(url, context = ctx).read()
                info = json.loads(api)
                helper = 0
                try:
                    for item in info[1]:
                        try:
                            if helper == 0:
                                name = item["country"]["value"]
                                helper = helper + 1
                                if item["value"] is None:
                                    valor = 0
                                else:
                                    valor = item["value"]
                                    indic = item["indicator"]["value"]
                            elif helper <= 11:
                                helper = helper + 1
                                if item["value"] is None:
                                    none_skip = 0
                                    valor = valor + none_skip
                                else:
                                    valor = valor + item["value"]
                        except:
                            continue

                    print("OK WITH: ", name, " in indicator = ", indic)
                    print("Medium of indicator is:  ", valor/helper)
                    if indicator == "gdp":
                        cur.execute('UPDATE Dados SET gdp = ? WHERE country = ?', (valor/helper, new_id))
                    if indicator == "gdpc":
                        cur.execute('UPDATE Dados SET gdpc = ? WHERE country = ?', (valor/helper, new_id))
                    if indicator == "gdpg":
                        cur.execute('UPDATE Dados SET gdpg = ? WHERE country = ?', (valor/helper, new_id))
                    if indicator == "gdpcg":
                        cur.execute('UPDATE Dados SET gdpcg = ? WHERE country = ?', (valor/helper, new_id))

                except:
                    continue
            except:
                continue
conn.commit()

print("\n")

#Building the figures with matplotlib

fig1, ax1 = plt.subplots()
fig2, ax2 = plt.subplots()
fig3, ax3 = plt.subplots()
fig4, ax4 = plt.subplots()
plt.style.use('fivethirtyeight')

ygdp_countries = list()
x_gdp = list()

cur.execute('SELECT Countries.name, Dados.gdp FROM Countries JOIN Dados WHERE Countries.id = Dados.country ORDER BY gdp DESC LIMIT 10')
big_gdp = cur.fetchall()

for util in big_gdp:
    ygdp_countries.append(util[0])
    x_gdp.append(float(util[1]))

lenght = range(len(x_gdp))

true_countries = [0,0,0,0,0,0,0,0,0,0]
true_gdp = [0,0,0,0,0,0,0,0,0,0]

for num in lenght:
    if len(str(round(x_gdp[num]))) == 14:
        x_gdp[num] = float(str(x_gdp[num])[:2] + '.' + str(x_gdp[num])[2:3])
    else:
        x_gdp[num] = float(str(x_gdp[num])[:1] + '.' + str(x_gdp[num])[1:2])

for item in range(len(ygdp_countries)):
        true_countries[item] = ygdp_countries[abs(item - (len(ygdp_countries) - 1))]

for item in lenght:
    true_gdp[item] = x_gdp[abs(item - (len(ygdp_countries) - 1))]


true_countries[9] = 'USA'
true_countries[5] = 'UK'
true_countries[1] = 'Russia'
print('Gráfico do GDP:  OK!')
print('\n')
helping_hand = list()

for item in range(len(true_gdp)):
    if item == 0:
        helping_hand.append(1)
        helper = 1
    else:
        helping_hand.append((true_gdp[item] - true_gdp[item-1] + helper))
        helper = (true_gdp[item] - true_gdp[item-1]) + helper

ax1.barh(true_countries, helping_hand)
ax1.set_xticks(helping_hand)
ax1.set_xticklabels(labels = [true_gdp[0],'','','','',true_gdp[5]] + true_gdp[6:], fontsize = 'x-small', rotation = 45.0)
ax1.set_xlabel('GDP in trillions of US$')
ax1.set_title('Highest gdp average (2008-2018)')

#DELETING THE CURRENT LIST OF DATA AND ADDING SOME NEW ONE

ygdp_countries.clear()
x_gdp.clear()
true_gdp.clear()
true_countries.clear()
helping_hand.clear()

ygdpc_countries = list()
x_gdpc = list()
true_gdpc = [0,0,0,0,0,0,0,0,0,0]
true_countries = [0,0,0,0,0,0,0,0,0,0]

cur.execute('SELECT Countries.name, Dados.gdpc FROM Countries JOIN Dados WHERE Countries.id = Dados.country ORDER BY gdpc DESC LIMIT 10')
big_gdpc = cur.fetchall()
for data in big_gdpc:
    ygdpc_countries.append(data[0])
    x_gdpc.append(data[1])

for item in range(len(ygdpc_countries)):
        true_countries[item] = ygdpc_countries[abs(item - (len(ygdpc_countries) - 1))]

for sub in range(len(x_gdpc)):
    if len(str(round(x_gdpc[abs(sub - (len(x_gdpc) - 1))]))) == 6:
        true_gdpc[sub] = float(str(x_gdpc[abs(sub - (len(x_gdpc) - 1))])[0:3] + '.' + str(x_gdpc[abs(sub - (len(x_gdpc) - 1))])[3:4])
    else:
        true_gdpc[sub] = float(str(x_gdpc[abs(sub - (len(x_gdpc) - 1))])[0:2] + '.' + str(x_gdpc[abs(sub - (len(x_gdpc) - 1))])[2:3])

for item in range(len(true_gdpc)):
    if item == 0:
        helping_hand.append(1)
        helper = 5
    else:
        helping_hand.append((true_gdpc[item]-true_gdpc[item-1]) + helper)
        helper = (true_gdpc[item]-true_gdpc[item-1]) + helper

ax2.barh(true_countries, helping_hand)
ax2.set_xticks(helping_hand)
ax2.set_xticklabels([true_gdpc[0],'',''] + true_gdpc[3:], fontsize = 'x-small', rotation = 45.0)
ax2.set_xlabel('GDP/Cap in Thousands US$')
ax2.set_title('Top GDP/Cap average (2008-2018)')

true_gdpc.clear()
true_countries.clear()
helping_hand.clear()

#Now for the gdp growth
x_gdpg = list()
cur.execute('SELECT Countries.name, Dados.gdpg FROM Countries JOIN Dados WHERE Countries.id = Dados.country ORDER BY gdpg DESC LIMIT 10')
big_gdpg = cur.fetchall()
for item in range(len(big_gdpg)):
    if '.' in str(big_gdpg[abs(item - (len(big_gdpg)-1))][1])[:2]:
        x_gdpg.append(float(str(big_gdpg[abs(item - (len(big_gdpg)-1))][1])[:1] + '.' + str(big_gdpg[abs(item - (len(big_gdpg)-1))][1])[2:4]))
    else:
        x_gdpg.append(float(str(big_gdpg[abs(item - (len(big_gdpg)-1))][1])[:2] + '.' + str(big_gdpg[abs(item - (len(big_gdpg)-1))][1])[3:5]))

    true_countries.append(big_gdpg[abs(item - (len(big_gdpg) - 1))][0])

for sub in range(len(x_gdpg)):
    if sub == 0:
        helping_hand.append(1)
        helper = 1
    else:
        helping_hand.append((x_gdpg[sub]-x_gdpg[sub-1]) + helper)
        helper = (x_gdpg[sub]-x_gdpg[sub-1]) + helper

ax3.barh(true_countries, helping_hand)
ax3.set_xticks(helping_hand)
ax3.set_xticklabels(labels = ['',x_gdpg[1],'',x_gdpg[3],'',x_gdpg[5]] + x_gdpg[6:], fontsize = 'x-small', rotation = 45.0)
ax3.set_xlabel('GDP percent growth (%)')
ax3.set_title('Biggest GDP growth in 2008-2018')

true_countries.clear()
helping_hand.clear()
x_gdpg.clear()

x_gdpcg = list()
cur.execute('SELECT Countries.name, Dados.gdpcg FROM Countries JOIN Dados WHERE Countries.id = Dados.country ORDER BY gdpcg DESC LIMIT 10')
big_gdpcg = cur.fetchall()

for sub in range(len(big_gdpcg)):
    true_countries.append(big_gdpcg[abs(sub - (len(big_gdpcg) - 1))][0])
    x_gdpcg.append(float(str(big_gdpcg[abs(sub - (len(big_gdpcg)- 1))][1])[0] + '.' + str(big_gdpcg[abs(sub - (len(big_gdpcg)- 1))][1])[2:4]))

for item in range(len(x_gdpcg)):
    if item == 0:
        helping_hand.append(1)
        helper = 1
    else:
        helping_hand.append((x_gdpcg[item] - x_gdpcg[item - 1]) + helper)
        helper =  (x_gdpcg[item] - x_gdpcg[item - 1]) + helper

ax4.barh(true_countries, helping_hand)
ax4.set_xticks(helping_hand)
ax4.set_xticklabels(labels = [x_gdpcg[0],'','','',x_gdpcg[4],''] + x_gdpcg[6:], fontsize = 'x-small', rotation = 45.0)
ax4.set_xlabel('GDP per Capita Growth (%)')
ax4.set_title('Biggest GDP per capita growth (2008-2018)')

plt.tight_layout()
plt.show()

cur.close()
conn.close()
