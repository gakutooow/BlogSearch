import requests
import json
import datetime
import time

def getBody(search_keyword,token):
    url = "https://api.hottolink.io/datainsights/articles/search"
    headers = {'Authorization': token}

    dic_list  = []
    from_date = '20171001000000'
    to_date     = '20181001000000'
    params1  ={
                'search_keyword': search_keyword,
                'not_keyword':'本日限定！ブログスタンプ',
                'from': from_date,
                'to': to_date,
                'domain': 'blog',
                'size':'1000',
                'spam_remove':'5'
                }

    r = requests.get(url, params=params1,headers=headers)
    dic_list = dic_list + json.loads(r.text)["docs"]

    while True:
        time.sleep(5)

    #to_dateとfrom_dateを更新する
        to_date = json.loads(r.text)["docs"][-1]["date"]
        to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=1)

        if to_date < datetime.datetime(2015, 10, 1):
            from_date = '20140801000000'
        else:
            from_date = to_date- datetime.timedelta(days=365)
            from_date = from_date.strftime("%Y%m%d%H%M%S")

        to_date = to_date.strftime("%Y%m%d%H%M%S")

        params1  ={
                        'search_keyword': search_keyword,
                        'not_keyword':'本日限定！ブログスタンプ',
                        'from': from_date,
                        'to': to_date,
                        'domain': 'blog',
                        'size':'1000',
                        'spam_remove':'5'
                        }

        r = requests.get(url, params=params1,headers=headers)


        print(len(dic_list))
        print(from_date)
        print(to_date)

        if json.loads(r.text)["docs"] != []:
            dic_list = dic_list + json.loads(r.text)["docs"]
        else:
            break
    return dic_list
