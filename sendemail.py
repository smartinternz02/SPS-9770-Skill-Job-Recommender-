import smtplib
import os
s = smtplib.SMTP('smtp.gmail.com', 587)
def sendmail(TEXT,email,SUBJECT):
    #print("sorry we cant process your candidature")
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.login("getaJob.Communication@gmail.com", "g3t@j0b4#U$")
    message  = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
    s.sendmail("getaJob.Communication@gmail.com", email, message)
    s.quit()