import sys, os, time
import requests
# from datetime import date, timedelta
import datetime
import calendar
import json
import cx_Oracle
import logging
import traceback
import smtplib
from email.mime.text import MIMEText

import const


# Get Singapore exchange rate via API.
# Input arguments as start and end month(format as "YYYY-MM") for searching time range.
# Return the last month updated into database, which does not neccessary equals to the input end month
# as exchange rate in end month might not available yet at the searching moment
# or the searching time range is over the maximal records, 100, that API can return in one request.
# The return value will be written in ini file for calculating next searching start month.
def call_api(s_month, e_month):
    log('==========Task Call API==========')
    headers = {"Content-Type": const.api_content_type}

    arg = "{0},{1}".format(s_month, e_month)
    data = {"resource_id": "10eafb90-11a2-4fbd-b7a7-ac15a42d60b6", "limit": "100",
            "fields": "end_of_month,usd_sgd", "between[end_of_month]": arg ,
            "sort": "end_of_month asc"}

    response = requests.get(const.api_prod_url, headers=headers, params=data, verify=False)
    if response.status_code == requests.codes.ok:
        result = response.json()  # type(result) is dict
        record_list = result["result"]["records"]
        # Check if any record exist in the given time range
        if len(record_list) > 0 :
            for i, dic in enumerate(record_list):
                month = dic["end_of_month"]
                rate = dic["usd_sgd"]
                #print(month, rate)
                # This month's exchange rate has to save in first date of next month.
                next_month_date = (datetime.datetime.strptime(month, "%Y-%m") + datetime.timedelta(days=40)).strftime("%Y%m") + "01"
                #print(next_month_date)
                insert_db(next_month_date, rate)
            return month
        else:
            log("No record between " + s_month + " and " + e_month)
            return ""

    else:
        log("[API Exception]\t" + response.text)


# Check if the date of rate has already existed in database, else insert new data row into database.
# Input arguments as date of the exchange rate(string) and the exchange rate(decimal).
def insert_db(rate_date, rate_value):
    log('==========Task Insert Database==========')
    try:
        conn = cx_Oracle.connect(const.db_username, const.db_password, const.db_address + "/" + const.db_tns)
        cur = conn.cursor()

        check = []
        cur.execute("SELECT VDATE FROM SAPSR3.ZTCURR WHERE VDATE = '{0}'".format(rate_date))
        for row in cur.fetchall():
            check.append(row)
        
        if len(check) == 0:
            insert_str = "INSERT INTO SAPSR3.ZTCURR(MANDT, KURST, FCURR, TCURR, VDATE, UKURS, FFACT, TFACT) " \
                        "VALUES('{0}', '{1}', '{2}', '{3}', '{4}', {5}, {6}, {7})".format(
                        "888", "SP", "USD", "SGD", rate_date, rate_value, 1, 1)
            cur.execute(insert_str)
            conn.commit()
        else:
            log(rate_date + " already in DB!")


    except Exception as e:
        exception_str = '[Exception]\n' + "".join(
            traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
        log(exception_str)


# Write the input argument into log file with given format.
def log(content):
    print(content)
    logging.basicConfig(filename=os.path.join(const.log_folder, datetime.datetime.now().strftime('%Y-%m-%d') + '.txt'),
                        level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s]\t%(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    logging.debug(content)  # 可以透過 logging印出


# Calculate the month difference between two date, only considering the year and month information.
# Input arguments as earlier date and later date.
def diffMonth(s_date, e_date):
    s_year = s_date.year
    e_year = e_date.year
    s_month = s_date.month
    e_month = e_date.month
    diff = (e_year - s_year) * 12 + (e_month - s_month)
    return diff


# Send email to receiver(set in ini file).
# Input arguments as email subject and email content.
def send_mail(subject, content):
    mime = MIMEText(content, "plain", "utf-8")
    mime["Subject"] = subject  # setting email subject
    mime["From"] = const.mail_sender  # setting sender
    mime["To"] = const.mail_receiver  # setting receiver
    msg = mime.as_string()  # transform to string type
    print(msg)
    smtpServer = smtplib.SMTP(const.mail_server, 25)
    smtpServer.login(const.mail_user, const.mail_password)
    status = smtpServer.sendmail(const.mail_sender, const.mail_receiver, msg)
    if status == {}:
        print("郵件傳送成功!")
    else:
        print("郵件傳送失敗!")
    smtpServer.quit()


def main():
    try:
        log('')
        log('==========Task Initial==========')
        last_update_date = datetime.datetime.strptime(const.read_ini('execution', 'singapore_currency'), "%Y-%m")
        current_date = datetime.datetime.now()
        # Next available date is every day after certain time(set in ini file).
        next_update_date = datetime.datetime(current_date.year, current_date.month, current_date.day, 
                                                const.avail_hour, const.avail_min, 0, 0)
        
        # Count how many records available for downloading.
        diff_month = diffMonth(last_update_date, current_date)
        if current_date > next_update_date:
            record = diff_month
        else:
            record = diff_month - 1

        # Call api function and update ini file.
        start_month = (last_update_date + datetime.timedelta(days=40)).strftime("%Y-%m")
        if record > 0:
            last_update_month = call_api(start_month, "9999-12")
            if len(last_update_month) > 0:
                const.write_ini('execution', 'singapore_currency', last_update_month)
        else:
            log(start_month + " currency not available yet!")

        log('==========Task Exit==========')

    except Exception as e:
        log('==========Task Exception==========')
        exception_str = '[Exception]\n' + "".join(
            traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]))
        log(exception_str)
        send_mail('[Singapore Currency] 新加坡匯率下載發生例外', exception_str)

    # Check the availability of next exchange rate once every given seconds(set in ini file).
    # Windows Service will start the program once it detect the program ends.
    finally:
        log('==========Task Wait==========')
        time.sleep(const.exec_interval)
        log('==========Task Exit==========')
        sys.exit(0)




if __name__ == '__main__':
    main()
