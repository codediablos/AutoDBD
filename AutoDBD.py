# -*- coding: utf-8 -*-
#!/usr/bin/python

import os, sys, urllib, urllib2, cookielib, time, datetime, random
import optparse
import ConfigParser
import bs4 as BeautifulSoup
import getpass
from daemon import Daemon

# print result
# import re
# pat = re.compile('Title:.*')
# print pat.search(content).group()

GENERAL_PROJECT = ['445', '447', '448', '449', '450', '451', '832']

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

    MSG_USAGE = "AutoDBD [ --undbd]"

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
        self.options, self.args = self.parser.parse_args(argv)

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
        today = datetime.datetime.today()
        start = datetime.time(15, 0)
        if today.weekday() == 4 and \
                today.time().hour == start.hour and \
                today.time().minute == start.minute or \
                self.options.debug:

            self.kimia_login()
            self.fill_task()

    def kimia_login(self):
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

    def fill_task(self):
        str_projects = self.get_config().get('core', 'random_project').split(',')
        str_states = self.get_config().get('core', 'random_state').split(',')
        durations = self.get_config().get('core', 'random_duration').split(',')
        projects = []
        states = []

        project_conf = ConfigParser.SafeConfigParser()
        project_conf.read(self.project_file)
        state_conf = ConfigParser.SafeConfigParser()
        state_conf.read(self.state_file)

        for project in str_projects:
            if project_conf.has_option('project', project):
                projects.append(project_conf.get('project', project))

        for state in str_states:
            if state_conf.has_option('state', state):
                states.append(state_conf.get('state', state))

        tasks = []
        today = datetime.datetime.today()
        for i in xrange(5):
            add_day = today + datetime.timedelta(-i, 0)
            tasks.append([add_day.strftime('%Y.%m.%d'),
                          random.choice(durations),
                          random.choice(projects),
                          random.choice(states)])

        for task in tasks:
            if task[3] in GENERAL_PROJECT:
                task[2] = project_conf.get('project', 'General')

            values = dict(axAction='add_edit_record',
                          comment='',
                          comment_type='0',
                          edit_in_day=task[0],
                          edit_in_time='00:00:00',
                          edit_out_time='17:24:14',
                          edit_out_day=task[0],
                          edit_duration=task[1],
                          pct_ID=task[2],
                          evt_ID=task[3],
                          filter='',
                          id='0',
                          rate='',
                          trackingnr='',
                          zlocation='')

            data = urllib.urlencode(values)
            req = urllib2.Request(self.kimai_processor_url, data)
            rsp = urllib2.urlopen(req)

        if self.options.debug:
            print tasks

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
        if html.find("alert_food") != -1:
            return

        print 'login.................'
        empid_cfg = self.get_config().get('core', 'empid')
        pwd_cfg = self.get_config().get('core', 'pwd')

        values = dict(authenticity_token=self.authtok, empid=empid_cfg, pwd=pwd_cfg)
        print values
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

        if html.find("alert_cancel") != -1:
            return True

        return False

    def dbd(self):
        print 'dbd...................'

        location_cfg = self.get_config().get('core', 'location')
        food_cfg = self.get_config().get('core', 'food')

        req = urllib2.Request(self.dbd_select_url)
        rsp = urllib2.urlopen(req)
        html = rsp.read()

        soup = BeautifulSoup.BeautifulSoup(html)

        foods = soup.findAll('input', attrs={'name':'food'})
        locations = soup.findAll('option')

#        print foods

        if len(foods) < 1:
            return ""

        values = dict(authenticity_token=self.authtok, food=foods[int(food_cfg)]['value'], location=location_cfg, save_item=u'我也要訂 !!')

        data = urllib.urlencode(values)
        req = urllib2.Request(self.dbd_select_submit_url, data)
        rsp = urllib2.urlopen(req)
        html = rsp.read()

    def undbd(self):
        self.login()

        print 'undbd.................'

        req = urllib2.Request(self.dbd_check_url)
        rsp = urllib2.urlopen(req)
        html = rsp.read()

        # do POST
        soup = BeautifulSoup.BeautifulSoup(html)
        # authtok = soup.find('input', attrs={'name':'authenticity_token'})['value']
        order = soup.find('input', attrs={'name':'order_id'})
        if order == None:
            print 'Un-DBD Failed'
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
        elif daemon.options.debug:
            daemon.run()
        else:
            if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
            else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)
