from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder='C:/Alexey Technion/ProjectB_Smart_Home/Smart_Home_Project/')
sources = ['http://www.walla.co.il', 'http://www.ynet.co.il', 'http://www.mako.co.il']
i = 0

@app.route('/') # <string:page_name>/
def render_static():
    #return render_template('%s.html' % page_name)
    #webcode = open('show_main.html').read()
    return render_template('show_main.html', my_iframe='http://www.walla.co.il')

@app.route("/getNextFrame", methods=['GET'])
def getData():
    global i
    next_source_frame = sources[i];
    i = (i + 1) % 3;

    return jsonify({'next_url': next_source_frame})


if __name__ == '__main__':
    app.run(debug=True)