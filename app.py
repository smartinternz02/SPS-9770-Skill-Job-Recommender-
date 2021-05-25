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

########################################       API SECTION   #########################################
'''This section of the code consists of the api logic which includes verifying the user's username(token) in the database and fetching
    the details of the user to be used to fetch user's applied jobs status and also to apply to a job requested by the user. The paramter
    search can take organization, position, role or location as input and return a json of the results to the user. Along with this the
    user can check status of applied jobs and can also apply to a job.
    The methods verify_password, error_handler and unauthorized access are to verify the user's account and to return an error message if
    the user's api token is incorrect or if the user doesn't have an account.
    The api page method is used to display the api documentation page which also fetches the user's api key and displays it on the top.
'''
@app.route('/apipage')
def apipage():
    #Takes user email from session, fetches api token of the user and passes it to the html documentation page of the api.
    email=session['usermail']
    try :
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT passhash FROM login WHERE email = %s",(email,))
        if cursor.rowcount:
            passhash=cursor.fetchone()
            apitoken=passhash
        else :
            apitoken=""
    except Exception as e:
        print('cannot fetch api token of user ',e)
    return render_template('apiDocumentation.html',apitoken=apitoken)

auth = HTTPBasicAuth()
@auth.verify_password
def verify_password(token,password):
    cursor=mysql.connection.cursor()
    passhash=token
    try:
        cursor.execute("SELECT email FROM login where passhash=% s",(passhash,))
    except Exception as e:
        print('Cannot access db',e)
    global user
    user=cursor.fetchone()
    if (cursor.rowcount):
        return True
    return False

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)

