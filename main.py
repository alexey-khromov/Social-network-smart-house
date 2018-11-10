from flask import Flask, jsonify, render_template, request
from bs4 import BeautifulSoup, Comment
import requests
import os
import cv2
import numpy as np
import boto3
import sys
import copy

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

SEQUEL_PHOTOS_TO_KEEP = 1
PHOTO_NAME_PATTERN = "photo_for_interp_{0}.jpg"
PHOTO_ENVIRONMENT = "photo_environment.jpg"
PHOTO_USER_ADDED = "photo_for_new_user.jpg"
PHOTO_USER_ARRIVED = "photo_user_arrived.jpg"
SEQUEL_PHOTOS_TO_RECOGNIZE_USER = 4
HAND_MATRIX_ORIGINAL_RIGHT = [False, False, False]
HAND_MATRIX_ORIGINAL_TOP = [False, False, False]
VERTICAL_SCROLL_THRESHOLD = 40
HORIZONTAL_SCROLL_THRESHOLD = 30

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
pages_to_show = [] # list of dicts
colId = "SmartSocNet"
sequel_photos_with_new_user_gesture = 0
previous_hands_matrix_right = copy.deepcopy(HAND_MATRIX_ORIGINAL_RIGHT)
previous_hands_matrix_top = copy.deepcopy(HAND_MATRIX_ORIGINAL_TOP)


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
    if sys.version_info[0] <= 2:
        import urllib
        urllib.urlretrieve(path)
    elif sys.version_info[0] <= 3:
        import urllib.request
        urllib.request.urlretrieve(path)

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

@app.route("/newEnvironment", methods=['GET'])
def new_environment():

    path = request.args.get('image_src')  # image link passed from javascript
    if sys.version_info[0] <= 2:
        import urllib
        urllib.urlretrieve(path, PHOTO_ENVIRONMENT)
    elif sys.version_info[0] <= 3:
        import urllib.request
        urllib.request.urlretrieve(path, PHOTO_ENVIRONMENT)

    res_dict = {'status': 'new_env_saved'}
    return jsonify(res_dict)



#-------------------------------------------------------------------------------

@app.route("/newUserArrived", methods=['GET'])
def new_user_arrived():
    global sequel_photos_with_new_user_gesture

    photo_path = request.args.get('photo_path')
    res_dict = _try_to_recognize(photo_path)
    sequel_photos_with_new_user_gesture = 0
    return jsonify(res_dict)


#-------------------------------------------------------------------------------

@app.route("/getCurrPostUrl", methods=['GET'])
def get_curr_post_url():
    global liked_page_index
    global liked_post_index
    global pages_to_show  # list of dicts

    res_dict = {'status': ''}
    gesture_result = request.args.get('gesture_result')
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
                'next_url': next_post}

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

    if new_friend_name:
        res_dict = _new_person_retrieve_data(new_friend_name)

    return res_dict

# -------------------------------------------------------------------------------


def _interpret_photos(last_photo_path):
    global liked_post_index
    global liked_page_index
    global pages_to_show
    global sequel_photos_with_new_user_gesture
    global previous_hands_matrix_right
    global previous_hands_matrix_top

    res_dict = {'status': ''}

    if _is_new_user_gesture(last_photo_path):
        sequel_photos_with_new_user_gesture += 1
        if sequel_photos_with_new_user_gesture >= SEQUEL_PHOTOS_TO_RECOGNIZE_USER:
            sequel_photos_with_new_user_gesture = 0
            image = cv2.imread(last_photo_path)
            cv2.imwrite(PHOTO_USER_ARRIVED, image)

            res_dict = {'status': 'new_user_gesture',
                        'photo_path': PHOTO_USER_ARRIVED}
            return res_dict
    else:
        sequel_photos_with_new_user_gesture = 0

    if curr_friend_name == '':
        return res_dict

    gesture_result = _get_hand_gesture(last_photo_path)
    if gesture_result != '':
        previous_hands_matrix_right = copy.deepcopy(HAND_MATRIX_ORIGINAL_RIGHT)
        previous_hands_matrix_top = copy.deepcopy(HAND_MATRIX_ORIGINAL_TOP)
        res_dict['status'] = 'new_post_or_page'
        res_dict['gesture'] = gesture_result

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


