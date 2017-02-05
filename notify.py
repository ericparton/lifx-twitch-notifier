from __future__ import unicode_literals
from __future__ import print_function
from apscheduler.schedulers.background import BlockingScheduler
from urllib2 import URLError
from lifxlan import LifxLAN, PURPLE, WorkflowException
from time import sleep
import signal
import urllib2
import json
import logging.config
import logging
import urllib
import datetime
import yaml


def main():
    try:
        check_interval = config['check_interval']
        current_threshold = job.next_run_time.replace(tzinfo=None) - datetime.timedelta(seconds=check_interval)
        past_threshold = current_threshold - datetime.timedelta(seconds=check_interval)
        user_id = get_user_id()
        user_follows = get_user_follows(user_id)
        streams = get_streams()

        channel_notifications = {}

        for follow in user_follows:
            channel_notifications[follow['channel']['_id']] = follow['notifications']

        for stream in streams:
            channel = stream['channel']
            if channel_notifications[str(channel['_id'])]:
                created_at = datetime.datetime.strptime(stream['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                logging.info('{0} has been streaming since {1}'.format(channel['display_name'], created_at))
                logging.info('Comparing: {0} < {1} < {2}'.format(past_threshold, created_at, current_threshold))
                if past_threshold < created_at < current_threshold:
                    logging.info('Stream start time within thresholds. Blinking lights...')
                    blink_lights(config['blink_interval'], config['blink_cycles'])
                    return
                else:
                    logging.info('Stream start time not within thresholds. Ignoring...')
    except URLError as u:
        logging.error('Unable to retrieve information from twitch. Reason: "{0}"'.format(str(u)))
    except WorkflowException as w:
        logging.error('Unable to communicate with lights. Reason: "{0}"'.format(str(w)))


def get_headers():
    return {
        'Accept': 'application/vnd.twitchtv.v5+json',
        'Client-ID': config['client_id'],
        'Authorization': 'OAuth {0}'.format(config['oath_token'])
    }


def get_user_id():
    request = urllib2.Request(url='https://api.twitch.tv/kraken/user', headers=get_headers())
    return json.loads(urllib2.urlopen(request).read())['_id']


def get_user_follows(user_id, limit=25, offset=0):
    parameters = urllib.urlencode({'limit': limit, 'offset': offset})
    url = 'https://api.twitch.tv/kraken/users/{0}/follows/channels?{1}'.format(user_id, parameters)
    request = urllib2.Request(url=url, headers=get_headers())
    response = json.loads(urllib2.urlopen(request).read())
    follows = response['follows']

    if (offset + 1) * limit < response['_total']:
        follows = follows + get_user_follows(user_id, limit, offset=offset + limit)

    return follows


def get_streams(limit=25, offset=0):
    parameters = urllib.urlencode({'limit': limit, 'offset': offset})
    url = 'https://api.twitch.tv/kraken/streams/followed?{0}'.format(parameters)
    request = urllib2.Request(url=url, headers=get_headers())
    response = json.loads(urllib2.urlopen(request).read())
    streams = response['streams']

    if (offset + 1) * limit < response['_total']:
        streams = streams + get_streams(limit, offset=offset + limit)

    return streams


def blink_lights(interval=0.5, num_cycles=3):
    lan = LifxLAN(config['number_of_lights'])
    original_powers = lan.get_power_all_lights()
    original_colors = lan.get_color_all_lights()
    lights = lan.get_lights()

    for i in range(num_cycles):
        for light in lights:
            light.set_color(PURPLE, rapid=True)

        for light in lights:
            light.set_power("off", rapid=True)

        sleep(interval)

        for light in lights:
            light.set_power("on", rapid=True)

        sleep(interval)

    for light, color in original_colors:
        light.set_color(color, rapid=True)

    for light, power in original_powers:
        light.set_power(power != 0, rapid=True)


def shutdown(signum=None, frame=None):
    scheduler.shutdown()


config = yaml.load(file('config.yml', 'r'))

logging.config.fileConfig('logging.conf')

signal.signal(signal.SIGTERM, shutdown)

scheduler = BlockingScheduler()
job = scheduler.add_job(main, 'interval', seconds=config['check_interval'])

try:
    scheduler.start()
except KeyboardInterrupt:
    shutdown()
