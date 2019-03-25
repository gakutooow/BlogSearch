import numpy as np
import pandas as pd
from pandas import DataFrame
import requests
import json
from pymongo import MongoClient
import datetime
import time
import re
from statistics import mean, median,variance,stdev
import MeCab
import collections
import gensim
from gensim import corpora, models


def count(search_keyword_list,session_id):
    url = "https://api.hottolink.io/datainsights/articles/counts/trend"
    headers = {'Authorization': session_id}

    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.blogdb

    for search_keyword in search_keyword_list:
        dic_list = []

        params1  = {'search_keyword': search_keyword,
                    'not_keyword':'',
                    'from': '20140501000000',
                    'to': '20140709000000',
                    'domain': 'blog',
                    'spam_remove':'5',
                    'interval':'1d'}

        r = requests.get(url, params=params1,headers=headers)
        dic_list = json.loads(r.text)

        today = datetime.datetime.now().strftime('%m%d')+'000000'

        for i in [4,5,6,7]:
            params1  = {'search_keyword': search_keyword,
                        'not_keyword':'',
                        'from': f'201{i}{today}',
                        'to': f'201{i+1}{today}',
                        'domain': 'blog',
                        'spam_remove':'5',
                        'interval':'1d'}

            r = requests.get(url, params=params1,headers=headers)
            dic_list = dic_list + json.loads(r.text)

        col = db["count_{}".format(search_keyword)]

        for blog in dic_list:
            col.insert(blog)

def body(search_keyword_list,session_id):
    url = "https://api.hottolink.io/datainsights/articles/search"
    headers = {'Authorization': session_id}

    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.blogdb

    for search_keyword in search_keyword_list:
        to_date = datetime.datetime.now().strftime('%Y%m%d')+'000000'
        last_year = datetime.datetime.now()- datetime.timedelta(days=365)
        from_date = last_year.strftime('%Y%m%d')+'000000'

        dic_list  = []

        params1  = {'search_keyword': search_keyword,
                    'not_keyword':'',
                    'from': from_date,
                    'to': to_date,
                    'domain': 'blog',
                    'size':'1000',
                    'spam_remove':'5'}

        r = requests.get(url, params=params1,headers=headers)

        dic_list = dic_list + json.loads(r.text)["docs"]


        j = 1
        while True:
            time.sleep(5)
            to_date = json.loads(r.text)["docs"][len(json.loads(r.text)["docs"])-1]["date"]
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=1)
            to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")
            to_date = re.sub('[-: ]', '', to_date)


            if int(to_date) < 20150301000000:
                from_date = '20140301000000'
            else:
                str_list = list(to_date)
                str_list[3] = str(int(str_list[3]) - 1 )
                from_date = "".join(str_list)


            # うるう年対応
            if list(from_date)[4] == '0' and list(from_date)[5] == '2' and list(from_date)[6] == '2' and list(from_date)[7] == '9':
                from_date = '20150301000000'


            params1  = {'search_keyword': search_keyword,
                        'not_keyword':'',
                        'from': from_date,
                        'to': to_date,
                        'domain': 'blog',
                        'size':'1000',
                        'spam_remove':'5'}

            r = requests.get(url, params=params1,headers=headers)


            print(len(dic_list))
            print(from_date)
            print(to_date)


            try:
                dic_list = dic_list + json.loads(r.text)["docs"]

                if len(json.loads(r.text)["docs"]) == 0:
                    col = db[search_keyword]

                    for blog in dic_list:
                        col.insert(blog)

                    break

            except KeyError:
                col = db[search_keyword]

                for blog in dic_list:
                    col.insert(blog)

                break

def getSpike(search_keyword_list,stop_word):

    from pymongo import MongoClient
    client = MongoClient('localhost', 27017)
    db = client.blogdb

    word_dic = {}

    for search_keyword in search_keyword_list:
        print(search_keyword)

        col = db["count_{}".format(search_keyword)]
        col2 = db[search_keyword]

        #日ごとの記事数をデータフレーム化
        date_list = []
        count_list = []

        for i in range(col.count()):
            date_list.append(col.find()[i]["from"].split(" ")[0])
            count_list.append(col.find()[i]["count"])


        df = pd.DataFrame(index = date_list)

        df["count"] = count_list

        #画像出力and 保存
        ax = df[:].plot( y=["count"], figsize=(16,4), alpha=0.5)
        fig = ax.get_figure()
        fig.savefig('画像/{}.png'.format(search_keyword))


        #前月平均+5*標準偏差である日を抽出　→　trend_dates
        trend_dates = []
        for start in range(len(df)-31):
            pre_data = []
            for i in range(start,start+30):
                pre_data.append(df.iloc[i]["count"])

            ave = mean(pre_data)
            sd = stdev(pre_data)


            if df.iloc[start+30]["count"] > ave + sd*5 and df.iloc[start+30]["count"]  >=30:
                trend_dates.append(df.index[start+30])



        #二日連続で再燃している場合、セットで考える
        for g in range(len(trend_dates)):
            try:
                if datetime.datetime.strptime(trend_dates[g], "%Y-%m-%d") + datetime.timedelta(days=1) == datetime.datetime.strptime(trend_dates[g+1], "%Y-%m-%d"):
                    trend_dates[g] = [trend_dates[g],trend_dates[g+1]]
                    trend_dates.pop(g+1)

            except IndexError:
                pass

        num = 1 #辞書を作成するときに、trend_date的に２日目以降はappendするために識別する
        for trend_date in trend_dates:
            print(trend_date)
            #再燃日のブログボディを抽出　→　trend_boby_list
            trend_boby_list = []

            for i in range(col2.count()):
                date = col2.find()[i]["date"].split(" ")[0]
                if date in trend_date:
                    trend_boby_list.append(col2.find()[i]["body"])

                if i%1000 ==0:
                    print(i)


            # 名詞・動詞・形容詞・形容動詞のみを抽出
            tagger = MeCab.Tagger()
            texts = []

            for t in range(len(trend_boby_list)):
                word = []
                result = tagger.parse(trend_boby_list[t]).split("\n")

                for r in result:
                    if r.split("\t")[0] == "EOS":
                        break
                    if r.split("\t")[1].split(",")[0] in ["形容詞","動詞","名詞","形容動詞"]:
                        word.append(r.split("\t")[1].split(",")[-3])

                texts.append(word)


            #ストップワード除去でtexts→docs
            stop_word = stop_word + search_keyword_list

            docs = []
            for i in range(len(texts)):
                docs.append([doc for doc in texts[i] if doc not in stop_word])


            a = []
            for doc in docs:
                for w in doc:
                    a.append(w)

            c = collections.Counter(a)

            if num == 1:
                if type(trend_date) == str:
                    word_dic[search_keyword] = [{trend_date : c.most_common(20),"number" : df.loc[trend_date].values[0]}]

                else:
                    word_dic[search_keyword] = [{trend_date[0] : c.most_common(20),"number" : df.loc[trend_date[0]].values[0]}]
                num = 2

            else:
                if type(trend_date) == str:
                    word_dic[search_keyword].append({trend_date : c.most_common(20),"number" : df.loc[trend_date].values[0]})

                else:
                    word_dic[search_keyword].append({trend_date[0] : c.most_common(20),"number" : df.loc[trend_date[0]].values[0]})

    print(word_dic)
