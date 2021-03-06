# -*- coding: utf-8 -*-
""""""

from __future__ import unicode_literals

# Standard library imports
import json
import os

# Third party imports
from jinja2 import Undefined
from lektor.project import Project
from meetup.api import Client
import requests


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT_PATH = os.path.dirname(HERE)


def load_api_key(name):
    """"""
    API_KEY = os.environ.get(name, None)

    if API_KEY is None:
        fpaths = [
            os.path.join(PROJECT_ROOT_PATH, name),
            os.path.join(PROJECT_ROOT_PATH, '.' + name),
            os.path.join(HERE, name),
            os.path.join(HERE, '.' + name),
        ]
        for fpath in fpaths:
            try:
                with open(fpath, 'r') as fh:
                    API_KEY = fh.read().strip()
                break
            except Exception:
                pass

    return API_KEY


def get_meetup_groups():
    """
    Loads meetup groups from the Python Colombia lektor database.

    This returns only communities that are displayed on the map.
    """
    project = Project.discover()
    env = project.make_env()
    pad = env.new_pad()
    groups = [g for g in pad.query('/usuarios/') if g['type'] == 'comunidad'
              and g['map'] and not isinstance(g['meetup_handle'], Undefined)]
    groups = {g['meetup_handle']: g['username'] for g in groups}
    return groups


class MeetupClient(Client):
    """"""

    def __init__(self, API_KEY):
        """"""
        super(MeetupClient, self).__init__(API_KEY)
        self._api_key = API_KEY
        self._payload = {'key': API_KEY}

    def get_group_events(self, group_name, status='draft'):
        """
        See: https://blog.samat.org/2015/10/23/Getting-All-Past-Meetup-Events/
        """
        group_events = []
        payload = self._payload.copy()
        payload.update({
            'status': [status],
            'page': 200,
            'group_urlname': group_name,
        })
        # Above is the equivalent of jQuery.extend()
        # for Python 3.5: payload = {**default_payload, **offset_payload}
        r = requests.get('https://api.meetup.com/{}/events'.format(group_name),
                         params=payload)
        json = r.json()
        events = json
        if isinstance(json, dict):
            # print([json])
            codes = json['errors']
            errors = [code['code'] for code in codes]
            if 'authorization_error' in errors:
                # print(codes)p
                events = []

        for event in events:
            # print([event])
            check = event.get('local_date', 0)
            if check != 0:
                group_events.append(event)

        return group_events

    def get_events(self, group_name=None):
        """"""
        grouped_events = []
        groups = [group_name] if group_name else self.GROUPS
        for group in groups:
            # draft_events = self.get_group_events(group, 'draft')
            upcoming_events = self.get_group_events(group, 'upcoming')
            # cancelled_events = self.group_events(group, 'cancelled')
            proposed_events = self.get_group_events(group, 'proposed')
            suggested_events = self.get_group_events(group, 'suggested')
            past_events = self.get_group_events(group, 'past')
            events = (upcoming_events + past_events
                      + proposed_events + suggested_events)
            events = sorted(events, key=lambda g: g['local_date'],
                            reverse=True)

            for event in events:
                grouped_events.append(event)

        return grouped_events

    def group_members(self, group_name):
        """"""
        offset = 0
        all_data = []
        while True:
            data = self.GetMembers(group_urlname=group_name, offset=offset)
            if data.results:
                all_data.extend(data.results)
                offset += 1
            else:
                break

        return all_data

    def save_data(self, fpath, data):
        """"""
        path = os.path.dirname(fpath)
        if not os.path.isdir(path):
            os.makedirs(path)

        with open(fpath, 'w') as fh:
            fh.write(json.dumps(data, sort_keys=True, indent=2,
                                separators=(',', ': ')))


def main():
    meetup_client = MeetupClient(load_api_key('MEETUP_API_KEY'))
    groups = get_meetup_groups()
    print('Downloading data from Meetup API...:')
    for group in groups:
        print('\n')
        print(group)
        members = meetup_client.group_members(group)
        members = [m for m in members if m.get('joined')]
        members = sorted(members, key=lambda g: g['joined'])
        meetup_client.save_data(os.path.join(HERE, '.MEETUP_DATA', 'members',
                                             group + '.json'), members)
        events = meetup_client.get_events(group)
        meetup_client.save_data(os.path.join(HERE, '.MEETUP_DATA', 'events',
                                             group + '.json'), events)


if __name__ == '__main__':
    main()
