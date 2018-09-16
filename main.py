from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
from urllib.request import urlopen
from fbrecog import FBRecog
import requests
import os

'''
path = 'mypic.jpg'
access_token = 'EAAYeBD26ZAQkBAPZBBURrrKoaXaIGOsTVLGHl9cUh0NYCo8PkCl0WIvZCgE9V2zUESxlpsaVpTgZC7sjJuc9ltDZAFtRrxjrT0bj7u9MQGfqRFjzfAIGVSCZAOfGbLzinqZADjauLZCmUYZBYNOmZCWVZAmbRKVR5zFRj8ZCnfAvIDLO4GKKYVFS5mNXVVpcieSkbv4rjEcKqRoMOcdqkZCuyWDnZBrlTt9XmrYs4ZD'
cookies = 'sb=xDdxW6gnARIAtC4XMxe0BTwL; datr=xDdxW7Ne7c2Tg4zreHGGsN8H; locale=en_US; dpr=1.5; pl=n; spin=r.4202043_b.trunk_t.1534169873_s.1_v.2_; act=1534169897844%2F3; c_user=100027703129886; xs=3%3ADZ81QAh8MPsC6g%3A2%3A1534169906%3A13822%3A-1; fr=0TeCrTm3A0MBtwlTt.AWWu3NCJcvYikAivBG9oC_YCZPs.BbcTfE.Qp.Ftx.0.0.BbcZMy.; presence=EDvF3EtimeF1534169900EuserFA21B27703129886A2EstateFDutF1534169900866CEchFDp_5f1B27703129886F2CC; wd=1113x830'
fb_dtsg = 'AQH94-Qo091F:AQEa7lhShlER'

# Instantiate the recog class
recog = FBRecog(access_token, cookies, fb_dtsg)

# Recog class can be used multiple times with different paths
# mike = 123059741964232
#temp = recog.get_user_data('/me/friends?field')

#recognized = recog.recognize(path)
#friend_name = recognized[0]['name']
'''

try:
    USERNAME = os.environ['USER_MAIL_PROJ']
    PASSWORD = os.environ['PASSWORD_PROJ']
except KeyError:
   print("Please set the environment variables: USER_MAIL_PROJ, PASSWORD_PROJ")
   exit(1)

app = Flask(__name__, template_folder='./')
PROTECTED_URL = 'https://www.facebook.com/asia.zhivov/likes?lst=1198688678%3A843054236%3A1535896155'
i = -1
global sources

@app.route('/') # <string:page_name>/
def render_static():
    return render_template('show_main.html')

@app.route("/getNextFrame", methods=['GET'])
def getData():
    global i
    global sources

    next_page_name = list(sources.keys())[i]
    friend_name = 'NAME_OF_MIKE'
    res = jsonify({'next_url': '',
                   'person_name': '',
                   'page_name': '',
                   'status': 'recognizing'
                   })
    if i > -1:
        res = jsonify({'next_url': sources[next_page_name],
                       'person_name': friend_name,
                       'page_name': next_page_name,
                       'status': 'recognized'
                       })

    i = (i + 1) % len(sources)
    return res



def login(session, email, password):
    '''
    Attempt to login to Facebook. Returns cookies given to a user
    after they successfully log in.
    '''

    # Attempt to login to Facebook
    response = session.post('https://m.facebook.com/login.php', data={ 'email': email, 'pass': password}, allow_redirects=False)

    assert response.status_code == 302
    assert 'c_user' in response.cookies
    return response.cookies


if __name__ == '__main__':

    session = requests.session()
    cookies = login(session, USERNAME, PASSWORD)

    response = session.get(PROTECTED_URL, cookies=cookies, allow_redirects=False)
    assert response.text.find('Home') != -1

    # to visually see if you got into the protected page, I recomend copying
    # the value of response.text, pasting it in the HTML input field of
    # http://codebeautify.org/htmlviewer/ and hitting the run button
    soup = BeautifulSoup(response.content, "html.parser")
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))
    final_likes_dict = {}
    for comment in comments:
        soup_inner = BeautifulSoup(comment, 'html.parser')
        div_likes_list = soup_inner.findAll('div',{'class':['fsl fwb fcb', 'fsl fwb fcb _5wj-']}) # one for eng. and one for heb.
        for div_like in div_likes_list:
            div_like_link = div_like.find('a')
            final_likes_dict[div_like_link.text] = div_like_link['href']

    #for liked_page, link_page in final_likes_dict.items():
    #    print(link_page)

    global sources
    sources = final_likes_dict

    # For posts retrieving from pages
    '''
    posts_links_to_show = []
    for liked_page, link_page in final_likes_dict.items():
        #print(link_page)
        page_name = link_page.split('/')[-2]
        new_link = link_page.replace(page_name, 'pg/' + page_name + '/posts/?ref=page_internal')
        #print(new_link)
        posts_links_to_show.append(new_link)

    final_posts_list = []
    for liked_page in posts_links_to_show:
        response = urlopen(liked_page)
        soup = BeautifulSoup(response.read(), "html.parser")
        posts_object = soup.find('span', {'class': 'fsm fwn fcg'})
        if posts_object is not None:
            div_like_link = posts_object.find('a')
            link_to_append = 'https://www.facebook.com' + div_like_link['href']
            final_posts_list.append(link_to_append)

    for post in final_posts_list:
        print(post)
    '''

    app.run(debug=True)

