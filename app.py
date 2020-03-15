import os
import sys
from flask import Flask, send_from_directory, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import pymongo
import time

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["medicalappointment"]
app = Flask(__name__)

def add_time(xtime, shr, smin):
    smin+=xtime
    if smin>60:
        shr+=1
        smin-=60
    return str(shr)+":"+str(smin)

def cmp_time(hr, minn, ehr, emin):
    if hr<ehr:
        return True
    elif hr==ehr and minn<=emin:
        return True
    else:
        return False

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mycol = mydb["users"]
        username = request.form.get("username")
        password = request.form.get("password")
        for x in mycol.find():
            if x["username"]==username: 
                if x["password"]==password: return redirect(url_for('home', username=x['username'], typeof=x['typeof']))
                else: return render_template('login.html', message="Wrong Id or Password")
        return render_template('login.html', message="Wrong Id or Password")
    return render_template('login.html', message="")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        mycol = mydb["users"]
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        typeof = request.form['type']
        print("YOLO")
        data = {"username":username, "password":password, "name":name, "typeof": typeof}
        x=mycol.insert_one(data)
        return render_template('register.html', message="Registered")
    return render_template('register.html', message="")

@app.route("/home/<string:username>/<string:typeof>", methods=['GET', 'POST'])
def home(username, typeof):
    if typeof == "doctor":
        return redirect(url_for('dhome', username=username, typeof=typeof))
    else:
        return redirect(url_for('phome', username=username, typeof=typeof))

@app.route("/dhome/<string:username>/<string:typeof>", methods=['GET', 'POST'])
def dhome(username, typeof):
    if request.method == "POST":
        mycol = mydb["avappoint"]
        fromm = request.form.get('from')
        to = request.form.get('to')
        date = request.form.get('date')
            data = {'username': username, 'date':date, 'from':fromm, 'to':to, myappointments:{}, total:0}
        x=mycol.insert_one(data)
        return render_template('dhome.html')
    return render_template('dhome.html')

@app.route("/phome/<string:username>/<string:typeof>", methods=['GET', 'POST'])
def phome(username, typeof):
    mycol = mydb["users"]
    doctors=[]
    for x in mycol.find():
        if x['typeof']=="doctor":
            doctors.append((x['name'], x['username']))
    return render_template('phome.html', doctors=doctors, patient=username)

@app.route("/appointment/<string:username>/<string:patient>", methods=['GET', 'POST'])
def appointment(username, patient):
    mycol = mydb['avappoint']
    dates=[]
    for x in mycol.find():
        if x['username'] == username:
            dates.append(x['date'])
    if request.method == "POST":
        date = request.form.get('dates')
        symptom = request.form.get('symptoms')
        myap = {}
        for x in mycol.find():
            if x['username'] == username and x['date'] == date:
                data = x
                total = int(x['total'])
                fromm = x['from']
                to = x['to']
                break
        ehr=int(to[0:2])
        emin=int(to[3:5])
        if total==0:
            shr=int(fromm[0:2])
            smin=int(fromm[3:5])
            time=add_time(15, shr, smin)
            total+=1
            newdata = data
            newdata["total"] = total
            newdata[str(total)] = {}
            return render_template('appointments.html', dates=dates, message="Appointment booked for " + fromm )
    return render_template('appointments.html', dates=dates, message="")

app.run(threaded=True)