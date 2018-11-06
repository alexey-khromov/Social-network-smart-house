from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
import requests
import os
import cv2
import numpy as np
import boto3
import sys

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

SEQUEL_PHOTOS_TO_KEEP = 4
ITERATIONS_BETWEEN_RECOGNITION = 10  # 5 seconds
PHOTO_NAME_PATTERN = "photo_for_interp_{0}.jpg"

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
liked_page_index = -1
liked_post_index = -1
curr_friend_name = ''
sequel_images_counter = 0
is_first_photo = True
pages_to_show = [] # list of dicts
colId = "SmartSocNet"
sequel_photos_mean = []

#-------------------------------------------------------------------------------
# Flask URLs
#-------------------------------------------------------------------------------

@app.route('/')
def render_static():
    return render_template('show_main.html')

#-------------------------------------------------------------------------------


@app.route("/interpretPhoto", methods=['GET'])
def interpret_photo():
    global sequel_images_counter

    path = request.args.get('image_src')  # image link passed from javascript

    res_dict = {'status': ''}
    prev_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
    sequel_images_counter = (sequel_images_counter % SEQUEL_PHOTOS_TO_KEEP) + 1 # we want 1 and 2
    next_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
    if sys.version_info[0] <= 2:
        import urllib
        urllib.urlretrieve(path, next_photo_name)
    elif sys.version_info[0] <= 3:
        import urllib.request
        urllib.request.urlretrieve(path, next_photo_name)

    res_dict = _interpret_photos(next_photo_name)

    return jsonify(res_dict)

#-------------------------------------------------------------------------------


@app.route("/newUser", methods=['GET'])
def new_user():

    path = request.args.get('image_src')  # image link passed from javascript
    username = request.args.get('user_name')  # new user name from javascript
    res_dict = {'status': ''}
    if sys.version_info[0] <= 2:
        import urllib
        urllib.urlretrieve(path, "photo_for_new_user.jpg")
    elif sys.version_info[0] <= 3:
        import urllib.request
        urllib.request.urlretrieve(path, "photo_for_new_user.jpg")

    try:
        client = boto3.client('rekognition')
        colId = "SmartSocNet"
        #c = client.create_collection(CollectionId=colId)
        with open("photo_for_new_user.jpg", "rb") as imgf:
            img = imgf.read()
        indr = client.index_faces(CollectionId=colId, Image={'Bytes': img}, ExternalImageId=username, MaxFaces=1, )
    except Exception as err:
        print('-------------------------------------------------------------------------------------------------------'
              '-------------------------------------------------------------------------------------------------------')
        print(err.msg)
        print('-------------------------------------------------------------------------------------------------------'
              '-------------------------------------------------------------------------------------------------------')
        raise

    res_dict = _new_person_retrieve_data()

    return jsonify(res_dict)


#-------------------------------------------------------------------------------


@app.route("/clrCol", methods=['GET'])
def clear_collection():
    res_dict = {'status': ''}
    client = boto3.client('rekognition')
    colId = "SmartSocNet"
    client.delete_collection(CollectionId=colId)
    c = client.create_collection(CollectionId=colId)

    res_dict['status'] = 'collection cleared'
    return jsonify(res_dict)


#-------------------------------------------------------------------------------
# Help Functions
#-------------------------------------------------------------------------------

def _new_person_retrieve_data(username):

    global liked_page_index
    global liked_post_index
    global curr_friend_name

    curr_friend_name = username
    liked_page_index = 0
    _create_liked_pages_list()
    next_page_name = pages_to_show[liked_page_index]['name']
    liked_post_index = 0
    _create_liked_posts_list(liked_page_index)
    next_post = pages_to_show[liked_page_index]['posts'][liked_post_index]
    res_dict = {'status': 'new_person',
                'person_name': curr_friend_name,
                'page_name': next_page_name,
                'next_url':next_post}

    return res_dict


#-------------------------------------------------------------------------------

