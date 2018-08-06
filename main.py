from pprint import pprint
from fbrecog import FBRecog

path = 'C:\Alexey Technion\ProjectB_Smart_Home\mypic.jpg'
access_token = 'EAAYeBD26ZAQkBACBd5bAXO5I7QFCt3CnBSTCuYPx91Ldd8jphWOml2sfMEIx0yuDyRWcSgunqy3RCiUvUx0xFZAl0yMQMTgXDwkZCrepDn7y8nplndrgQ48ZC8cdqmAgzXNzES5zZCjA3aYiRP2qD55JV0WOXIv6fpz1Tz7EC7ZAZCo8UzmjU9HLNbtxLzUF4yYAVcNhtVLbuuXwt0UCCI9zURowEXmqrKJJZBLQrnm4XQZDZD'
cookies ='sb=9kLwWktAnKZOmrlxUuJlGvKk; datr=9kLwWo5FFaoj5mK76Z1-vShO; ; dpr=1.75; locale=en_US; js_ver=3138; pl=n; spin=r.4177188_b.trunk_t.1533505341_s.1_v.2_; act=1533505364795%2F4; c_user=100027703129886; xs=31%3ALgNoqfXtv89nXw%3A2%3A1533505369%3A-1%3A-1; fr=0wfDpjdR3vG29Yo3f.AWUwoZSmpKH1-RB9NvU2bO2SY9k.Ba8EL2.K_.AAA.0.0.BbZ29Y.AWWyAomF; presence=EDvF3EtimeF1533505367EuserFA21B27703129886A2EstateFDutF1533505367743CEchFDp_5f1B27703129886F2CC; wd=1034x747'
fb_dtsg = 'AQECP_wJf79L:AQE_gm8kQnRB'

# Instantiate the recog class
recog = FBRecog(access_token, cookies, fb_dtsg)
# Recog class can be used multiple times with different paths
print(recog.recognize(path))