@app.route('/api/v1.0/jobs', methods=['GET','POST'])
@auth.login_required
def get_jobs():
    #Serves api requests of the user and chatbot
    if request.headers.get('Content-Type') == 'application/json':
        #If the content type is of json the request is originating from the chatbot
        content = request.get_json(silent=True)
        searchtext=content['search']
        temp=searchtext.split('-')
        searchtext= ' '.join(map(str, temp))
        try :
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT organization,position,location FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s OR organization LIKE % s AND status='open' LIMIT 2",("%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%",))
        except Exception as e:
            print('While serving chatbot request :',e)
            joboffer={"Error":'The Service is not accessible currently.'}
            return jsonify({'joboffers': joboffer})
        joboffer=[]
        for i in range(cursor.rowcount):
            job=cursor.fetchone()
            jobs=job[0]+" is offering the role of "+job[1]+" at "+job[2]+"."
            #Instead of sending a dictionary or json to the user, the result is formatted into a sentence and sent to the api, which displays it with a little processing.
            joboffer.append(jobs)
        if cursor.rowcount==1:
            joboffer.append(jobs)
        if not cursor.rowcount:
            #For some reason if the results for the querry are nill, the same is shown to the user via chat message.
            jobs="Sorry, currently there are no job openings for your profile!"
            joboffers.append(jobs)
        applylink='<style>.buton{background: none!important;border: none;padding: 0!important;color: #069;text-decoration: underline;cursor: pointer; }</style>'
        applylink+='<form action="/search" method="post"><input type="text" value="'+searchtext+'"name="searchtext" hidden><input type="text" value="job" name="category" hidden><input type="submit" class="buton" value="Apply here"></form>'
        joboffer.append(applylink)
        #applylink is a html button clicking on which the same search parameter is passed to the search function and the results page is displayed where the user can apply for a job.
        return {"jobs":joboffer,"apply":applylink}

    else :
        #If the request has a get parameter then the request is from a user
        searchtext=request.args.get('search')
        apply=request.args.get('apply')
        if apply:
            #If the parameter is apply, then the user is trying to apply for a job using the api and passing the jobid to which they want to apply.
            try:
                jobid=apply
                usermail=user
                today=date.today()
                cursor=mysql.connection.cursor()
                cursor.execute("INSERT INTO appliedjobs(jobid,userid,status,appliedon) VALUES (% s, % s, % s, % s)", (jobid,usermail,'pending',today))
                cursor.execute("SELECT position,organization FROM availjobs WHERE jobid=%s",(jobid,))
                temp=cursor.fetchone()
                if not cursor.rowcount:
                    #If an invalid jobid is passed the json file has an error message indicating the same to the user.
                    jobapplication="Job doesn't exist for the Id :"+apply+" !"
                    return jsonify({'Applied for':jobapplication})
                mysql.connection.commit()
                pos=temp[0]
                org=temp[1]  
                msg='Your application is received!'
                TEXT =f"""\
Hello user,

Thank you for applying to the role of {pos} at {org}. 

We are happy to announce that your application for the role of {pos}
at {org} is received. All further communication will be from {org}.
If you are among the qualified candidates, you will receive  communication
from  the recruiters of {org} to schedule a virtual interview.

In any case, we will keep you posted on the  status of your 
application. You can also check the status of your application
from the profile section of the website.

Application Details
Organization : {org}
Position : {pos}

Wishing you all the best and Luck.
Regards,
GetaJob Team.

This is a system generated email, please do not reply to this email.
                """
                SUBJECT = "Application Received!"
                sendmail(TEXT,usermail,SUBJECT)
                jobapplication={"Organsation":org,"Position":pos,"Applied on":today,"Application Status":'pending'}
            except Exception as e:
                print('User trying to apply for a job using api failed or mail sending failed :',e)
                return jsonify({'Error':'There is a problem on our side, Please try after sometime!'})
            #If applied succesfully an entry is added to the db and a confirmation email is sent to the user of the same.
            return jsonify({'Applied for ':jobapplication})

    if searchtext=='appliedjobs':
        #If the user wants to know the status of their job applications the search param would be appliedjobs
        try :
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
        except Exception as e:
            print('Trying to access the db to display user applied jobs failed',e)
            return jsonify({'Error':'There is a problem on our side, Please try after sometime!'})
    else:
        #The search text passed by the user is taken, and is split,(full-stack-developer to full stack developer, hyphens replaced by spaces)
        temp=searchtext.split('-')
        searchtext= ' '.join(map(str, temp))
        #The search text passed by the user is compared against skills organisation position and location and the results are sent to the user
        try :
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT organization,position,location,skills,salary,status,dateposted,jobid FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s OR organization LIKE % s AND status='open'",("%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%",))
        except Exception as e:
            print('While the user is trying to check jobs using the api :',e)
            #If accessing the database fails the user is replied the same.
            joboffer={"Error":'The service is not accessible currently!'}
            return jsonify({'joboffers': joboffer})
        joboffer=[]
        for i in range(cursor.rowcount):
            job=cursor.fetchone()
            jobs={"Company":job[0],"Role":job[1], "Location":job[2],"Skill reqirement":job[3],"Salary":job[4],"Status":job[5],"Posted on":job[6],"Unique Id":job[7]}
            joboffer.append(jobs)
        #If the querry results in any jobs the same are sent as json to the user.
        joboffers={"Desc ":"Available job offers for "+"'"+searchtext+"'"}
        #if the user's searchtext doesn't match any, the user receives no jobs message
        if not cursor.rowcount:
            joboffer="Currently there are no job openings!"
        joboffers['jobs']=joboffer
        return jsonify({'joboffers': joboffers})
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

######################################## END OF  API SECTION   #########################################

########################################  EMPLOYER SECTION    ##########################################
'''This section of the code contains the logic required for employer's interface of the webapp which includes employer login, employer dashboard, approving a job, 
   rejecting a job, closing a job and viewing applicant profile along with employer documentation.
'''
@app.route('/empLogin')
def empLogin():
    #No computation, just to render the html page
    return render_template('empLogin.html')

@app.route('/empdocumentation',methods=["POST","GET"])
def empdocumentation():
    #displays documentation to the user
    return render_template('empdocumentation.html')

