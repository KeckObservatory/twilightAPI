from flask import Flask, render_template, request, redirect, url_for, session
from twilightobs import twilightobs_select,twilightobs_insert
import re 

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# @app.route('/twilightcmd/',methods=['POST','GET'])
# def twilightcmd():
# 	return str(twilight_cmd())

#establish MySQL select route
@app.route('/twilight_select/',methods=['POST','GET'])
def twilight_select():
	return str(twilightobs_select())

#establish MySQL insert route
@app.route('/twilight_insert/',methods=['POST','GET'])
def twilight_insert():
	return str(twilightobs_insert())

#run on port 50001
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 50011
    debug = False
    app.run(host=host,port=port,debug=debug)
