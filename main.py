from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
from fbrecog import FBRecog
import requests
import os
import urllib.request


#-------------------------------------------------------------------------------
# Environment Variables
#-------------------------------------------------------------------------------

try:
    USERNAME = os.environ['USER_MAIL_PROJ']
    PASSWORD = os.environ['PASSWORD_PROJ']
except KeyError:
   print("Please set the environment variables: USER_MAIL_PROJ, PASSWORD_PROJ")
   exit(1)

#-------------------------------------------------------------------------------
# Global Variables
#-------------------------------------------------------------------------------

app = Flask(__name__, template_folder='./')
likes_list_index = -1
curr_friend_name = ''
sources = {}

#-------------------------------------------------------------------------------
# Flask URLs
#-------------------------------------------------------------------------------

@app.route('/')
def render_static():
    return render_template('show_main.html')

#-------------------------------------------------------------------------------

@app.route("/getNextFrame", methods=['GET'])
def getNextFrame():
    return _get_liked_page(likes_list_index+1)

#-------------------------------------------------------------------------------

@app.route("/getPrevFrame", methods=['GET'])
def getPrevFrame():
    return _get_liked_page(likes_list_index-1)

#-------------------------------------------------------------------------------

@app.route("/getPersonName", methods=['GET','POST'])
def getPersonName():

    global curr_friend_name
    path = request.args.get('image_src') # image link passed from javascript
    access_token = 'EAAYeBD26ZAQkBADfCM3fcQqOcMCAK84UlfVOlnZB0APgRgQi0XU54MNYlJ8GuOZChBDSZBKfAmkJuH4xI477ZAA4uFRquUb0z9MEHNG1fcXHCvN4BZAiOBISBTZA06SGpqRgZB7SXjLYZBvFykjlZCqaJPVbfVBXaljtwCr1oCAz7N6nCdA0w965KHDb0dftR6KocM8i8WKjJN3BKV1H9641KJfsZAb7Nyr46wZD'
    cookies = 'datr=vyE3WK59AKHob24eJFofccbS; sb=1CE3WLBBfN52DzpYJW81Fl-E; locale=en_US; pl=n; spin=r.4342406_b.trunk_t.1537627084_s.1_v.2_; act=1537627842029%2F3; c_user=100027703129886; xs=16%3AYPAsGxXhmRO2Vw%3A2%3A1537627843%3A13822%3A-1; fr=0BF4Qlml0lg3T6JpB.AWXQ9_wabZ8f6tfmQtrjRwN_xkU.Ba-_AL.PF.Fum.0.0.BbplbC.; presence=EDvF3EtimeF1537627846EuserFA21B27703129886A2EstateFDutF1537627846949CEchFDp_5f1B27703129886F2CC; wd=1110x1038'
    fb_dtsg = 'AQHAtSNnpE3I:AQHUMYNbksuj'
    urllib.request.urlretrieve(path, "photo_for_recognition.png")

    try:
        #TODO: remove comments
        #fb_recog_obj = FBRecog(access_token, cookies, fb_dtsg)
        #recognized_friends_list = fb_recog_obj.recognize("photo_for_recognition.png")
        recognized_friends_list = [{'name': 'James Bond'}]
        if (len(recognized_friends_list) > 0):
            new_friend_name = recognized_friends_list[0]['name']
            if (new_friend_name) and (new_friend_name != curr_friend_name):
                curr_friend_name = new_friend_name

            res = jsonify({'person_name': curr_friend_name,
                           'status': 'recognized'})
        else:
            res = jsonify({'person_name': '',
                           'status': 'recognizing'})
    except Exception as err:
        print(err)
        print('Error occured, please check the token, and verify you are connected.')

    return res

#-------------------------------------------------------------------------------
# Help Functions
#-------------------------------------------------------------------------------

def _login(session, email, password):
    '''
    Attempt to login to Facebook. Returns cookies given to a user
    after they successfully log in.
    '''

    # Attempt to login to Facebook
    response = session.post('https://m.facebook.com/login.php',
                            data={'email': email, 'pass': password},
                            allow_redirects=False)
    assert response.status_code == 302
    assert 'c_user' in response.cookies
    return response.cookies

#-------------------------------------------------------------------------------

def _get_liked_page(next_index):
    global likes_list_index
    global sources

    if (sources == {}):
        _create_likes_list()
        likes_list_index = 0

    likes_list_index = next_index % len(sources)
    next_page_name = list(sources.keys())[likes_list_index]
    res = jsonify({'next_url': sources[next_page_name],
                   'page_name': next_page_name,
                   'status': 'new_fb_page'})
    return res

#-------------------------------------------------------------------------------

def _create_likes_list():
    global curr_friend_name
    global sources

    session = requests.session()
    cookies = _login(session, USERNAME, PASSWORD)
    splitted_name_of_curr_friend = 'Asia Zhivov'.lower().split(' ') # TODO: curr_friend_name
    dotted_name_of_curr_friend = splitted_name_of_curr_friend[0] + '.' + splitted_name_of_curr_friend[-1]
    likes_url = 'https://www.facebook.com/' + dotted_name_of_curr_friend +'/likes?lst=1198688678%3A843054236%3A1535896155'
    response = session.get(likes_url, cookies=cookies, allow_redirects=False)
    assert response.text.find('Home') != -1

    # For visual see, use: http://codebeautify.org/htmlviewer/
    soup = BeautifulSoup(response.content, "html.parser")
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))    # the liked pages are in comment
    final_likes_dict = {}
    for comment in comments:
        soup_inner = BeautifulSoup(comment, 'html.parser')
        div_likes_list = soup_inner.findAll('div',{'class':['fsl fwb fcb', 'fsl fwb fcb _5wj-']}) # one for eng. and one for heb.
        for div_like in div_likes_list:
            div_like_link = div_like.find('a')
            final_likes_dict[div_like_link.text] = div_like_link['href']

    sources = final_likes_dict

#-------------------------------------------------------------------------------
# Main Function
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)