@app.route('/emlogin', methods=["GET","POST"])
def emlogin():
    #Verifies employer's account and fetches dashboard data
    if request.method == 'GET':
        msg='Please login to proceed!'
        return render_template('empLogin.html',msg=msg)
    if request.method == 'POST' :
        email = request.form['email']
        passphrase = request.form['password']
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM employer WHERE username = % s AND passphrase = % s', (email, passphrase),)
            account = cursor.fetchone()
        except Exception as e:
            print('Cannot fetch login details from db',e)
            msg='We are facing issues, Please try after sometime!'
            return render_template('empLogin.html',msg=msg)
        if account:
            session['loggedin'] = True
            session['id'] = account[1]
            Organisation=account[0]
            #fetches all the jobs posted by the employer
            cursor.execute('SELECT jobid,position,location,status,dateposted FROM availjobs WHERE organization = % s AND status = "open"',(Organisation,),)
            postedjobs=[]
            posted_job_Ids=[]
            postedjobs.append(cursor.rowcount) #posted_job_count
            for i in range(cursor.rowcount):
                row=cursor.fetchone()
                posted_job_Ids.append(row[0])
                job={"Unique Id ":row[0],"Position":row[1],"Location":row[2],"Status":row[3],"Posted on":row[4]}
                postedjobs.append(job)
            total_applications_received=[]
            for jobid in posted_job_Ids:
                job_applications_received=[]
                #fetches all the job applications received for each and every job posted by the employer
                cursor.execute('SELECT distinct(appid),userid,status,appliedon FROM appliedjobs WHERE jobid = % s AND status="pending" ORDER BY appliedon',(jobid,),)
                for i in range(cursor.rowcount):
                    row=cursor.fetchone()
                    jappl={"Application Id":row[0],"Applicant":row[1],"Status":row[2]}
                    job_applications_received.append(jappl)
                total_applications_received.append({jobid:job_applications_received})
            #After fetching all the posted jobs and the received applications they are sent to the dashboard page
            return render_template('employer.html',postedjobs=postedjobs,applications=total_applications_received)

@app.route('/applicant/<usermail>',methods=["GET"])
def applicant(usermail):
    #Displays profile of the applicant after fetching the details of the applicant from the db, using the applicant's User Id.
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM user WHERE usermail = % s', (usermail, ))
        account = cursor.fetchone()
        userdetails=account
        edu=account[6].split('!')
    except Exception as e:
        print('Cannot access db to show applicant profile',e)
        msg = 'A problem on our side, please try after sometime!'
        return 'Failed!'
    return render_template('applicant.html',userdetails=userdetails,edu=edu)

@app.route('/closejob', methods=["POST"])
def closejob():
    #Changes the status of a job to closed and all the applicant's job status to rejected when the employer clicks on close a job
    if request.method == 'POST':
        jobid=request.form['closejob_id']
        try:
            cursor = mysql.connection.cursor()
            print(jobid)
            cursor.execute("UPDATE availjobs SET status='closed' WHERE jobid=% s",(jobid,),)
            cursor.execute("UPDATE appliedjobs SET status='rejected' WHERE jobid=% s",(jobid,),)
            mysql.connection.commit()
            msg='Job Status changed to Closed!,please login again to continue.'
        except Exception as e:
            print(e)
            msg='There was a problem parsing your request please try after sometime!'
        #The employer is logged out, when such an action is performed and asked to login again.
        return render_template('empLogin.html',msg=msg)

