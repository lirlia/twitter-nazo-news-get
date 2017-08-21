# -*- coding: utf-8 -*-

from requests_oauthlib import OAuth1Session
import os
import sys
import urllib
import json
import datetime
from pytz import timezone
from dateutil import parser
import boto3
import random
import hashlib
import base64
import requests
import re
from xml.sax.saxutils import *

## Twitter系の変数
# OAuth認証 セッションを開始
CK = os.getenv('Twitter_Consumer_Key')          # Consumer Key
CS = os.getenv('Twitter_Consumer_Secret_Key')   # Consumer Secret
AT = os.getenv('Twitter_Access_Token_Key')      # Access Token
AS = os.getenv('Twitter_Access_Token_Secret')   # Accesss Token Secert

twitter = OAuth1Session(CK, CS, AT, AS)

twitterListID = 795464117347721216  # TwitterリストID
twitterListCount = 500              # 一度に取得するリストのアカウント数
twitterFav = 10                     # 集計対象Fav数
twitterRT = 10                      # 集計対象RT数
twitterListName = 'tenhouginsama/nazo-news'

regionName = 'ap-northeast-1'               # 使用するリージョン名

## Hatena系の変数
hatenaUsername = 'lirlia'
hatenaPassword = os.environ.get('Hatena_Password')
hatenaBlogname = 'lirlia.hatenablog.com'
hatenaDraft = 'no'
hatenaAuthor = 'ぎん'


#
# 特定の条件を満たすTweetを検索
# 引数：twitterのid(tenhouginsama)
# 戻り値: 条件を満たしたツイートの検索結果
# https://dev.twitter.com/rest/reference/get/search/tweets
#
def SearchTweet(today):

    lastWeek = today - datetime.timedelta(days=7)
    url = "https://api.twitter.com/1.1/search/tweets.json"

    searchWord = \
        '-RT list:' + twitterListName +  ' ' + \
        'since:' + lastWeek.strftime("%Y-%m-%d") + '_12:00:00_JST ' \
        'until:' + today.strftime("%Y-%m-%d") + '_11:59:59_JST ' \
        'min_faves:' + str(twitterFav) + ' ' \
        'min_retweets:' + str(twitterRT)

    params = {'q': searchWord, 'count': 100 }
    req = twitter.get(url, params = params)

    # レスポンスを確認
    if req.status_code != 200:
        print ("Error: %d" % req.status_code)
        sys.exit()

    return json.loads(req.text)


#
# WSSE認証の取得
#
def Wsse():
    created = datetime.datetime.now().isoformat() + 'Z'
    nonce = hashlib.sha1(str(random.random())).digest()
    digest = hashlib.sha1(nonce + created + hatenaPassword).digest()

    return 'UsernameToken Username="{}", PasswordDigest="{}", Nonce="{}", Created="{}"'.format(hatenaUsername, base64.b64encode(digest), base64.b64encode(nonce), created)

