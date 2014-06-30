# -*- coding: utf-8 -*-
#!/usr/bin/python

import os, sys, urllib, urllib2, cookielib, time, datetime, random
import optparse
import ConfigParser
import bs4 as BeautifulSoup
import getpass
import gspread
import logging
from daemon import Daemon

# print result
# import re
# pat = re.compile('Title:.*')
# print pat.search(content).group()

GENERAL_STATE = ['445', '447', '448', '449', '450', '451', '832']

class DbdDaemon(Daemon):
	dbd_login_url = 'http://woodstock.acer.com.tw/dbd/'
	dbd_logout_url = 'http://woodstock.acer.com.tw/dbd/welcome/logout'
	dbd_select_url = 'http://woodstock.acer.com.tw/dbd/order/select'
	dbd_select_submit_url = 'http://woodstock.acer.com.tw/dbd/order/select_submit'
	dbd_select_cancel_url = 'http://woodstock.acer.com.tw/dbd/order/select_cancel'
	dbd_check_url = 'http://woodstock.acer.com.tw/dbd/order/select'

	kimai_login_url = 'http://woodstock.acer.com.tw/kimai/index.php?a=checklogin'
	kimai_processor_url = 'http://woodstock.acer.com.tw/kimai/extensions/ki_timesheets/processor.php'

	HOME_DIR = os.environ['HOME']
	config_file = HOME_DIR + '/.AutoDBD.conf'
	project_file = HOME_DIR + '/AutoDBD/project_list'
	state_file = HOME_DIR + '/AutoDBD/state_list'
	project_state_file = HOME_DIR + '/.project_state'
	log_file = HOME_DIR + '/.AutoDBD.log'

	temp_send_file = '/tmp/sendmail.txt'

	project_state = {}

	logger = logging.getLogger('AutoDBD')

	MSG_USAGE = "AutoDBD [ --undbd]"

	google_col_size = 3
	retry_interval = 60
	check_interval = 60
	authtok = ''

	def __init__(self, pidfile, argv):
		Daemon.__init__(self, pidfile)

		reload(sys)
		sys.setdefaultencoding('utf-8')
		# acquire cookie
		cookie_jar = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
		urllib2.install_opener(opener)

		self.parser = optparse.OptionParser(self.MSG_USAGE)
		self.parser.add_option('-u', '--undbd', action='store_true', dest='undbd', help="Un-DBD",default=False)
		self.parser.add_option('-i', '--input', action='store_true', dest='input', help="Input name & password",default=False)
		self.parser.add_option('-t', '--time', action='store_true', dest='time', help="Auto time card",default=False)
		self.parser.add_option('-g', '--debug', action='store_true', dest='debug', help="for debug",default=False)
		self.parser.add_option('--sync', action='store_true', dest='sync', help="Sync data with server",default=False)
		self.parser.add_option('--local', action='store_true', dest='local', help="Not sync with server",default=False)
		self.parser.add_option('--nodaemon', action='store_true', dest='nodaemon', help="Start with no-daemon",default=False)
		self.options, self.args = self.parser.parse_args(argv)

		hdlr = logging.FileHandler(self.log_file)
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		hdlr.setFormatter(formatter)
		self.logger.addHandler(hdlr)
		self.logger.setLevel(logging.INFO)

	def get_config(self):
		config = ConfigParser.SafeConfigParser()
		config.read(self.config_file)

		return config

	def set_days(self):
		self.days = []
		str_days = self.get_config().get('core', 'days').split(',')
		for day in str_days:
			self.days.append(int(day) - 1)

	def set_time(self):
		day_time = self.get_config().get('core', 'time').split(':')
		self.time = datetime.time(int(day_time[0]), int(day_time[1]))

	def run(self):
		while True:
			if self.get_config().get('core', 'dbd') == 'y':
				self.auto_dbd_system()
			if self.get_config().get('core', 'timecard') == 'y':
				self.auto_time_card();

			time.sleep(self.check_interval)

	def auto_time_card(self):
		day_time = self.get_config().get('core', 'start_time').split(':')
		today = datetime.datetime.today()
		start = datetime.time(int(day_time[0]), int(day_time[1]))

		if (today.time().hour == start.hour and \
			today.time().minute == start.minute) or self.options.debug:
			if not self.options.local:
				self.get_data_form_server()
			self.get_data_form_local()

			if self.kimia_login():
				self.fill_task()
				self.send_mail()

	def kimia_login(self):
		self.logger.info('kimia_login')
		name_cfg = ''
		pwd_cfg = ''

		if daemon.options.input:
			print 'Input Account: '
			name_cfg = raw_input()
			print 'Input Password: '
			pwd_cfg = getpass.getpass()
		else:
			name_cfg = self.get_config().get('core', 'name')
			pwd_cfg = self.get_config().get('core', 'pwd')

		values = dict(name=name_cfg, password=pwd_cfg)
		data = urllib.urlencode(values)
		req = urllib2.Request(self.kimai_login_url, data)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

		if not html.find('Access denied!') == -1:
			self.logger.error('kimia login fail')
			return False
		else:
			self.logger.info('kimia login success')

		return True

	def send_mail(self):
		if self.get_config().has_option('core', 'mail_list'):
			mail_list = self.get_config().get('core', 'mail_list')
			os.system("tac " + self.log_file + " > " + self.temp_send_file)
			os.system("sendmail " + mail_list + " < " + self.temp_send_file)

	def is_holiday(self, holidays):
		today = datetime.datetime.today()
		#Sun & Sat
		if today.weekday() == 5 or today.weekday() == 6:
			return True

		for oneday in holidays:
			date = oneday.split('.')
			if len(date) == 2:
				if int(date[0]) == today.month and int(date[1]) == today.day:
					return True

		return False

	def write_list(self, f, _list):
		for id in _list:
			f.write(id + ':')
		f.seek(f.tell() - 1)
		f.write('\n')

	def get_data_form_server(self):
		try:
			gc = gspread.login('codediablos.guest@gmail.com', 'acer123456')
			sh = gc.open_by_key('0AkLncPMATEhwdGRjejdRcEhFazNTc0plZ3dpb0twTmc')
			worksheet = sh.worksheet("State")

			id_list = worksheet.row_values(worksheet.find("ProjectID").row)[1:]
			project_list = worksheet.row_values(worksheet.find("Project").row)[1:]
			state_list = worksheet.row_values(worksheet.find("State").row)[1:]

			f = open(self.project_state_file, 'w')
			self.write_list(f, id_list)
			self.write_list(f, project_list)
			self.write_list(f, state_list)
			f.close()

		except Exception:
			self.logger.error('Get google drive error!')

	def get_data_form_local(self):
		f = open(self.project_state_file, 'r')
		lines = f.readlines()
		f.close()

		if len(lines) >= self.google_col_size:
			ids = lines[0].replace('\n', '').replace(' ', '').split(':')
			projects = lines[1].replace('\n', '').replace(' ', '').split(':')
			states = lines[2].replace('\n', '').replace(' ', '').split(':')

			if len(projects) == len(states) and len(states) == len(ids):
				for i in xrange(len(projects)):
					self.project_state[projects[i]] = (ids[i], states[i])
			else:
				self.logger.error('Local data format error!')
		else:
			self.logger.error('Get local data format error!')

	def get_project_index_by_name(self, name):
		for i in xrange(len(self.projects)):
			self.projects

	def fill_task(self):
		str_projects = self.get_config().get('core', 'random_project').split(',')