def _try_to_recognize(image_path):

    global curr_friend_name
    global colId

    res_dict = {'status': ''}
    new_friend_name = curr_friend_name
    try:
        client = boto3.client('rekognition')
        with open(image_path, "rb") as imgf:
            img = imgf.read()
        inds = client.search_faces_by_image(CollectionId=colId, Image={'Bytes': img}, MaxFaces=1)

        if (len(inds) > 0) and (inds['FaceMatches'][0]['Similarity'] > 90):
            new_friend_name = inds['FaceMatches'][0]['Face']['ExternalImageId']

    except Exception as err:
        print(err)
        print('Error occurred, please check the token, and verify you are connected.')

    if new_friend_name and (new_friend_name != curr_friend_name):
        res_dict = _new_person_retrieve_data(new_friend_name)

    return res_dict

# -------------------------------------------------------------------------------


def _interpret_photos(last_photo_path):
    global liked_post_index
    global liked_page_index
    global pages_to_show

    res_dict = {'status': ''}
    gesture_result = _get_hand_gesture(last_photo_path)

    if gesture_result == 'new_user_gesture':
        res_dict = _try_to_recognize(last_photo_path)

    elif gesture_result != '':
        if gesture_result == 'scroll_up':
            if 'posts' not in pages_to_show[liked_page_index]:
                _create_liked_posts_list(liked_page_index)
            liked_post_index = (liked_post_index + 1) % len(pages_to_show[liked_page_index]['posts'])
            res_dict['status'] = 'new_post'
        if gesture_result == 'scroll_down':
            if 'posts' not in pages_to_show[liked_page_index]:
                _create_liked_posts_list(liked_page_index)
            liked_post_index = (liked_post_index - 1) % len(pages_to_show[liked_page_index]['posts'])
            res_dict['status'] = 'new_post'
        if gesture_result == 'swipe_left':
            liked_page_index = (liked_page_index + 1) % len(pages_to_show)
            liked_post_index = 0
            res_dict['status'] = 'new_page'
            res_dict['page_name'] = pages_to_show[liked_page_index]['name']
        if gesture_result == 'swipe_right':
            liked_page_index = (liked_page_index - 1) % len(pages_to_show)
            liked_post_index = 0
            res_dict['status'] = 'new_page'
            res_dict['page_name'] = pages_to_show[liked_page_index]['name']

        if len(pages_to_show) > liked_page_index:
            res_dict['gesture'] = gesture_result
            if len(pages_to_show) > 0:
                if 'posts' not in pages_to_show[liked_page_index]:
                    _create_liked_posts_list(liked_page_index)
                res_dict['next_url'] = pages_to_show[liked_page_index]['posts'][liked_post_index]

    return res_dict

#-------------------------------------------------------------------------------


def _create_liked_posts_list(index_to_create_for):
    global pages_to_show

    pages_to_show[index_to_create_for]['posts'] = []
    page_name = pages_to_show[index_to_create_for]['link'].split('/')[-2]

    if page_name != 'facebook':
        new_page_link = pages_to_show[index_to_create_for]['link'].replace(page_name, 'pg/' + page_name + '/posts/?ref=page_internal')
    else:
        link_splitted = pages_to_show[index_to_create_for]['link'].split('facebook')
        link_for_work = 'facebook'.join(link_splitted[:-1])
        link_for_work = link_for_work + 'pg/' + page_name + '/posts/?ref=page_internal'
        link_for_work = link_for_work + link_splitted[-1]
        new_page_link = link_for_work

    if sys.version_info[0] <= 2:
        import urllib
        response = urllib.urlopen(new_page_link)
    elif sys.version_info[0] <= 3:
        import urllib.request
        response = urllib.request.urlopen(new_page_link)

    soup = BeautifulSoup(response.read(), "html.parser")
    posts_objects_list = soup.find_all('span', {'class': 'fsm fwn fcg'})
    for posts_object in posts_objects_list:
        div_like_link = posts_object.find('a')
        link_to_append = 'https://www.facebook.com' + div_like_link['href']
        pages_to_show[index_to_create_for]['posts'].append(link_to_append)

#-------------------------------------------------------------------------------