def _is_new_user_gesture(img_name_new):
    '''
    In this function we will be looking for the blue rectangle
    :param img_name_new:
    :return:
    '''
    '''
    :param img_name_new: 
    :return: 
    '''
    img_last = cv2.imread(img_name_new)
    img_env = cv2.imread(PHOTO_ENVIRONMENT)

    diff = cv2.absdiff(img_last, img_env)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    ret, thresh_gray_diff_img = cv2.threshold(gray_diff, 10, 255, cv2.THRESH_BINARY)  # + cv2.THRESH_OTSU
    blur_img_last = cv2.blur(thresh_gray_diff_img, (15, 15))
    ret, thresh_img_last = cv2.threshold(blur_img_last, 230, 255, cv2.THRESH_BINARY)  # + cv2.THRESH_OTSU

    '''
    cv2.imshow('image1', gray_diff)
    cv2.imshow('image2', thresh_img_last)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    '''

    y, x = thresh_img_last.shape
    cropx = 120
    cropy = 120
    startx = 480  # x // 2 - (cropx // 2)
    starty = 100  # y // 2 - (cropy // 2)
    cropped_img = thresh_img_last[starty:starty + cropy, startx:startx + cropx]

    '''
    cv2.imshow('image3', cropped_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    '''

    ci = -1
    max_area = 0
    img2, contours, hierarchy = cv2.findContours(cropped_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for i in range(len(contours)):
        cnt = contours[i]
        area = cv2.contourArea(cnt)
        if area > max_area:
            max_area = area
            ci = i

    if ci != -1:
        cnt = contours[ci]

        '''
        hull = cv2.convexHull(cnt)
        drawing = np.zeros(img_last.shape, np.uint8)
        cv2.drawContours(drawing, [cnt], 0, (255, 0, 0), 2)
        cv2.drawContours(drawing, [hull], 0, (255, 0, 255), 2)
        cv2.imshow('image1', cropped_img)
        cv2.imshow('image2', drawing)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        '''

        hull = cv2.convexHull(cnt, returnPoints=False)
        defects = cv2.convexityDefects(cnt, hull)

        if (defects is not None) and (len(defects) >= 6):
            return True

    return False

    '''
    moments = cv2.moments(cnt)
    if moments['m00'] != 0:
        cx = int(moments['m10'] / moments['m00'])  # cx = M10/M00
        cy = int(moments['m01'] / moments['m00'])  # cy = M01/M00

    centr = (cx, cy)
    i = 0
    for i in range(defects.shape[0]):
        s, e, f, d = defects[i, 0]
        start = tuple(cnt[s][0])
        end = tuple(cnt[e][0])
        far = tuple(cnt[f][0])
        cv2.line(drawing, start, end, [0, 255, 0], 2)
        cv2.circle(drawing, far, 5, [0, 0, 255], -1)
    '''


#-------------------------------------------------------------------------------

def _fill_hand_matrices(image):
    global new_hand_matrix_right
    global new_hand_matrix_top

    height, width = image.shape

    new_hand_matrix_right = copy.deepcopy(HAND_MATRIX_ORIGINAL_RIGHT)
    new_hand_matrix_top = copy.deepcopy(HAND_MATRIX_ORIGINAL_TOP)

    rows_num = len(HAND_MATRIX_ORIGINAL_RIGHT)
    cols_num = len(HAND_MATRIX_ORIGINAL_TOP)
    x_slice_size = width // cols_num
    y_slice_size = height // rows_num

    def _aux_fun(image, startx, starty, x_slice_size, y_slice_size):
        cropped_img = image[starty:starty + y_slice_size, startx:startx + x_slice_size]
        n_white_pix = np.sum(cropped_img == 255)
        n_black_pix = np.sum(cropped_img == 0)
        return n_white_pix, n_black_pix

    for row in range(0, rows_num):
        startx = 10
        starty = row * y_slice_size
        n_white_pix, n_black_pix = _aux_fun(image, startx, starty, 100, y_slice_size)
        new_hand_matrix_right[row] = n_white_pix > (n_black_pix // VERTICAL_SCROLL_THRESHOLD)

    for col in range(0, cols_num):
        startx = col * x_slice_size
        starty = 10
        n_white_pix, n_black_pix = _aux_fun(image, startx, starty, x_slice_size, 100)
        new_hand_matrix_top[col] = n_white_pix > (n_black_pix // HORIZONTAL_SCROLL_THRESHOLD)

    return new_hand_matrix_right, new_hand_matrix_top

    '''
    cv2.imshow('image4', cropped_img)
    cv2.imshow('image5', drawing)

    cv2.waitKey(0)
    cv2.destroyAllWindows()
    '''

#-------------------------------------------------------------------------------


def _get_hand_gesture(img_name_new):
    global pages_to_show
    global previous_hands_matrix_right
    global previous_hands_matrix_top
    global curr_friend_name

    try:
        res = ''
        img_last = cv2.imread(img_name_new)
        img_env = cv2.imread(PHOTO_USER_ARRIVED)

        diff = cv2.absdiff(img_last, img_env)
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        ret, thresh_gray_diff_img = cv2.threshold(gray_diff, 10, 255, cv2.THRESH_BINARY) #  + cv2.THRESH_OTSU
        blur_img_last = cv2.blur(thresh_gray_diff_img, (15, 15))
        ret, thresh_img_last = cv2.threshold(blur_img_last, 230, 255, cv2.THRESH_BINARY) #  + cv2.THRESH_OTSU

        '''
        cv2.imshow('image1', thresh_gray_diff_img)
        cv2.imshow('image2', blur_img_last)
        cv2.imshow('image3', thresh_img_last)

        cv2.waitKey(0)
        cv2.destroyAllWindows()
        '''

        new_hand_matrix_right, new_hand_matrix_top = _fill_hand_matrices(thresh_img_last)
        res = _compare_images_for_gesture(previous_hands_matrix_right, new_hand_matrix_right, previous_hands_matrix_top, new_hand_matrix_top)
        previous_hands_matrix_right = copy.deepcopy(new_hand_matrix_right)
        previous_hands_matrix_top = copy.deepcopy(new_hand_matrix_top)

        return res

        '''
        cv2.imshow('image1', thresh_gray_diff_img)
        cv2.imshow('image2', blur_img_last)
        cv2.imshow('image3', thresh_img_last)

       # cv2.waitKey(0)
       # cv2.destroyAllWindows()

        if (True): # 5 fingers
                res = 'new_user_gesture'
        elif len(pages_to_show) > 0:
            res = _compare_images_for_gesture(sequel_photos_mean)
            if res != '':
                sequel_photos_mean = []
        '''
        '''
        cv2.imshow('image1', cropped_img)
        cv2.imshow('image2', drawing)

        cv2.waitKey(0)
        cv2.destroyAllWindows()
        '''

    except Exception as err:
        print(err)

#-------------------------------------------------------------------------------


def _compare_images_for_gesture(previous_hands_matrix_right, new_hand_matrix_right, previous_hands_matrix_top, new_hand_matrix_top):
    res = ''
    columns_num = len(previous_hands_matrix_top)
    rows_num = len(previous_hands_matrix_right)
    print(str(previous_hands_matrix_right) + " " + str(new_hand_matrix_right) + "\n" + str(previous_hands_matrix_top) + " " + str(new_hand_matrix_top))

    try:
        # swipe right
        if ((previous_hands_matrix_top[0]) and  # and not new_hand_matrix_top[0]
                (not previous_hands_matrix_top[columns_num - 1] and new_hand_matrix_top[columns_num - 1])):
            res = 'swipe_right'

        # swipe left
        elif ((not previous_hands_matrix_top[0] and new_hand_matrix_top[0]) and
              (previous_hands_matrix_top[columns_num - 1])):    # and not new_hand_matrix_top[columns_num - 1]
            res = 'swipe_left'

        # scroll down
        elif ((previous_hands_matrix_right[0]) and  #  and not new_hand_matrix_right[0]
              (not previous_hands_matrix_right[rows_num-1] and new_hand_matrix_right[rows_num-1])):
            res = 'scroll_down'

        # scroll up
        elif ((previous_hands_matrix_right[rows_num-1]) and # and not new_hand_matrix_right[rows_num-1]
              (not previous_hands_matrix_right[0] and new_hand_matrix_right[0])):
            res = 'scroll_up'
    except Exception as err:
        print(err)

    print(res)
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