@app.route('/approvejob',methods=["GET"])
def approvejob():
    #When employer clicks on approve job of a user, the status is changed to approved to changed and the user is intimated with an email
    appid=request.args.get('id')
    try:
        cursor=mysql.connection.cursor()
        cursor.execute('UPDATE appliedjobs SET status="Approved" WHERE appid=% s',(appid,),)
        cursor = mysql.connection.commit()
        cursor=mysql.connection.cursor()
        #email address(userid) of the user is fetched and an email is sent to the user.
        cursor.execute("SELECT userid FROM appliedjobs WHERE appid=% s",(appid,),)
        usermail=cursor.fetchone()
        TEXT =f"""\
Hello User!

We are happy to announce that one of your applications was approved.
Please check your profile for further details, you will receive
communication from  the recruiters shortly to schedule a virtual interview. 

Wishing you all the best for the interview.
Regards,
GetaJob Team.

This is a system generated email, please do not reply to this email.
            """
        SUBJECT = "Application approved!"
        sendmail(TEXT,usermail,SUBJECT)
        msg='Application of the user approved!'
        return render_template('application.html',msg=msg)
    except Exception as e:
        print('Cannot access db or mailing failed to change application status to approved!',e)
        msg='A Problem on our side, please try again later!'
        return render_template('empLogin.html',msg=msg)

@app.route('/rejectjob',methods=["GET"])
def rejectjob():
    #when employer rejects an application the status of the application is changed to rejected and an email is sent to the user informing the same.
    appid=request.args.get('id')
    try:
        print(appid)
        cursor=mysql.connection.cursor()
        cursor.execute('UPDATE appliedjobs SET status="Rejected" WHERE appid=% s',(appid,),)
        mysql.connection.commit()
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT userid FROM appliedjobs WHERE appid=% s",(appid,),)
        usermail=cursor.fetchone()
        TEXT =f"""\
Hello User!

We are sorry to inform you that one of your applications was rejeted.
Please check your profile for further details.

Please use the learning resources provided to upskill yourself.
Wishing you all the best!
Regards,
GetaJob Team.

This is a system generated email, please do not reply to this email.
            """
        SUBJECT = "Application rejected!"
        sendmail(TEXT,usermail,SUBJECT)
        msg='Application of the user is rejected!'
        return render_template('application.html',msg=msg)
    except Exception as e:
        print('Cannot access db or mailing failed to change application status to approved!',e)
        msg='A Problem on our side, please try again later!'
        return render_template('empLogin.html',msg=msg)

######################################## END OF EMPLOYER SECTION   #########################################

######################################## User SECTION   1.1 #########################################
'''These functions only render html pages and there isn't any logic to be performed!'''

@app.route('/documentation',methods=["POST","GET"])
def documentation():
    #displays website documentation to the user
    return render_template('documentation.html')

@app.route('/forgotpassword', methods=["POST","GET"])
def forgotpassword():
    #displays the forgot password form to the user
    return render_template('forgotpass.html')

@app.route('/learn')
def learn():
    #Takes the user to the index page, scrolls down to the resources section and highlights it.
    return render_template('index.html', scroll='learn')

@app.route('/loginpage')
def loginpage():
    #Displays login form to the user.
    return render_template('login.html')

@app.route('/signup', methods =["POST","GET"])
def signup():
    #Dispalys sign up form to the user.
    return render_template('signup.html')

@app.route('/tc')
def tc():
    #Displays the terms and conditions page of the website to the user.
    return render_template('TermsConditions.html')
######################################## End of User SECTION   1.1 #########################################

