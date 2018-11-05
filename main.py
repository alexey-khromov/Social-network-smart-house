from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
import requests
import os
import cv2
import numpy as np
import boto3
import urllib
#from urllib2 import urlopen

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

SEQUEL_PHOTOS_TO_KEEP = 2
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
curr_iteration = -1
curr_friend_name = ''
sequel_images_counter = 0
is_first_photo = True
pages_to_show = [] # list of dicts
colId = "SmartSocNet"

#-------------------------------------------------------------------------------
# Flask URLs
#-------------------------------------------------------------------------------

@app.route('/')
def render_static():
    return render_template('show_main.html')

#-------------------------------------------------------------------------------


@app.route("/interpretPhoto", methods=['GET'])
def interpret_photo():
    global curr_iteration
    global sequel_images_counter
    global is_first_photo
    global liked_page_index
    global liked_post_index
    global curr_friend_name

    path = request.args.get('image_src')  # image link passed from javascript

    res_dict = {'status': ''}
    curr_iteration = (curr_iteration + 1) % ITERATIONS_BETWEEN_RECOGNITION
    if curr_iteration == 0:
        urllib.urlretrieve(path, "photo_for_recognition.jpg")
        new_friend_name = _get_person_name()
        if new_friend_name and (new_friend_name != curr_friend_name):
            curr_friend_name = new_friend_name
            liked_page_index = 0
            _create_liked_pages_list()
            next_page_name = pages_to_show[liked_page_index]['name']
            liked_post_index = 0
            next_post = pages_to_show[liked_page_index]['posts'][liked_post_index]
            res_dict['status'] = 'new_person'
            res_dict['person_name'] = curr_friend_name
            res_dict['page_name'] = next_page_name
            res_dict['next_url'] = next_post
    else:
        prev_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
        sequel_images_counter = (sequel_images_counter % SEQUEL_PHOTOS_TO_KEEP) + 1 # we want 1 and 2
        next_photo_name = PHOTO_NAME_PATTERN.format(sequel_images_counter)
        urllib.urlretrieve(path, next_photo_name)

        if not is_first_photo:
            res_dict = _interpret_hand_gesture(prev_photo_name, next_photo_name)
        else:
            is_first_photo = False

    return jsonify(res_dict)

#-------------------------------------------------------------------------------


@app.route("/newUser", methods=['GET'])
def new_user():
    global liked_page_index
    global liked_post_index
    global curr_friend_name

    path = request.args.get('image_src')  # image link passed from javascript
    username = request.args.get('user_name')  # new user name from javascript
    res_dict = {'status': ''}
    urllib.urlretrieve(path, "photo_for_new_user.jpg")

    client = boto3.client('rekognition')
    colId = "SmartSocNet"
    #c = client.create_collection(CollectionId=colId)
    with open("photo_for_new_user.jpg", "rb") as imgf:
        img = imgf.read()
    indr = client.index_faces(CollectionId=colId, Image={'Bytes': img}, ExternalImageId=username, MaxFaces=1, )

    curr_friend_name = username
    liked_page_index = 0
    _create_liked_pages_list()
    next_page_name = pages_to_show[liked_page_index]['name']
    liked_post_index = 0
    next_post = pages_to_show[liked_page_index]['posts'][liked_post_index]
    res_dict['status'] = 'new_person'
    res_dict['person_name'] = curr_friend_name
    res_dict['page_name'] = next_page_name
    res_dict['next_url'] = next_post

    return jsonify(res_dict)

#-------------------------------------------------------------------------------
# Help Functions
#-------------------------------------------------------------------------------


def _get_person_name():
    global curr_friend_name
    global colId

    #access_token = 'EAAYeBD26ZAQkBABrAJhhuBzZAGBXzgZBu0vwKJYphmMieKkt4MDUGtn428daGpP7rGJOQNAey7lf9qOjX1OWhkEAc8VcW4pQPrJVshySSEDze0qJIKiBLJb177HT1ejJQ1cZC7c2hZC60EyO2yLNXh1fvyFQwqEz0puzt2r3UnZBk3ZCWc9FM3czDyt4I4o9MH8ZC0wiYhVZBVwZDZD'
    #cookies = 'sb=9kLwWktAnKZOmrlxUuJlGvKk; datr=9kLwWo5FFaoj5mK76Z1-vShO; locale=en_US; c_user=1198688678; xs=35%3AlyCvKlPdxEjPyg%3A2%3A1538383858%3A3484%3A15165; pl=n; spin=r.4393324_b.trunk_t.1538905122_s.1_v.2_; fr=0wfDpjdR3vG29Yo3f.AWUPGfa3vQZ80Dw_B3o1kU5p0ts.Ba8EL2.K_.Fux.0.0.BbudUS.AWVcNdsJ; dpr=1.75; presence=EDvF3EtimeF1538908587EuserFA21198688678A2EstateFDutF1538908587789CEchFDp_5f1198688678F2CC; act=1538908590107%2F0; wd=884x742'
    #fb_dtsg = 'AQG4zg_XZ4s4:AQE3N127AIwY'

    friend_name = curr_friend_name
    try:
        #fb_recog_obj = FBRecog(access_token, cookies, fb_dtsg)
        #picture_for_recog_path = os.getcwd() + '\photo_for_recognition.jpg'
        #recognized_friends_list = fb_recog_obj.recognize(picture_for_recog_path)
        #recognized_friends_list = [{'name': 'James Bond'}]

        client = boto3.client('rekognition')
        with open("photo_for_recognition.jpg", "rb") as imgf:
            img = imgf.read()
        inds = client.search_faces_by_image(CollectionId=colId, Image={'Bytes': img}, MaxFaces=1)

        if (len(inds) > 0) and (inds['FaceMatches'][0]['Similarity'] > 90):
            friend_name = inds['FaceMatches'][0]['Face']['ExternalImageId']

    except Exception as err:
        print(err)
        print('Error occurred, please check the token, and verify you are connected.')

    return friend_name

