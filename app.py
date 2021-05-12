# -*- coding: utf-8 -*-
"""
Created on Tue Apr 27 14:55:39 2021

@author: SathishKantamsetti
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, make_response
from flask_httpauth import HTTPBasicAuth
from flask_mysqldb import MySQL
from sendemail import sendmail
from datetime import date
import MySQLdb.cursors
import re
import hashlib
import smtplib
import secrets
import string

app=Flask( __name__ )
app.config['JSON_SORT_KEYS'] = False
app.secret_key='Fox'
app.config['MYSQL_HOST'] ='remotemysql.com'    #'localhost'
app.config['MYSQL_USER'] = 'WnJoztH6xP'             #'root'
app.config['MYSQL_PASSWORD'] ='Dp6jBCRncC'          #''
app.config['MYSQL_DB'] = 'WnJoztH6xP'               #'getAjobdb'
mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/profile',methods=["POST","GET"])
def profile():
    if not session['loggedin']:
        msg='Please login to proceed!'
        return render_template('login.html',msg=msg)
    else :
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM user WHERE usermail = % s', (session['usermail'], ))
        except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
            msg = 'A problem on our side, please try after sometime!'
            return render_template('main.html',msg=msg)
        account = cursor.fetchone()
        msg=account
        edu=account[6].split('!')
        cursor.execute("SELECT DISTINCT(jobid),appliedon,status FROM appliedjobs WHERE userid=%s ORDER BY appliedon LIMIT 3",(session['usermail'],))
        jobs=[]
        jobcount=cursor.rowcount
        for i in range(cursor.rowcount):
            job=cursor.fetchone()
            jobs.append(job)
        appliedjobs=[]
        appliedjobs.append(jobcount)
        for i in range(jobcount):
            job=list(jobs[i])
            cursor.execute("SELECT position,Organization,location FROM availjobs WHERE jobid=% s LIMIT 3",((job[0]),))
            jobapplied=cursor.fetchone()
            appliedjob={"Organisation":jobapplied[1],"Position":jobapplied[0],"Status":jobs[i][2]}
            appliedjobs.append(appliedjob)
        return render_template('profile.html',msg=msg,edu=edu,appliedjobs=appliedjobs)

@app.route('/loginpage')
def loginpage():
    return render_template('login.html')

@app.route('/apipage')
def apipage():
    email=session['usermail']
    try :
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT passhash FROM login WHERE email = %s",(email,))
    except MySQLdb._exceptions.OperationalError :
        msg="We are facing some issues, please try after sometime!"
        return render_template('main.html')
    if cursor.rowcount:
        passhash=cursor.fetchone()
        return render_template('apiDocumentation.html',apitoken=passhash)
@app.route('/tc')
def tc():
    return render_template('TermsConditions.html')
@app.route('/dashboard')
def dashboard():
    if session['loggedin']:
        joboffers=[]
        cursor = mysql.connection.cursor()
        usermail=session['usermail']
        cursor.execute("SELECT username,skillset,city FROM user WHERE usermail= % s",(session['usermail'],))
        user=cursor.fetchone()
        city=user[2].split(',') #session['usercity']
        session['username']=user[0]
        skills=user[1].split(',')  #=session['userskills']
        #print(skills)
        cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s AND status='open'",("%" + skills[0] + "%","%" + skills[0] + "%","%" + city[0] + "%",))
        joboffers.append(cursor.rowcount)
        for i in range(cursor.rowcount):
            joboffers.append(cursor.fetchone())
        #print(joboffers)
        if joboffers[0]<6:
            for i in (1,3):
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s AND status='open'",("%" + skills[1] + "%","%" + skills[1] + "%",))
                joboffers[0]+=cursor.rowcount
                for j in range(cursor.rowcount):
                    joboffers.append(cursor.fetchone())
        if joboffers[0]<6:
            cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s",("%" + "Excel" + "%","%" + "Data Entry" + "%",))
            joboffers[0]+=cursor.rowcount
            for j in range(cursor.rowcount):
                joboffers.append(cursor.fetchone())
        session['joboffers']=joboffers
        while joboffers[0]>6:
                del[joboffers[-1]]
                joboffers[0]-=1
        return render_template('main.html',joboffers=joboffers)
    else :
        return render_template('index.html')

@app.route('/empLogin')
def empLogin():
    return render_template('empLogin.html')

@app.route('/signup', methods =["POST","GET"])
def signup():
    return render_template('signup.html')

@app.route('/forgotpassword', methods=["POST","GET"])
def forgotpassword():
    return render_template('forgotpass.html')

@app.route('/forgotpass',methods=["POST"])
def forgotpass():
    if request.method == 'POST':
        usermail=request.form['email']
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM login where email = %s",(usermail,))
        if cursor.rowcount:
            alphabet = string.ascii_letters + string.digits +'!'+'@'+'#'+'$'+'%'+'&'+'*'
            password = ''.join(secrets.choice(alphabet) for i in range(10))
            passhash = hashlib.md5(password.encode())
            passhash = passhash.hexdigest()
            try :
                cursor.execute("UPDATE login SET passhash=%s WHERE email=%s",(passhash,usermail,))
                mysql.connection.commit()
            except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
                msg='There is a problem on our side, please try after time!'
                return render_template('login.html',msg=msg)
            msg = 'Your password reset request is processed. A new password is sent to your mail.'
            TEXT = "Hello user" + ",\n\n"+ "We have received processed your password reset request. Your new password is "+password +",\n" 
            message  = 'Subject: {}\n\n{}'.format("Password Reset Request", TEXT)
            SUBJECT = "Password Reset Request"
            sendmail(TEXT,usermail,SUBJECT)
            return render_template('login.html',msg=msg)
    else :
        msg="You don't have an account registered with this email. Please click on sign up to continue."
    return render_template('login.html',msg=msg)

@app.route('/search',methods =["POST","GET"])
def search():
    joboffers=[]
    if request.method == 'POST':
        category=request.form['catgeory']
        searchtext=request.form['searchtext']
        searchtext=searchtext.lower()
        cursor = mysql.connection.cursor()
        try :
            if category == 'skill':
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE %s AND status='open'", ("%"+searchtext+"%",))
            elif category == 'job':
                cursor.execute("SELECT * FROM availjobs WHERE position LIKE %s AND status='open'",("%"+searchtext+"%",))
            elif category == 'location':
                cursor.execute("SELECT * FROM availjobs WHERE location LIKE %s AND status='open'", ("%"+searchtext+"%",))
            else :
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s AND status='open'",("%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%",))
        except :
            msg='A problem on our side please try again later!'
            return render_template('main.html',msg=msg)
        joboffers.append(cursor.rowcount)
        for i in range(cursor.rowcount):
            joboffers.append(cursor.fetchone())
        msg='Search Results'       
    return render_template('jobapply.html',msg=msg,joboffers=joboffers)

@app.route('/applyjob',methods=["POST"])
def applyjob():
    if request.method == 'POST':
        jobid=request.form['jobid']
        org=request.form['org']
        pos=request.form['pos']
        city=request.form['city']
        usermail=session['usermail']
        today=date.today()
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("INSERT INTO appliedjobs(jobid,userid,status,appliedon) VALUES (% s, % s, % s, % s)", (jobid,usermail,'pending',today))
            mysql.connection.commit()
            msg='Your application is received!'
            TEXT = "Hello "+session['username'] + ",\n\n"+ "You have succesfully applied for the position of "+pos+" at "+org+" on "+str(today)+". Your application is sent to "+org+". You can check the status of the application, in your feed. A confirmation mail will also be sent to you once the application is approved. Best regards getAjob Team!" 
            message  = 'Subject: {}\n\n{}'.format("Job application received", TEXT)
            SUBJECT = "Job application received."
            sendmail(TEXT,usermail,SUBJECT)
        except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
            msg = 'A problem on our side, please try after sometime!'
    return render_template('main.html',msg=msg,joboffers=session['joboffers'])

auth = HTTPBasicAuth()
@auth.verify_password
def verify_password(token,password):
    cursor=mysql.connection.cursor()
    passhash=token
    cursor.execute("SELECT email FROM login where passhash=% s",(passhash,))
    global user
    user=cursor.fetchone()
    if (cursor.rowcount):
        return True
    return False

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)

@app.route('/api/v1.0/jobs', methods=['GET'])
@auth.login_required
def get_jobs():
    searchtext=request.args.get('search')
    apply=request.args.get('apply')
    if apply:
        try:
            jobid=apply
            usermail=user
            today=date.today()
            cursor=mysql.connection.cursor()
            cursor.execute("INSERT INTO appliedjobs(jobid,userid,status,appliedon) VALUES (% s, % s, % s, % s)", (jobid,usermail,'pending',today))
            cursor.execute("SELECT position,organization FROM availjobs WHERE jobid=%s",(jobid,))
            temp=cursor.fetchone()
            mysql.connection.commit()
        except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
            return jsonify({'Error':'There is a problem on our side, Please try after sometime!'})
        pos=temp[0]
        org=temp[1]  
        msg='Your application is received!'
        TEXT = "Hello user,\n\n"+ "You have succesfully applied for the position of "+pos+" at "+org+" on "+str(today)+". Your application is sent to "+org+". You can check the status of the application, in your feed. A confirmation mail will also be sent to you once the application is approved. Best regards getAjob Team!" 
        message  = 'Subject: {}\n\n{}'.format("Job application received", TEXT)
        SUBJECT = "Job application received."
        sendmail(TEXT,usermail,SUBJECT)
        jobapplication={"Organsation":org,"Position":pos,"Applied on":today,"Application Status":'pending'}
        return jsonify({'Applied for ':jobapplication})

    if searchtext=='appliedjobs':
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT DISTINCT(jobid),appliedon,status FROM appliedjobs WHERE userid=%s ORDER BY appliedon LIMIT 5",(user,))
        jobs=[]
        jobcount=cursor.rowcount
        for i in range(cursor.rowcount):
            job=cursor.fetchone()
            jobs.append(job)
        appliedjobs=[]
        for i in range(jobcount):
            job=list(jobs[i])
            cursor.execute("SELECT position,Organization,location FROM availjobs WHERE jobid=% s LIMIT 5",((job[0]),))
            jobapplied=cursor.fetchone()
            appliedjob={"Organisation":jobapplied[1],"Position":jobapplied[0],"Location":jobapplied[2],"Application Status":jobs[i][2],"Date":jobs[i][1]}
            appliedjobs.append(appliedjob)
        return jsonify({'Applied Jobs':appliedjobs})
    else:
        temp=searchtext.split('-')
        searchtext= ' '.join(map(str, temp))
        try :
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT organization,position,location,skills,salary,status,dateposted,jobid FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s OR organization LIKE % s AND status='open'",("%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%",))
        except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
            joboffer={"Error":'The database is down'}
            return jsonify({'joboffers': joboffers})
        joboffer=[]
        for i in range(cursor.rowcount):
            job=cursor.fetchone()
            jobs={"Company":job[0],"Role":job[1], "Location":job[2],"Skill reqirement":job[3],"Salary":job[4],"Status":job[5],"Posted on":job[6],"Unique Id":job[7]}
            joboffer.append(jobs)
        joboffers={}
        joboffers['Available jobs for '+"'"+searchtext+"'"]=joboffer
        return jsonify({'joboffers': joboffers})
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/register', methods=["POST"])
def register():
    msg=''
    if request.method == 'POST' :
        usermail = request.form['usermail']
        if not re.match(r'[^@]+@[^@]+\.[^@]+', usermail):
            msg = 'Invalid email address !'
            return render_template('signup.html',msg=msg)
        tcCheck=request.form['tcCheck']
        if not tcCheck:
            msg = 'You should Agree to our terms and conditions to proceed!'
            return render_template('signup.html',msg=msg)

        username = request.form['firstname'] +' '+ request.form['lastname'] #Name 
        gender=request.form['gender']
        age = request.form['age']
        aboutme = request.form['aboutme']
        city = request.form['city']
        educ = request.form['NameOfGradInst'] +'!'+ request.form['gradGpa']+'!' + request.form['gradDate']+'!'+ request.form['NameofSscInst']+'!' + request.form['sscGpa']+ '!' + request.form['sscDate'] + '!'+request.form['NameofHsclInst']+'!'+request.form['HsclGpa']+ '!'+request.form['HsclDate']
        certIn = request.form['CertifiedAin']
        skillset =request.form['skillset']
        git=request.form['git']
        workedAt=request.form['workedAt']
        workExp=request.form['workExp']
        degree=request.form['degree']
        #msg=("INSERT INTO user VALUES(% s,% s,,% s,% s,% s,% s,% s,% s,% s,% s)",(usermail,username,age,aboutme,city,educ,certIn,skillset,workedAt,workExp))
        #return render_template('error.html',msg=msg)
    
        alphabet = string.ascii_letters + string.digits +'!'+'@'+'#'+'$'+'%'+'&'+'*'
        password = ''.join(secrets.choice(alphabet) for i in range(10))
        passhash = hashlib.md5(password.encode())
        passhash = passhash.hexdigest()
        #Instead of storing the password in plain text formate in the database, the password is hashed and the hash of the password is stored.
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM login WHERE email = % s', (usermail, ))
        account = cursor.fetchone()
        #print(account)
        if account:
            msg = 'This Email Address is already registered!'
            return render_template('signup.html',msg=msg)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', usermail):
            msg = 'Invalid email address !'
            return render_template('signup.html',msg=msg)
        else:
            try:
                cursor.execute("INSERT INTO login VALUES (% s, % s)", (usermail,passhash))
                cursor.execute("INSERT INTO user VALUES(% s, %s, % s, % s, %s, % s, % s, % s, % s, % s, % s, % s, % s,% s)",(usermail,username,gender,age,aboutme,city,educ,certIn,skillset,git,workedAt,workExp,date.today(),degree))
                mysql.connection.commit()
            except MySQLdb._exceptions.IntegrityError or MySQLdb._exceptions.OperationalError or MySQLdb._exceptions.ProgrammingError:
                msg = 'A problem on our side, please try after sometime!'
                return render_template('signup.html',msg=msg)
            msg = 'You are now registered with getAjob! Login to Continue. The password is sent to your mail.'
            TEXT = "Hello "+username + ",\n\n"+ "Thank you for registering at getAjob. your password is "+password +",\n"+"Please make sure that you store your password using a password manager. Our system doesn't store your password in the server. So, if you loose your password you'll have to reset your password." 
            message  = 'Subject: {}\n\n{}'.format("getAjob Registration", TEXT)
            SUBJECT = "getAjob Registration"
            sendmail(TEXT,usermail,SUBJECT)
    elif request.method == 'POST':
            msg = 'Please fill out the form !'
    return render_template('login.html', msg = msg)

@app.route('/login', methods=["POST","GET"])
def login():
    msg=''
    if request.method == 'GET':
        msg='Please login to proceed!'
        return render_template('login.html',msg=msg)
    if request.method == 'POST' :
        email = request.form['email']
        password = request.form['password']
        passhash = hashlib.md5(password.encode())
        passhash = passhash.hexdigest()
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM login WHERE email = % s AND passhash = % s', (email, passhash),)
            account = cursor.fetchone()
        except MySQLdb._exceptions.OperationalError :
            msg='We are facing issues, Please try after sometime!'
            return render_template('login.html',msg=msg)
        #print (account)
        if account:
            session['loggedin'] = True
            session['id'] = account[0]
            userid=  account[0]
            session['usermail'] = account[0]
            msg = 'Logged in successfully !'
            joboffers=[]

            cursor = mysql.connection.cursor()
            usermail=session['usermail']
            cursor.execute("SELECT username,skillset,city FROM user WHERE usermail= % s",(session['usermail'],))
            user=cursor.fetchone()
            city=user[2].split(',') #session['usercity']
            session['username']=user[0]
            skills=user[1].split(',')  #=session['userskills']
            #print(skills)
            cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s AND status='open'",("%" + skills[0] + "%","%" + skills[0] + "%","%" + city[0] + "%",))
            joboffers=[]
            joboffers.append(cursor.rowcount)
            for i in range(cursor.rowcount):
                joboffers.append(cursor.fetchone())
            #print(joboffers)
            if joboffers[0]<6:
                for i in (1,3):
                    cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s AND status='open'",("%" + skills[1] + "%","%" + skills[1] + "%",))
                    joboffers[0]+=cursor.rowcount
                    for j in range(cursor.rowcount):
                        joboffers.append(cursor.fetchone())
            if joboffers[0]<6:
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s",("%" + "Excel" + "%","%" + "Data Entry" + "%",))
                joboffers[0]+=cursor.rowcount
                for j in range(cursor.rowcount):
                    joboffers.append(cursor.fetchone())
            while joboffers[0]>6:
                del[joboffers[-1]]
                joboffers[0]-=1
            session['joboffers']=joboffers
            return render_template('main.html',joboffers=joboffers)
        else:
            msg = 'Incorrect username / password !'
            return render_template('login.html', msg = msg)

@app.route('/logout')
def logout():
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   return render_template('index.html')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug = True,port = 8080)
