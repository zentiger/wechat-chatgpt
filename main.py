from flask import Flask
from wechat.wechat import wechat
from feishu.feishu import feishu 

app = Flask(__name__)

app.register_blueprint(wechat, url_prefix='/wechat')
app.register_blueprint(feishu, url_prefix='/feishu')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)