import configparser
import os

# 讀設定檔
download_folder = 'C:/temp/Singapore_Currency'
config_file = os.path.join(download_folder, 'singapore.ini')
config = configparser.ConfigParser()
config.optionxform = str  # reference: http://docs.python.org/library/configparser.html
config.read(config_file)

# 讀設定檔
exec_interval = int(config.get('system', 'exec_interval'))
log_folder = config.get('system', 'log_folder')
avail_hour = int(config.get('system', 'avail_hour'))
avail_min = int(config.get('system', 'avail_min'))

db_address = config.get('database', 'db_address')
db_tns = config.get('database', 'db_tns')
db_username = config.get('database', 'db_username')
db_password = config.get('database', 'db_password')

api_prod_url = config.get('api', 'prod_url')
api_content_type = config.get('api', 'content_type')

mail_server = config.get('mail', 'server')
mail_sender = config.get('mail', 'sender')
mail_password = config.get('mail', 'password')
mail_receiver = config.get('mail', 'receiver')


def write_ini(section, key, value):
    config.set(section, key, value)  # 要修改Key 的 Value
    config.write(open(config_file, 'w'))


def read_ini(section, key):
    return config.get(section, key)