#		str_states = self.get_config().get('core', 'random_state').split(',')
		durations = self.get_config().get('core', 'random_duration').split(',')
		holiday_list = self.get_config().get('core', 'holiday_list').split(',')
#		projects = []
#		states = []

		if self.is_holiday(holiday_list):
			self.logger.info('Today is in holiday list')
			return

		project_conf = ConfigParser.SafeConfigParser()
		project_conf.read(self.project_file)
		state_conf = ConfigParser.SafeConfigParser()
		state_conf.read(self.state_file)

#		for project in str_projects:
#			if project_conf.has_option('project', project):
#				projects.append(project_conf.get('project', project))

#		for state in str_states:
#			if state_conf.has_option('state', state):
#				states.append(state_conf.get('state', state))

		today = datetime.datetime.today()

		project_name = random.choice(str_projects)

		# default using General-SurveyandStudy to filled
		project_index = project_conf.get('project', 'General')
		state_index = state_conf.get('state', 'SurveyandStudy')

		if project_name in self.project_state:
			project_index, state_name = self.project_state[project_name]
			if state_conf.has_option('state', state_name):
				state_index = state_conf.get('state', state_name)
			else:
				state_index = state_conf.get('state', 'Maintenance')
		else:
#			if state_index in GENERAL_STATE:
			project_index = project_conf.get('project', 'General')
			# For general task, using project_name replace state_name
			state_index = state_conf.get('state', project_name)

		values = dict(axAction='add_edit_record',
						comment='',
						comment_type='0',
						edit_in_day=today.strftime('%Y.%m.%d'),
						edit_in_time='00:00:00',
						edit_out_time='17:24:14',
						edit_out_day=today.strftime('%Y.%m.%d'),
						edit_duration=random.choice(durations),
						pct_ID=project_index,
						evt_ID=state_index,
						filter='',
						id='0',
						rate='',
						trackingnr='',
						zlocation='')

		data = urllib.urlencode(values)
		req = urllib2.Request(self.kimai_processor_url, data)
		rsp = urllib2.urlopen(req)

		self.logger.info('Fill task done! - ' + str([project_index, state_index]))

		if self.options.debug:
			print (project_index, state_index)

	def auto_dbd_system(self):
		self.set_days()
		self.set_time()

		today = datetime.datetime.today()
		if today.weekday() in self.days and \
			today.time().hour == self.time.hour and \
			today.time().minute == self.time.minute:
			self.login()

			while not self.is_done():
				self.dbd()
				time.sleep(self.retry_interval)

			print self.is_done()
		else:
			print 'Not DBD'

	def login(self):
		req = urllib2.Request(self.dbd_login_url)
		rsp = urllib2.urlopen(req)
		html = rsp.read()
		soup = BeautifulSoup.BeautifulSoup(html)
		self.authtok = soup.find('input', attrs={'name':'authenticity_token'})['value']

		# already login
		if not html.find("alert_food") == -1:
			return

		self.logger.info('login.................')
		empid_cfg = self.get_config().get('core', 'empid')
		pwd_cfg = self.get_config().get('core', 'pwd')

		values = dict(authenticity_token=self.authtok, empid=empid_cfg, pwd=pwd_cfg)
		self.logger.info(values)
		data = urllib.urlencode(values)
		req = urllib2.Request(self.dbd_login_url, data)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

	def logout(self):
		req = urllib2.Request(self.dbd_logout_url)
		rsp = urllib2.urlopen(req)

	def is_done(self):
		req = urllib2.Request(self.dbd_check_url)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

		if not html.find("alert_cancel") == -1:
			return True

		return False

	def dbd(self):
		self.logger.info('dbd...................')

		location_cfg = self.get_config().get('core', 'location')
		food_cfg = self.get_config().get('core', 'food')

		req = urllib2.Request(self.dbd_select_url)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

		soup = BeautifulSoup.BeautifulSoup(html)

		foods = soup.findAll('input', attrs={'name':'food'})
		locations = soup.findAll('option')

