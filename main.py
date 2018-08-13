from pprint import pprint
from fbrecog import FBRecog
from bs4 import BeautifulSoup
from urllib.request import urlopen

path = 'C:\Alexey Technion\ProjectB_Smart_Home\mypic.jpg'
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


temp = urlopen('https://www.facebook.com/alexey.e.khromov')
page = temp.read()
soup = BeautifulSoup(page)
print(soup)
