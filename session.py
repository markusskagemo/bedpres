import requests as r
import subprocess
import asyncio
import yaml
import pickle
import json
import time
import os

from pyppeteer import launch
from box import Box
from typing import Dict, List


class VevenSession(object):
    def __init__(self, event_url, username, password, cookies=None):
        with open("assets/config.yml", "r") as ymlfile:
            self.config = Box(yaml.safe_load(ymlfile))
            
        self.event_url = event_url
        self.username = username
        self.password = password
        self.cookies = cookies
    
    @staticmethod
    def _parse_cookies(cookies: List[Dict[str, str]]) -> str:
        """Parse cookies from webdriver to servers' approved format."""
        if cookies is None:
            print('Cookies is None.')
            return
        
        parsed_cookies = ""
        for cookie in cookies:
            for key, val in cookie.items():
                if key == 'name':
                    parsed_cookies += '%s=' % val
                elif key == 'value':
                    parsed_cookies += '%s; ' % val
                    break
        return parsed_cookies
    
    async def _get_veven_cookies(self) -> Dict[str, str]:
        browser = await launch(headless=True)
        page = await browser.newPage()

        # Login page
        await page.goto('https://omega.ntnu.no/user/login')
        await page.waitForSelector('input')
        await page.type('input', self.username)
        await page.type('div:nth-child(2) > input', self.password)
        await page.keyboard.press('Enter')

        # Use navbar on main page to get all cookies
        await page.waitForSelector('li:nth-child(2) > a')
        await page.click('li:nth-child(2) > a')
        time.sleep(1)
        
        cookies = await page.cookies()
        await browser.close()
        
        print('New cookies fetched.')
        return cookies
    
    def _valid_cookies(self) -> bool:
        """Send mock request to assert status code 200."""
        if self.cookies is None:
            return False
        
        headers = {
            'User-Agent': self.config.user_agent,
            'Cookie': self.cookies
        }
        response = r.get('https://omega.ntnu.no/api/user/user', headers=headers)
        valid = response.status_code == 200
        print('Valid cookies:', valid)
        return valid
        
    async def get_cookies(self) -> None:
        if self.cookies is None:
            print('Fetching new cookies with webdriver.')
            self.cookies = await self._get_veven_cookies()
            self.cookies = self._parse_cookies(self.cookies)
            self._valid_cookies() # Check
        else:
            # Check validity of currently loaded cookies
            if not self._valid_cookies():
                print('Cookies are invalid. Fetching new ones.')
                cookies = await self._get_veven_cookies()
                self.cookies = self._parse_cookies(self.cookies)
    
    def register(self):
        if self.cookies is None:
            print('No cookies. Register failed.')
            return False

        headers = {
            'Host': 'omega.ntnu.no',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': self.config.user_agent,
            'Content-Type': 'application/json',
            'Origin': 'https://omega.ntnu.no',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': self.event_url,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,nb-NO;q=0.8,nb;q=0.7,no;q=0.6,nn;q=0.5',
            'Cookie': self.cookies
        }
        data = {
            'EventId': self.event_url.split('/')[-1],
            'company': False
        }
        return r.post('https://omega.ntnu.no/api/events/register', headers=headers, data=json.dumps(data))