#		 print foods

		if len(foods) < 1:
			return ""

		values = dict(authenticity_token=self.authtok, food=foods[int(food_cfg)]['value'], location=location_cfg, save_item=u'我也要訂 !!')

		data = urllib.urlencode(values)
		req = urllib2.Request(self.dbd_select_submit_url, data)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

	def undbd(self):
		self.login()

		self.logger.info('undbd.................')

		req = urllib2.Request(self.dbd_check_url)
		rsp = urllib2.urlopen(req)
		html = rsp.read()

		# do POST
		soup = BeautifulSoup.BeautifulSoup(html)
		# authtok = soup.find('input', attrs={'name':'authenticity_token'})['value']
		order = soup.find('input', attrs={'name':'order_id'})
		if order == None:
			self.logger.error('Un-DBD Failed')
			return

		values = dict(authenticity_token=self.authtok, cancel_item=u'我要取消', order_id=order['value'])
		data = urllib.urlencode(values)
		req = urllib2.Request(self.dbd_select_cancel_url, data)
		rsp = urllib2.urlopen(req)
		html = rsp.read()


if __name__ == "__main__":
	daemon = DbdDaemon('/tmp/audo_dbd_daemon.pid', sys.argv)
	if daemon.options.undbd:
		daemon.undbd()
	elif daemon.options.time:
		daemon.auto_time_card()
	elif daemon.options.nodaemon:
		daemon.run()
	elif daemon.options.sync:
		daemon.get_data_form_server()
	else:
		if 'start' in daemon.args:
			daemon.start()
		elif 'stop' in daemon.args:
			daemon.stop()
		elif 'restart' in daemon.args:
			daemon.restart()
		else:
			print "usage: %s start|stop|restart" % sys.argv[0]
			sys.exit(2)

		sys.exit(0)
