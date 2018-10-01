from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
from fbrecog import FBRecog
import requests
import os
import urllib.request
import cv2
import numpy as np
from PIL import Image, ImageChops
import time

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

SEQUEL_PHOTOS_TO_KEEP = 5
PHOTO_NAME_PATTERN = "photo_for_interp_{0}.png"
app = Flask(__name__, template_folder='./')
likes_list_index = -1
curr_friend_name = ''
sequel_images_counter = 0
is_first_photo = True
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


@app.route("/getHandGesture", methods=['GET','POST'])
def getHandGesture():
    global sequel_images_counter
    path = request.args.get('image_src') # image link passed from javascript
    prev_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
    sequel_images_counter = (sequel_images_counter % SEQUEL_PHOTOS_TO_KEEP) + 1
    next_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
    urllib.request.urlretrieve(path, next_photo_name)

    global is_first_photo
    res = 'identifying gestures...'
    if is_first_photo:
        is_first_photo = False
    else:
        res = _get_hand_gesture(prev_photo_name, next_photo_name)

    return jsonify({'gesture_name': res})

#-------------------------------------------------------------------------------


@app.route("/getPersonName", methods=['GET','POST'])
def getPersonName():

    global curr_friend_name
    access_token = 'EAAYeBD26ZAQkBAG8Uphw9jhsbZCxUL5gaKZCP69iQOWpRkGrLW9sGclNQ90yBZAJhb6qc9n5YH2HTeEbIC3joYZAZB0QLwdE5FTaiZAIiHyEWscmLtVLqcMKZBl5Kqm2hGtS7kFH2UCH7pPtHMu727Ext3rcKindlYlfFLohpboLZCaVjeAbKuSX7JkSPB1BZAkkDINJz0U6DU8jN8Sgjn4WpdUQi2iGVZAeloZD'
    cookies = 'sb=9kLwWktAnKZOmrlxUuJlGvKk; datr=9kLwWo5FFaoj5mK76Z1-vShO; pl=n; dpr=1.75; spin=r.4367964_b.trunk_t.1538380847_s.1_v.2_; c_user=100027703129886; xs=16%3A2Zf8wyCzfZSO5Q%3A2%3A1538382512%3A13822%3A-1; fr=0wfDpjdR3vG29Yo3f.AWXF6IdAyo2AtuvKqiEtcU_yoaM.Ba8EL2.K_.AAA.0.0.Bbsdqw.AWX2tor5; act=1538382491391%2F0; presence=EDvF3EtimeF1538382491EuserFA21B27703129886A2EstateFDutF1538382491553CEchFDp_5f1B27703129886F4CC; wd=884x742'
    fb_dtsg = 'AQF0PNORNBXH:AQHjb-SoMx_S'
    path = request.args.get('image_src') # image link passed from javascript
    urllib.request.urlretrieve(path, "photo_for_recognition.png")

    try:
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

    if sources == {}:
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


def _get_hand_gesture(img_name_first, img_name_second):
    try:
        img_first = cv2.imread(img_name_first)
        img_second = cv2.imread(img_name_second)

        gray_img_first = cv2.cvtColor(img_first, cv2.COLOR_BGR2GRAY)
        gray_img_second = cv2.cvtColor(img_second, cv2.COLOR_BGR2GRAY)

        blur_img_first = cv2.GaussianBlur(gray_img_first, (5, 5), 0)
        blur_img_second = cv2.GaussianBlur(gray_img_second, (5, 5), 0)

        ret, thresh_img_first = cv2.threshold(blur_img_first, 150, 255, cv2.THRESH_BINARY) #  + cv2.THRESH_OTSU
        ret, thresh_img_second = cv2.threshold(blur_img_second, 150, 255, cv2.THRESH_BINARY) # + cv2.THRESH_OTSU

        # ---Compute the center/mean of the contours---
        points_first = cv2.findNonZero(thresh_img_first)
        curr_avg_first = np.mean(points_first, axis=0)

        points_second = cv2.findNonZero(thresh_img_second)
        curr_avg_second = np.mean(points_second, axis=0)

        prev_pos = curr_avg_first.tolist()[0]
        cur_pos = curr_avg_second.tolist()[0]
        print(prev_pos)
        print(cur_pos)

        #cv2.imshow('image1', thresh_img_first)
        #cv2.imshow('image2', thresh_img_second)
        #cv2.waitKey(0)

        return _compare_images_for_gesture(prev_pos, cur_pos)

    except Exception as err:
        print(err)

#-------------------------------------------------------------------------------


def _compare_images_for_gesture(first_avg, second_avg):

    delta_x, delta_y = first_avg[0] - second_avg[0], first_avg[1] - second_avg[1]

    res = "no gesture found"
    treshold_ver = 10
    treshold_hor = 30

    direction = 'ver' if abs(delta_y) > abs(delta_x) else 'hor'
    if direction == 'ver':
        if delta_y < -treshold_ver:
            res = 'scroll_up'
        elif delta_y > treshold_ver:
            res = 'scroll_down'
    else:
        if delta_x < -treshold_hor:
            res = 'swipe_right'
        elif delta_x > treshold_hor:
            res = 'swipe_left'


    return res

#-------------------------------------------------------------------------------
# Main Function
#-------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True)