# -------------------------------------------------------------------------------


def _interpret_hand_gesture(prev_photo_name, next_photo_name):
    global liked_post_index
    global liked_page_index

    res_dict = {'status': ''}
    gesture_result = _get_hand_gesture(prev_photo_name, next_photo_name)
    if gesture_result != '':
        if gesture_result == 'scroll_up':
            liked_post_index = (liked_post_index + 1) % len(pages_to_show[liked_page_index]['posts'])
            res_dict['status'] = 'new_post'
        if gesture_result == 'scroll_down':
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

        if len(pages_to_show)>liked_page_index:
            res_dict['gesture'] = gesture_result
            res_dict['next_url'] = pages_to_show[liked_page_index]['posts'][liked_post_index]

    return res_dict

#-------------------------------------------------------------------------------


def _create_liked_posts_list(index_to_create_for, max_posts_num=2):
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

    response = urllib.urlopen(new_page_link)
    soup = BeautifulSoup(response.read(), "html.parser")
    posts_objects_list = soup.find_all('span', {'class': 'fsm fwn fcg'})
    for posts_object in posts_objects_list:
        div_like_link = posts_object.find('a')
        link_to_append = 'https://www.facebook.com' + div_like_link['href']
        pages_to_show[index_to_create_for]['posts'].append(link_to_append)
        if len(pages_to_show[index_to_create_for]['posts']) >= max_posts_num:
            break

#-------------------------------------------------------------------------------


def _create_liked_pages_list(max_pages_num=2):
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
            liked_page_dict = {}
            liked_page_dict['name'] = div_like_link.text
            liked_page_dict['link'] = div_like_link['href']
            pages_to_show.append(liked_page_dict)
            if len(pages_to_show) >= max_pages_num:
                break
        if len(pages_to_show) >= max_pages_num:
            break

    for i, page in enumerate(pages_to_show):
        _create_liked_posts_list(i)

#-------------------------------------------------------------------------------


def _get_hand_gesture(img_name_first, img_name_second):
    try:
        img_first = cv2.imread(img_name_first)
        img_second = cv2.imread(img_name_second)

        gray_img_first = cv2.cvtColor(img_first, cv2.COLOR_BGR2GRAY)
        gray_img_second = cv2.cvtColor(img_second, cv2.COLOR_BGR2GRAY)

        blur_img_first = cv2.GaussianBlur(gray_img_first, (5, 5), 0)
        blur_img_second = cv2.GaussianBlur(gray_img_second, (5, 5), 0)


        ret, thresh_img_first = cv2.threshold(blur_img_first, 100, 255, cv2.THRESH_BINARY) #  + cv2.THRESH_OTSU
        ret, thresh_img_second = cv2.threshold(blur_img_second, 100, 255, cv2.THRESH_BINARY) # + cv2.THRESH_OTSU


        # ---Compute the center/mean of the contours---
        points_first = cv2.findNonZero(thresh_img_first)
        curr_avg_first = np.mean(points_first, axis=0)

        points_second = cv2.findNonZero(thresh_img_second)
        curr_avg_second = np.mean(points_second, axis=0)


        prev_pos = curr_avg_first.tolist()[0]
        cur_pos = curr_avg_second.tolist()[0]

        #cv2.imshow('image1', thresh_img_first)
        #cv2.imshow('image2', thresh_img_second)
        #cv2.waitKey(0)

        return _compare_images_for_gesture(prev_pos, cur_pos)

    except Exception as err:
        print(err)

#-------------------------------------------------------------------------------


def _compare_images_for_gesture(first_avg, second_avg):

    delta_x, delta_y = first_avg[0] - second_avg[0], first_avg[1] - second_avg[1]

    res = ''
    threshold_ver = 10
    threshold_hor = 25

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
    '''
    client = boto3.client('rekognition')
    colId = "SmartSocNet"
    client.delete_collection(CollectionId=colId)
    c = client.create_collection(CollectionId=colId)
    exit(0)
    '''

    app.run(debug=True)



