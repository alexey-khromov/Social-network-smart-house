from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
from fbrecog import FBRecog
import requests
import os

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
global likes_list_index
global sources
global curr_friend_name

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
    access_token = 'EAAYeBD26ZAQkBAGZARk0n7FUJHr9ogTmdkEjprDgA7ZAIN2mb3KGM4JP4SDRujYIRz38OEqxJMB8HMzZCmiKt2pXS1ZCNK0xZCCnfwF6CJyq4YTgz2VlL84yL9ZBj5FameBL6d5uGGWCHPc8bjYC4mVOn0EMfZAuHZBEuh1q7faxyt8mfb2lROcYBRKEtU2Fvvn3VyMexAVZASOiigDgW9pAkQYFpXz59jxZCsZD'
    cookies = 'datr=vyE3WK59AKHob24eJFofccbS; sb=1CE3WLBBfN52DzpYJW81Fl-E; ; dpr=1.25; locale=en_US; pl=n; spin=r.4337968_b.trunk_t.1537532329_s.1_v.2_; act=1537532373473%2F5; c_user=100027703129886; xs=16%3At3Ha5ucHq6yxLg%3A2%3A1537532374%3A13822%3A-1; fr=0BF4Qlml0lg3T6JpB.AWV3-y7bMhKTugzLs8JzD24V8NQ.Ba-_AL.PF.Fuk.0.0.BbpOHW.; presence=EDvF3EtimeF1537532378EuserFA21B27703129886A2EstateFDutF1537532378401CEchFDp_5f1B27703129886F2CC; wd=1110x1038'
    fb_dtsg = 'AQHufDWSC85X:AQEW6RNDXeCH'

    fb_recog_obj = FBRecog(access_token, cookies, fb_dtsg)
    recognized_Pfriends_list = fb_recog_obj.recognize(path)
    if (len(recognized_Pfriends_list) > 0):
        new_friend_name = recognized_Pfriends_list[0]['name']
        if (curr_friend_name) and (new_friend_name != curr_friend_name):
            curr_friend_name = new_friend_name
            _create_likes_list()
            likes_list_index = 0
        res = {'person_name': curr_friend_name,
               'status': 'recognized'}
    else:
        res = jsonify({'person_name': '',
                       'status': 'recognizing'})

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
    global curr_friend_name

    like_index = next_index % len(sources)
    next_page_name = list(sources.keys())[likes_list_index]
    if likes_list_index > -1:
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


