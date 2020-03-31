import os
import sys
from werkzeug.utils import secure_filename
from flask import Flask, send_from_directory, render_template, request, redirect, url_for
import pymongo
import time
import datetime
from joblib import load

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["medicalappointment"]
app = Flask(__name__)
svm = load('appointmentmanagement.joblib') 

def add_time(xtime, shr, smin):
    smin+=xtime
    if smin>60:
        shr+=1
        smin-=60
    return str(shr).zfill(2)+":"+str(smin)

def cmp_time(hr, minn, ehr, emin):
    if hr<ehr:
        return True
    elif hr==ehr and minn<=emin:
        return True
    else:
        return False

def getDate():
    x = datetime.datetime.now()
    return (x.year, x.month, x.day)

def checkDate(appdate, date):
    year=int(appdate[:4])
    month=int(appdate[5:7])
    day=int(appdate[8:])
    if year>date[0]:
        return True
    elif year==date[0] and month>date[1]:
        return True
    elif year==date[0] and month==date[1] and day>=date[2]:
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
        return redirect(url_for('dhome', username=username))
    else:
        return redirect(url_for('phome', username=username))

@app.route("/dhome/<string:username>", methods=['GET', 'POST'])
def dhome(username):
    mycoltwo = mydb["booked"]
    appointments=[]
    date=getDate()
    for x in mycoltwo.find():
        cdate=x["date"]
        if x["dusername"]==username and checkDate(cdate, date):
            appointments.append((x["pusername"], x["from"], x["to"], x["date"]))
    if request.method == "POST":
        mycol = mydb["avappoint"]
        fromm = request.form.get('from')
        to = request.form.get('to')
        date = request.form.get('date')
        data = {'username': username, 'date':date, 'from':fromm, 'to':to, "total":0, "ltime":fromm}
        x=mycol.insert_one(data)
        return render_template('dhome.html', appointment=appointments)
    return render_template('dhome.html', appointment=appointments)

@app.route("/phome/<string:username>", methods=['GET', 'POST'])
def phome(username):
    mycol = mydb["users"]
    mycoltwo = mydb["booked"]
    doctors=[]
    appointments=[]
    date=getDate()
    for x in mycol.find():
        if x['typeof']=="doctor":
            doctors.append((x['name'], x['username']))
    for x in mycoltwo.find():
        cdate=x["date"]
        if x["pusername"]==username and checkDate(cdate, date):
            appointments.append((x["dusername"], x["from"], x["date"], x["pusername"]))
    if len(appointments)==0:
        return render_template('phome.html', doctors=doctors, patient=username, appointment="No Appointments available")
    return render_template('phome.html', doctors=doctors, patient=username, appointment=appointments)

@app.route("/appointment/<string:username>/<string:patient>", methods=['GET', 'POST'])
def appointment(username, patient):
    mycol = mydb['avappoint']
    dates=[]
    #get all available appointments
    for x in mycol.find():
        if x['username'] == username:
            dates.append(x['date'])
    #for booking appointments        
    if request.method == "POST":
        date = request.form.get('dates')
        symptom = int(request.form.get('symptoms'))
        book = mydb["booked"]
        #find the availability details
        for x in mycol.find():
            if x['username'] == username and x['date'] == date:
                data = x
                break
        loong = svm.predict([[symptom]])
        fromm = data['ltime']
        to = data['to']
        ehr=int(to[0:2])
        emin=int(to[3:])
        shr=int(fromm[0:2])
        smin=int(fromm[3:])
        print(loong[0])
        time=add_time(loong[0], shr, smin)
        if cmp_time(int(time[0:2]), int(time[3:]), ehr, emin): 
            bookdata = { "dusername":username,"pusername": patient, "from":fromm, "to":time, "date":date}
            book.insert_one(bookdata)
            myquery = {"date" : date, "username": username}
            newvalues = {"$set" : {"ltime" : time}}
            mycol.update_one(myquery, newvalues)
            return render_template('appointments.html', dates=dates, message="Appointment booked for " + fromm )
        else:
            return render_template('appointments.html', dates=dates, message="Appointment not available")
    return render_template('appointments.html', dates=dates, message="")

@app.route("/deleteappointment/<string:pusername>/<string:dusername>/<string:date>/<string:fromm>")
def deleteappointment(pusername, dusername, date, fromm):
    to=""
    pto=""
    mycol = mydb['booked']
    for x in mycol.find():
        if x["dusername"]==dusername and x["date"]==date and x["from"]==fromm:
            pto = x["to"]
            to = x["to"]
            myquery = {"dusername":dusername, "pusername":pusername, "from":fromm, "date": date}
            mycol.delete_one(myquery)
            break
    for x in mycol.find():
        if x["dusername"]==dusername and x["date"]==date and x["from"]==pto:
            print(fromm, to)
            myquery = {"_id": x["_id"]}
            newvalues = {"$set": {"from":fromm, "to":to}}
            mycol.update_one(myquery, newvalues)
            fromm = to
            to = x["to"]
            pto = x["to"]
    newcol = mydb["avappoint"]
    myquery = {"date" : date, "username": dusername}
    newvalues = {"$set" : {"ltime" : fromm}}
    newcol.update_one(myquery, newvalues)
    return redirect(url_for("phome", username=pusername))

@app.route("/logout", methods=["GET", "POST"])
def logout():
    return redirect(url_for('login'))

app.run(threaded=True)