######################################## User SECTION   1.2 #########################################
'''Register, Login, Sign up and forgot password'''
@app.route('/register', methods=["POST"])
def register():
    #The data from the sign up form is collected and an account is created of the user.
    msg=''
    if request.method == 'POST' :
        usermail = request.form['usermail']
        if not re.match(r'[^@]+@[^@]+\.[^@]+', usermail):
            msg = 'Invalid email address !'
            return render_template('signup.html',msg=msg)
        tcCheck=request.form['tcCheck']
        if not tcCheck:
            #Checks user agreement to the terms and conditions.
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
    
        alphabet = string.ascii_letters + string.digits +'!'+'@'+'#'+'$'+'%'+'&'+'*'
        password = ''.join(secrets.choice(alphabet) for i in range(10))
        passhash = hashlib.md5(password.encode())
        passhash = passhash.hexdigest()
        #Instead of storing the password in plain text formate in the database, the password is hashed and the hash of the password is stored.
        cursor = mysql.connection.cursor()
        #checks if the user already has an account
        cursor.execute('SELECT * FROM login WHERE email = % s', (usermail, ))
        account = cursor.fetchone()
        if account:
            msg = 'This Email Address is already registered!'
            return render_template('signup.html',msg=msg)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', usermail):
            msg = 'Invalid email address !'
            return render_template('signup.html',msg=msg)
        else:
            try:
                cursor.execute("INSERT INTO user VALUES(% s, %s, % s, % s, %s, % s, % s, % s, % s, % s, % s, % s, % s,% s)",(usermail,username,gender,age,aboutme,city,educ,certIn,skillset,git,workedAt,workExp,date.today(),degree))
                cursor.execute("INSERT INTO login VALUES (% s, % s)", (usermail,passhash))
                mysql.connection.commit()
                msg = 'You are now registered with getAjob! Login to Continue. The password is sent to your mail.'
                TEXT =f"""\
Hi {username},

Welcome to getaJob, Thank you for registering with us. 
Your account is now actived. This confirmation is for your
records, and this mail also has the password that you will
use to login to the website. So, please retain this email.

Registration Details
Name     : {username}
Email    : {usermail}
Password : "{password}"

Wishing you all the best!
Regards,
GetaJob Team.

If you have any questions, including changes to your registration or 
cancellation of request. Please feel free to reply to this email.
                """
                SUBJECT = "GETaJob Registration"
                sendmail(TEXT,usermail,SUBJECT)
            except Exception as e:
                print('Inserting data into login or user table failed :',e)
                msg = 'A problem on our side, please try after sometime!'
                return render_template('signup.html',msg=msg)
    elif request.method == 'GET':
            msg = 'Please fill out the form !'
    #An email is sent to the user with login details and a message is displayed on the login form.
    return render_template('login.html', msg = msg)

@app.route('/forgotpass',methods=["POST"])
def forgotpass():
    #Resets the user's password, if for some reason they loose there password.
    if request.method == 'POST':
        usermail=request.form['email']
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM login where email = %s",(usermail,))
        if cursor.rowcount:
            #If the account exists a new password is generated
            alphabet = string.ascii_letters + string.digits +'!'+'@'+'#'+'$'+'%'+'&'+'*'
            password = ''.join(secrets.choice(alphabet) for i in range(10))
            passhash = hashlib.md5(password.encode())
            passhash = passhash.hexdigest()
            try :
                cursor.execute("UPDATE login SET passhash=%s WHERE email=%s",(passhash,usermail,))
                mysql.connection.commit()
                #The generated password's hash is added to the db, and the password is sent to the user via email.
                msg = 'Your password reset request is processed. A new password is sent to your mail.'
                TEXT =f"""\
Hi user,

We have processed your password reset request. 
You can now access your account with the following
login credentials. This mail has the password that
you would use from now on to login to the website.
So, please retain this email.

Login Details
Email    : {usermail}
Password : " {password} "

Wishing you All the best!
Regards,
GetaJob Team.

This is a system generated email, please do not reply to this email.
                """
                SUBJECT = "Password Rest Request"
                sendmail(TEXT,usermail,SUBJECT)
            except Exception as e:
                print('Cannot add updated password to db',e)
                msg='There is a problem on our side, please try after time!'
                return render_template('login.html',msg=msg)
        else :
            #If the user doesn't have an account, this message is displayed on the login form.
            msg="You don't have an account registered with this email. Please click on sign up to continue."
    #The generated password is sent to the user, added to the db, and a message is displayed on the login form
    return render_template('login.html',msg=msg)


