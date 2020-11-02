import datetime as dt
import pandas as pd
import time
import asyncio
import yaml
import random

from concurrent.futures import ThreadPoolExecutor
from session import VevenSession
from box import Box
from typing import Dict


async def mass_get_cookies(credentials: Dict[str, str], event_url):
    sessions = {}
    for un, pw in credentials.items():
        print('\nUser:', un)
        Session = VevenSession(
            event_url=event_url,
            username=un, password=pw
        )
        await Session.get_cookies()
        sessions[un] = Session
    return sessions


def threaded_timed_mass_register(trigger, session_list):
    while dt.datetime.now() < trigger:
        time.sleep(0.001)
    
    print('\nStarting registers. Time:', dt.datetime.now())
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=len(session_list)) as exec:
        responses = list(exec.map(
            lambda session: session.register(), session_list
        ))
    print('%.5fs elapsed' % (time.time() - t0))
    return responses


if __name__ == '__main__':
    with open("assets/config.yml", "r") as ymlfile:
        cfg = Box(yaml.safe_load(ymlfile))
    
    # Get cookies
    creds = dict(cfg.users)
    loop = asyncio.get_event_loop()
    sessions = loop.run_until_complete(mass_get_cookies(creds, cfg.event_url))
    loop.close()
    
    # Register all users cfg.attempts times
    session_list = list(sessions.values()) * cfg.attempts
    random.shuffle(session_list)
    trigger = pd.to_datetime(cfg.trigger, format='%Y-%m-%d %H:%M')
    responses = threaded_timed_mass_register(trigger, session_list)
    print('status codes:', [r.status_code for r in responses])
