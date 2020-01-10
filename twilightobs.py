from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np
import db_conn
import datetime
import json
import urllib
import re
import time
import hashlib
import os
import yaml

def twilightobs_select():
    # grab selected parameters from drop-down menu
    utdate = request.args.get("utdate")
    starttime = request.args.get("starttime")
    duration = request.args.get("duration")
    endtime = request.args.get("endtime")
    telnr = request.args.get("telnr")
    instr = request.args.get("instr")
    semester = request.args.get("semester")
    projcode = request.args.get("projcode")
    institution = request.args.get("institution")
    piid = request.args.get("piid")
    observerid = request.args.get("observerid")
    nightlogticket = request.args.get("nightlogticket")
    delflag = request.args.get("delflag")
    moddate = request.args.get("moddate")

    #check for SQL injections
    if not verify_inputs([utdate,starttime,duration,endtime,telnr,instr,semester,projcode,institution,piid,observerid,nightlogticket,delflag,moddate]):
        print('inputs verified')
    else:
        return f'SQL Injection Detected'

    #get all possible parameters from URL, collect into list
    paramname = ['UTDate','StartTime','Duration','EndTime','TelNr','Instr','Semester','ProjCode','Institution','PiId','ObserverId','NightlogTicket']
    params = [utdate,starttime,duration,endtime,telnr,instr,semester,projcode,institution,piid,observerid,nightlogticket]

    #if no parameters input, show all twilightObserving table entries
    if not any(params):
        query = "select * from twilightObserving where DelFlag=0;"
    else: 
        query = "select * from twilightObserving where DelFlag=0"
        for i,p in enumerate(params):
            if p is not None:
                p = p.replace("'","")
                if paramname[i] == 'Instr':
                    #instr needs %% due to suffixes (-LGS,-NGS, etc.)
                    query += f" and {paramname[i]} like '{'%'+p+'%'}'"
                else:
                    query += f" and {paramname[i]} like '{p}'"
        query += ';'


    #do query
    result = dbquery(query)
    url = 'https://www.keck.hawaii.edu/software/db_api/telSchedule.php?cmd=getObserverInfo&obsid='
    for key, entry in enumerate(result):
        result[key]['PILastName'] = result[key]['PIFirstName'] = ''
        if entry['PiId'] == None: continue
        data = urllib.request.urlopen(url+str(entry['PiId']))
        data = data.read().decode('utf8')
        data = json.loads(data)
        if data:
            result[key]['PILastName'] = data['LastName']
            result[key]['PIFirstName'] = data['FirstName']

    return json.dumps(result,default=jsonConverter)

def verify_inputs(paramarray):
    #check all GET parameters for SQL commands
    sqlcmdlist = ['alter','create','delete','grant','revoke','commit','rollback','savepoint','drop','insert','join','select','truncate','union','update']
    injectionarr = []
    #for each command
    for c in sqlcmdlist:
        #for each GET parameter
        for p in paramarray:
            #attempt (will go to except if parameter is None)
            try:
                #if SQL command in GET parameter, add to injection array
                if c in p:
                    print(c,paramarray)
                    injectionarr += [p]
            except:
                pass
    #return attempted injections
    return injectionarr