@app.route('/login', methods=["POST","GET"])
def login():
    #Logs user into the website and sets the session variables
    msg=''
    if request.method == 'GET':
        msg='Please login to proceed!'
        return render_template('login.html',msg=msg)
    if request.method == 'POST' :
        email = request.form['email']
        password = request.form['password']
        passhash = hashlib.md5(password.encode())
        passhash = passhash.hexdigest()
        #The entered password is converted into passhash and the hash is compared from the database.
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM login WHERE email = % s AND passhash = % s', (email, passhash),)
            account = cursor.fetchone()
        except Exception as e:
            print('Cannot fetch login details from db',e)
            msg='We are facing issues, Please try after sometime!'
            return render_template('login.html',msg=msg)
        #print (account)
        if account:
            try:
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
                #All the session variables are set, and job suggestions are fetched for the user and displayed on the main page.
                return render_template('main.html',joboffers=joboffers)
            except Exception as e:
                print(e)
                return render_template('index.html',msg='Cannot fetch job recommendations, Please try after sometime.')
        else:
            msg = 'Incorrect username / password !'
            #If the username or password is incorrect.
            return render_template('login.html', msg = msg)

@app.route('/logout')
def logout():
    #If the user clicks on logout, all the session variables that are set are removed.
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   session.pop('joboffers', None)
   #Takes the user back to the landing page and a message is displayed that the user is logged out.
   return render_template('index.html',msg='You have been logged out!')

######################################## End of User SECTION   1.2 #########################################

######################################## User SECTION   1.3 ################################################
'''This last user section consists of the code, that processes user data and serves the user. 
    Dashboard displays the main page for the user, fetching job recommendations from db,
    profile displays the profile section of the user fetching user data and applied jobs from db,
    appliedjobs displays status of user's job applications fetching the data from the db,
    search takes category and search text as input from the user, queries and displays data,
    applyjob takes job details and creates an entry in the db as a job application.
 '''

@app.route('/appliedjobs')
def appliedjobs():
    #Fetches applied jobs from the db, and displays to the user.
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT DISTINCT(jobid),appliedon,status FROM appliedjobs WHERE userid=%s ORDER BY appliedon ASC",(session['usermail'],))
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
            appliedjob={"Organisation":jobapplied[1],"Position":jobapplied[0],"Status":jobs[i][2],"Applied On":jobs[i][1]}
            appliedjobs.append(appliedjob)
    except Exception as e:
        print('Cannot access db to show user profile',e)
        msg = 'A problem on our side, please try after sometime!'
        #If the db cannot be accessed, the user is a notified with a message.
        return render_template('main.html',msg=msg)
    return render_template('appliedjobs.html',appliedjobs=appliedjobs)

@app.route('/applyjob',methods=["POST"])
def applyjob():
    #when a user applies for a job, the user is notified via email and an entry is made in the database as job applcation.
    if request.method == 'POST':
        jobid=request.form['jobid']
        org=request.form['org']
        pos=request.form['pos']
        city=request.form['city']
        usermail=session['usermail']
        today=date.today()
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("SELECT status FROM appliedjobs WHERE jobid= % s",(jobid,),)
            if cursor.rowcount:
                status=cursor.fetchone()
                msg='You have already applied for this job, and the status is '+status[0]+' !'
                return render_template('main.html',msg=msg,joboffers=session['joboffers'])
            cursor.execute("INSERT INTO appliedjobs(jobid,userid,status,appliedon) VALUES (% s, % s, % s, % s)", (jobid,usermail,'pending',today))
            mysql.connection.commit()
            msg='Your application is received!'
            TEXT =f"""\
Hi {session['username']},

Thank you for applying to the role of {pos} at {org}. 

We are happy to announce that your application for the role of {pos}
at {org} is received. All further communication will be from {org}.
If you are among the qualified candidates, you will receive  communication
from  the recruiters of {org} to schedule a virtual interview. 

In any case, we will keep you posted on the  status of your application.
You can also check the status of your application from the profile section
of the website.

Application Details
Organization : {org}
Position : {pos}
Name    : {session['username']}
Email  for correspondence {usermail}.

Wishing you all the best and we hope you will land in your dream job soon.
Regards,
GetaJob Team.

This is a system generated email, please do not reply to this email.
            """
            SUBJECT = "Application Received!"
            sendmail(TEXT,usermail,SUBJECT)
        except Exception as e:
            print('Cannot add applied job to db or send mail to user',e)
            msg = 'A problem on our side, please try after sometime!'
    return render_template('main.html',msg=msg,joboffers=session['joboffers'])