#
# HatenaBlogへの記事の投稿
#
def PostHatena(nazoList, today):

    lastWeek = today - datetime.timedelta(days=7)

    day1 = lastWeek.strftime("%Y/%m/%d")
    day2 = today.strftime("%Y/%m/%d")

    year = str(today.strftime("%Y"))

    title = u'リアル脱出ゲーム・謎解きの今週のニュース(' \
        + day1 + u'〜' + day2 + u') ';

    body = \
        u'<p><img class="hatena-fotolife" title="画像" src="https://cdn-ak.f.st-hatena.com/images/fotolife/l/lirlia/20170612/20170612112453.jpg" alt="f:id:lirlia:20161124194747j:plain" /></p>' \
        u'<p><!-- more --></p>' \
        u'<p></p>' \
        u'<p>こんにちは、<span id="myicon"> </span><a href="https://twitter.com/intent/user?original_referer=http://lirlia.hatenablog.com/&amp;region=follow&amp;screen_name=tenhouginsama&amp;tw_p=followbutton&amp;variant=2.0">ぎん</a>です。' \
        u'<p>' + \
        day1 + u'〜' + day2 + u'の期間に話題の、<strong>リアル脱出ゲーム・リアル謎解き関連のニュース</strong>を紹介します。これだけみれば最新状況が追える！</p>' \
        u'<p></p>' \
        u'<p>[:contents]</p>' \
        u'<p></p>' \
        u'<h3>今週話題のニュース一覧</h3>'

    i_before = ""
    # 配列内の辞書要素（Twitter名）で並び替え
    import time
    sortNazoList = sorted(nazoList, key=lambda k: (k['userName'],int(k['tweetID'])))

    for i in sortNazoList:
        if i_before != "":
            if i['userName'] == i_before['userName']:
                body = body + u'<p>[https://twitter.com/' + i['twitterID'] + u'/status/' + str(i['tweetID']) + u':embed]</p>'
            else:
                body = body + u'<h4>' + i['userName'].replace(u'&',u' ') + u'</h4>' + \
              u'<p>[https://twitter.com/' + i['twitterID'] + u'/status/' + str(i['tweetID']) + u':embed]</p>'
        else:
            body = body + u'<h4>' + i['userName'].replace(u'&',u' ') + u'</h4>' + \
          u'<p>[https://twitter.com/' + i['twitterID'] + u'/status/' + str(i['tweetID']) + u':embed]</p>'

        i_before = i

    body = body +  u'<h3>この記事について</h3>' \
        u'<h4>集計の条件</h4>' \
        u'<p>Twitterから話題の記事を集める条件についてまとめます。</p>' \
        u'<ul>' \
        u'<li>' + day1 + u' 12:00:00(JST) 〜' + day2 + u' 11:59:59(JST) の期間に投稿されたツイートであること。</li>' \
        u'<li>データ集計タイミング(' + day2 + u' 21:00)にRTが' + str(twitterRT) + u'以上であること。</li>' \
        u'<li>データ集計タイミング(' + day2 + u' 21:00)にお気に入り数が' + str(twitterFav) + u'以上であること。</li>' \
        u'<li>-RT数、お気に入り数の条件は今後変動の可能性があります。</li></ul>' \
        u'<p></p>' \
        u'<p>【注意】</p>' \
        u'<p>フォローワー数1万以上のアカウントについてはRTが' + str(int(twitterRT) * 5) + u'以上、お気に入り数が' + str(int(twitterFav) * 5) + u'以上であることとしています。</p>' \
        u'<p></p>' \
        u'<h4>集計対象Twitterアカウント</h4>' \
        u'<p>集計対象アカウントは下記のTwitterリストとなります。</p>' \
        u'<ul><li>https://twitter.com/tenhouginsama/lists/nazo-news/members</li></ul>' \
        u'<p></p>' \
        u'<p><strong>「このアカウントも収集対象に追加して欲しい」</strong>というご要望があれば[https://twitter.com/intent/user?original_referer=http%3A%2F%2Flirlia.hatenablog.com%2F&amp;region=follow&amp;screen_name=tenhouginsama&amp;tw_p=followbutton&amp;variant=2.0:title=(@tenhouginsama)]までご連絡ください</p>' \
        u'<p></p>' \
        u'<h4>記事の修正について</h4>' \
        u'<p>この記事は<strong>自動投稿</strong>されています。明らかに違うツイートが貼り付けられている場合はお手数ですが[https://twitter.com/intent/user?original_referer=http%3A%2F%2Flirlia.hatenablog.com%2F&amp;region=follow&amp;screen_name=tenhouginsama&amp;tw_p=followbutton&amp;variant=2.0:title=(@tenhouginsama)]までご連絡ください。</p>'
    body = escape(body)
    data = \
        u'<?xml version="1.0" encoding="utf-8"?>' \
        u'<entry xmlns="http://www.w3.org/2005/Atom"' \
        u'xmlns:app="http://www.w3.org/2007/app">' \
        u'<title>' + title + '</title>' \
        u'<author><name>name</name></author>' \
        u'<content type="text/plain">' + body + u'</content>' \
        u'<category term="今週のニュース" />' \
        u'<category term="今週のニュース-' + year + u'年" />' \
        u'<app:control>' \
        u'<app:draft>' + hatenaDraft + '</app:draft>' \
        u'</app:control>' \
        u'</entry>'

    headers = {'X-WSSE': Wsse()}
    url = 'http://blog.hatena.ne.jp/{}/{}/atom/entry'.format(hatenaUsername, hatenaBlogname)
    req = requests.post(url, data=data.encode('utf-8'), headers=headers)

    if req.status_code != 201:
        print ("Error: %d" % req.status_code)
        sys.exit()

def lambda_handler(event, context):

    nazoList = []

    ## その他の変数
    # AWS Lamdaで稼働させる場合UTCのため、JSTに変換するために0900を足す
    # たさない場合日がずれてしまい、意図通りに集計できない

    # lambda_handlerの中じゃないと時刻が再取得されない場合があるので移動
    # http://qiita.com/yutaro1985/items/a24b572624281ebaa0dd
    today = datetime.datetime.today() + datetime.timedelta(hours=9)

    # 対象のアカウントのツイートから条件を満たしているものを抽出
    for tweet in SearchTweet(today)['statuses']:

        # 取得したツイートが条件を満たしていない場合があるので排除する
        if int(tweet['retweet_count']) < twitterRT or \
            int(tweet['favorite_count']) < twitterFav:
            continue

        # フォロワー数1万超える団体アカウントはこっち
        if int(tweet['user']['followers_count']) > 9999:
            if int(tweet['retweet_count']) < twitterRT * 5 or \
                int(tweet['favorite_count']) < twitterFav * 5:
                continue

        # データの格納
        nazoList.append({
            'userName': tweet['user']['name'],
            'tweetID': tweet['id_str'],
            'twitterID': tweet['user']['screen_name'],
            'rt': tweet['retweet_count'],
            'fav': tweet['favorite_count']
        })


    # ブログへ記事を投稿
    PostHatena(nazoList, today)

    return { "messages":"success!" }