def twilightobs_insert():

    #get supplied hash from insert call
    hash_cron = request.args.get('hash')
    hashacc = yaml.safe_load(open('config.live.ini'))['Hash']['account']

    #get hash for KCRON user only
    #hash_verif = hashlib.md5(b'kcron').hexdigest()
    hash_verif = hashlib.md5(hashacc.encode('utf-8')).hexdigest()
    #check if correct user (kcron crontab only)
    if hash_cron != hash_verif:
        return "INCORRECT USER"
    else:
        print('HASH VERIFIED')

    # grab selected parameters from drop-down menu
    utdate = request.args.get("utdate")
    starttime = request.args.get("starttime")
    duration = request.args.get("duration")
    endtime = request.args.get("endtime")
    telnr = request.args.get("telnr")
    instr = request.args.get("instr")
    semester = request.args.get("semester")
    projcode = request.args.get("projcode")
    institution = request.args.get("institution")
    piid = request.args.get("piid")
    observerid = request.args.get("observerid")
    nightlogticket = request.args.get("nightlogticket")
    delflag = request.args.get("delflag")
    moddate = request.args.get("moddate")

    #print required parameters
    print('Start:',starttime)
    print('UT:',utdate)
    print('Telnr:',telnr)
    print('Instr:',instr)
    print('End:',endtime)
    print('Duration:',duration)
    
    #check for SQL injections
    if not verify_inputs([utdate,starttime,duration,endtime,telnr,instr,semester,projcode,institution,piid,observerid,nightlogticket,delflag,moddate]):
        print('inputs verified')
    else:
        return f'SQL Injection Detected'
    #check required parameters
    if not (utdate and starttime and telnr and instr and (endtime or duration)):
        return f"Please specify the following parameters: utdate, starttime, telnr, instr, duration/endtime<br><br>utdate: {utdate}<br>starttime: {starttime}<br>duration: {duration}<br>endtime: {endtime}<br>telnr: {telnr}<br>instr: {instr}"

    #check telnr
    if telnr not in ['1','2']:
        return f"telnr must be 1 or 2"

    #check instr, autocorrect if possible
    if instr not in ['OSIRIS-NGS','NIRC2-NGS']:
        try:
            if telnr == '1':
                instr='OSIRIS-NGS'
            elif telnr == '2':
                instr='NIRC2-NGS'
        except:
            return "Current valid instruments are OSIRIS-NGS (K1) and NIRC2-NGS (K2)"

    #if starttime and duration supplied, calculate endtime
    if starttime and duration and not endtime:
        #strip out extra quotes
        starttime = starttime.replace("'","")
        duration = duration.replace("'","")
        #format starttime and duration
        try:
            startdt = datetime.datetime.strptime(starttime,'%H:%M:%S')
        except:
            startdt = datetime.datetime.strptime(starttime,'%H:%M')
        durdt = duration.split(':')
        try:
            #HH:MM
            if len(durdt)==2:
                durdt = datetime.timedelta(hours=int(durdt[0]),minutes=int(durdt[1]))
            #HH:MM:SS
            elif len(durdt)==3:
                durdt = datetime.timedelta(hours=int(durdt[0]),minutes=int(durdt[1]),seconds=int(durdt[2]))
        except:
            return "Format duration as HH:MM or HH:MM:SS"
        #add
        endtime = startdt+durdt
        #get endtime as a string
        endtime = endtime.strftime('%H:%M:%S')

    #if starttime and endtime supplied, calculate duration
    elif starttime and endtime and not duration:
        starttime = starttime.replace("'","")
        endtime = endtime.replace("'","")
        #accept HH:MM:SS or HH:MM formatting
        try:
            startdt = datetime.datetime.strptime(starttime,'%H:%M:%S')
        except:
            startdt = datetime.datetime.strptime(starttime,'%H:%M')
        try:
            enddt = datetime.datetime.strptime(endtime,'%H:%M:%S')
        except:
            enddt = datetime.datetime.strptime(endtime,'%H:%M')

        duration = str(enddt - startdt)

    #if utdate supplied, calculate semester
    if utdate and not semester:
        #strip out extra quotes
        utdate = utdate.replace("'","")
        utdt = datetime.datetime.strptime(utdate, '%Y-%m-%d')
        #get entry year as integer
        year = utdt.year
        #specify possible semesters for entry year (yr-1B,yrA,yrB)
        lastyrB = [datetime.datetime(year-1,8,1),datetime.datetime(year,1,31)]
        thisyrA = [datetime.datetime(year,2,1),datetime.datetime(year,7,31)]
        thisyrB = [datetime.datetime(year,8,1),datetime.datetime(year+1,1,31)]
        #categorize into appropriate semester
        if utdt >= lastyrB[0] and utdt <= lastyrB[1]:
            semester = str(lastyrB[0].year)+'B'
        elif utdt >= thisyrA[0] and utdt <= thisyrA[1]:
            semester = str(year)+'A'
        elif utdt >= thisyrB[0] and utdt <= thisyrB[1]:
            semester = str(year)+'B' 

    #find institution
    if semester and projcode and not institution:
        #remove ToO_ project code prefixes
        projcode = projcode.replace('ToO_','')
        proposalsapi = yaml.safe_load(open('config.live.ini'))['PropAPI']['url']
        #query proposals API for institution based on semester and project code
        allocinst = f"{proposalsapi}?cmd=getAllocInst&ktn={semester}_{projcode}"
        data = urllib.request.urlopen(allocinst)
        data = data.read().decode('utf8')
        data = data.replace('null',"'null'")
        if 'Usage:' in data or data == 'error':
            data = None
        institution = data

    #find piid
    if semester and projcode and not piid:
        projcode = projcode.replace('ToO_','')
        #query proposals API for piid based on semester and project code
        getpiid = f"{proposalsapi}?output=web&cmd=getPIID&ktn={semester}_{projcode}"
        data = urllib.request.urlopen(getpiid)
        data = data.read().decode('utf8')
        data = data.replace('null',"'null'")
        if 'Usage:' in data or data == 'error' or data == '0':
            data = None
        piid = data

    #get all supplied or calculated parameters, collect into list
    paramname = ['UTDate','StartTime','Duration','EndTime','TelNr','Instr','Semester','ProjCode','Institution','PiId','ObserverId','NightlogTicket','DelFlag','ModDate']
    params = [utdate,starttime,duration,endtime,telnr,instr,semester,projcode,institution,piid,observerid,nightlogticket,delflag,moddate]

    #if no parameters supplied, do nothing
    if not any(params):
        print("No parameters supplied, returning...")
        return

    fields = ""
    values = ""
    beginflag = 1
    #construct fields and values arrays of specified parameters
    for i,p in enumerate(params):
        #create without comma
        if p is not None and beginflag == 1:
            #add quotes if needed
            if "'" not in p:
                p = "'"+p+"'"
            fields += f"{paramname[i]}"
            values += f"{p}"
            beginflag = 0
        #create with comma
        elif p is not None and beginflag == 0:
            #add quotes if needed
            if "'" not in p:
                p = "'"+p+"'"
            fields += f",{paramname[i]}"
            values += f",{p}"
    #construct insert query with specified parameters
    query = f"insert into twilightObserving ({fields}) values ({values});"
    print(query)

    #do query
    dbquery(query)
    #print latest entry
    result = dbquery('select * from twilightObserving order by Id desc limit 1;')
    return json.dumps(result,default=jsonConverter)

def dbquery(query):
    #connect to database
    db = db_conn.db_conn('config.live.ini')
    result = db.query('keckOperations',query)
    return result


def replaceall(toreplace,replacements,fullstring):
    if fullstring is None:
        return fullstring
    if not isinstance(replacements,list):
        for i in toreplace:
            fullstring = fullstring.replace(i,replacements)
    else:
        for i,val in enumerate(toreplace):
            fullstring = fullstring.replace(val,replacements[i])
    return fullstring

#prevents times from appearing as "datetime.*" in API output
def jsonConverter(o):
    if isinstance(o,datetime.datetime):
        return o.__str__()
    elif isinstance(o,datetime.timedelta) or isinstance(o,datetime.date):
        return str(o)