@app.route('/dashboard')
def dashboard():
    #fetches job recommendations of the user and displays on the main page.
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
        try :
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
        except Exception as e:
            print('Cannot fetch suggested jobs for user from db',e)
            return render_template('index.html',msg='We are facing issues, please try after a while')
        return render_template('main.html',joboffers=joboffers)
    else :
        return render_template('login.html',msg='Please log in to continue')

@app.route('/profile',methods=["POST","GET"])
def profile():
    #Fetches details of the user from database and displays on the profile page
    if not session['loggedin']:
        msg='Please login to proceed!'
        return render_template('login.html',msg=msg)
    else :
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM user WHERE usermail = % s', (session['usermail'], ))
            account = cursor.fetchone()
            userdetails=account
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
        except Exception as e:
            print('Cannot access db to show user profile',e)
            msg = 'A problem on our side, please try after sometime!'
            return render_template('main.html',msg=msg)
        return render_template('profile.html',userdetails=userdetails,edu=edu,appliedjobs=appliedjobs)


@app.route('/search',methods =["POST","GET"])
def search():
    #When user clicks on search the selected category is taken along with the searchtext, and querries the db.
    msg=''
    joboffers=[]
    if request.method == 'POST':
        category=request.form['category']
        searchtext=request.form['searchtext']
        searchtext=searchtext.lower()
    if request.method == 'GET':
        #Also serves the index pages job gallery section
        category='roleorg'
        searchtext=request.args.get('searchtext')
        searchtext=searchtext.lower()
    cursor = mysql.connection.cursor()
    if searchtext and category:
        try :
            if category == 'skill':
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE %s AND status='open'", ("%"+searchtext+"%",))
            elif category == 'job':
                cursor.execute("SELECT * FROM availjobs WHERE position LIKE %s AND status='open'",("%"+searchtext+"%",))
            elif category == 'location':
                cursor.execute("SELECT * FROM availjobs WHERE location LIKE %s AND status='open'", ("%"+searchtext+"%",))
            elif category == 'suggestions':
                searchtext=searchtext.split(',')
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s AND status='open'",("%"+searchtext[3]+"%","%"+searchtext[0]+"%","%"+searchtext[1]+"%",))
            elif category == 'roleorg':
                #serves index pages job gallery section
                cursor.execute("SELECT * FROM availjobs WHERE position LIKE %s OR organization LIKE % s AND status='open'",("%"+searchtext+"%","%"+searchtext+"%",))
            else :
                #if category is not specified, querries the db matching skill, position and location
                cursor.execute("SELECT * FROM availjobs WHERE skills LIKE % s OR position LIKE % s OR location LIKE % s AND status='open'",("%"+searchtext+"%","%"+searchtext+"%","%"+searchtext+"%",))
        except Exception as e:
            print('Cannot fetch from db to show search results',e)
            msg='A problem on our side please try again later!'
            return render_template('main.html',msg=msg)
        joboffers.append(cursor.rowcount)
        for i in range(cursor.rowcount):
            joboffers.append(cursor.fetchone())
        msg='Search Results'       
        return render_template('jobapply.html',msg=msg,joboffers=joboffers)

if __name__ == '__main__':
    #main function of the app, runs everything on port 8080, debug = true dynamically updates the webapp without the need of restarting.
    app.run(host='0.0.0.0',debug = True,port = 8080)