def _create_liked_pages_list():
    global curr_friend_name
    global pages_to_show

    session = requests.session()
    username = USERNAME
    password = PASSWORD
    cookies = _login(session, username, password)
    likes_url = 'https://www.facebook.com/' + curr_friend_name +'/likes?lst=1198688678%3A843054236%3A1535896155'
    response = session.get(likes_url, cookies=cookies, allow_redirects=False)
    assert response.text.find('Home') != -1

    # For visual see, use: http://codebeautify.org/htmlviewer/
    soup = BeautifulSoup(response.content, "html.parser")
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))    # the liked pages are in comment
    pages_to_show = []
    for comment in comments:
        soup_inner = BeautifulSoup(comment, 'html.parser')
        div_likes_list = soup_inner.findAll('div',{'class':['fsl fwb fcb', 'fsl fwb fcb _5wj-']}) # one for eng. and one for heb.
        for div_like in div_likes_list:
            div_like_link = div_like.find('a')
            liked_page_dict = {'name': div_like_link.text,
                               'link': div_like_link['href']}
            pages_to_show.append(liked_page_dict)

#-------------------------------------------------------------------------------


def _get_hand_gesture(img_name_first):
    global sequel_photos_mean
    global pages_to_show

    try:
        res = ''
        img_last = cv2.imread(img_name_first)
        gray_img_last = cv2.cvtColor(img_last, cv2.COLOR_BGR2GRAY)
        blur_img_last = cv2.GaussianBlur(gray_img_last, (5, 5), 0)

        ret, thresh_img_last = cv2.threshold(blur_img_last, 180, 255, cv2.THRESH_BINARY) #  + cv2.THRESH_OTSU

        #cv2.imshow('image1', thresh_img_last)
        #cv2.waitKey(0)

        # ---Compute the center/mean of the contours---
        points_img_last = cv2.findNonZero(thresh_img_last)
        curr_avg_img_last = np.mean(points_img_last, axis=0)

        sequel_photos_mean.append(curr_avg_img_last.tolist()[0])

        if len(sequel_photos_mean) > SEQUEL_PHOTOS_TO_KEEP:
            sequel_photos_mean.remove(sequel_photos_mean[0])

        if len(sequel_photos_mean) == SEQUEL_PHOTOS_TO_KEEP:
            threshold = 2
            # if special gesture, try to recognize person

            if ((SEQUEL_PHOTOS_TO_KEEP == 4) and
                (sequel_photos_mean[1][1] - sequel_photos_mean[0][1] > threshold) and
                (sequel_photos_mean[2][0] - sequel_photos_mean[1][0] > threshold) and
                (sequel_photos_mean[3][1] - sequel_photos_mean[2][1] < -threshold) and
                (sequel_photos_mean[0][0] - sequel_photos_mean[3][0] < -threshold)):

                res = 'new_user_gesture'
            elif len(pages_to_show) > 0:
                res = _compare_images_for_gesture(sequel_photos_mean)
                if res != '':
                    sequel_photos_mean = []

        #cv2.imshow('image1', thresh_img_first)
        #cv2.waitKey(0)

        return res

    except Exception as err:
        print(err)

#-------------------------------------------------------------------------------


def _compare_images_for_gesture(sequel_photos_mean_list):

    res = ''

    delta_x = 0
    delta_y = 0

    for i in range(2, len(sequel_photos_mean_list)):
        delta_x += sequel_photos_mean_list[i][0] - sequel_photos_mean_list[i-1][0]
        delta_y += sequel_photos_mean_list[i][1] - sequel_photos_mean_list[i-1][1]

        #res_x = sequel_photos_mean_list[i][0] - sequel_photos_mean_list[i-1][0]
        #res_y = sequel_photos_mean_list[i][1] - sequel_photos_mean_list[i-1][1]
        #if abs(res_x) > abs(res_y):
        #    delta_x += sequel_photos_mean_list[i][0] - sequel_photos_mean_list[i-1][0]
        #else:
        #    delta_y += sequel_photos_mean_list[i][1] - sequel_photos_mean_list[i-1][1]

    print(str(delta_x) + ' ' + str(delta_y) + '\n')

    if abs(abs(delta_x) - abs(delta_y)) < 30:
        return res

    threshold_ver = 20
    threshold_hor = 30

    direction = 'ver' if abs(delta_y) > abs(delta_x) else 'hor'
    if direction == 'ver':
        if delta_y < -threshold_ver:
            res = 'scroll_up'
        elif delta_y > threshold_ver:
            res = 'scroll_down'
    else:
        if delta_x < -threshold_hor:
            res = 'swipe_right'
        elif delta_x > threshold_hor:
            res = 'swipe_left'

    return res

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
# Main Function
#-------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True)



