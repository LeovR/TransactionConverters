#!/usr/bin/env python3
# coding: utf-8

"""
Run with
./n26.py
"""

import json
import yaml
import logging
import requests
import time
import re
from decimal import Decimal

from converter import Converter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Number26(Converter):
    """
    Implementation for Number26 bank
    """
    def __init__(self, *args, **kwargs):
        super(Number26, self).__init__(*args, **kwargs)
        with open('n26_config.yml', 'r') as yfile:
            config = yaml.load(yfile)
        self.credentials = {
            'username': config['email'],
            'password': config['password'],
            'grant_type': 'password'
        }
        del config

    def load_transactions(self):
        session = requests.Session()
        session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://my.number26.de',
            'Referer': 'https://my.number26.de/',
            'Authorization': 'Basic bXktdHJ1c3RlZC13ZHBDbGllbnQ6c2VjcmV0',
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/47.0.2526.111 Safari/537.36')
        })
        page = session.post("https://api.tech26.de/oauth/token",
                            data=self.credentials)
        del self.credentials
        if page.status_code != 200:
            raise Exception("Wrong email/password")
        logger.info('bank token aquired')

        resp = json.loads(page.text)
        session.headers.update({
            'Authorization': 'bearer %s' % resp['access_token']
        })
        del session.headers['Content-Type']
        page = session.get('https://api.tech26.de/api/smrt/transactions',
                           params={'limit': 50})
        if page.status_code != 200:
            raise Exception("Could not load transactions: %s" % page.text)
        logger.info('transactions loaded')
        resp = json.loads(page.text)
        return resp

    def convert_row(self, row):
        _timestamp = row['visibleTS'] / 1000
        _raw_payee = row.get('merchantName') or row.get('partnerName', '')
        _raw_payee = _raw_payee.strip()
        _comment = row.get('referenceText', '').strip()
        _raw_amount = row['amount']
        _category = row.get('category', '').replace('micro-', '').strip()
        _city = row.get('merchantCity', '').strip()
        date = time.strftime('%m/%d/%y', time.gmtime(_timestamp))
        payee = self.find_payee(_raw_payee, _comment, _category)
        amount = Decimal(str(_raw_amount))
        memo = "%s %s %s" % (_raw_payee, _comment, _city)
        memo = re.sub('\s+', ' ', memo).strip()
        category = ""   # let client software determine category based on payee
        ynab = {
            'Date': date,
            'Payee': payee,
            'Memo': memo,
            'Outflow': -amount if amount < 0 else '',
            'Inflow': amount if amount > 0 else '',
            'Category': category,
        }
        return ynab


if __name__ == '__main__':
    ynab_file = "export/ynab_import_n26.csv"
    converter = Number26()
    input_data = converter.load_transactions()
    ynab_data = []
    for row in input_data:
        ynab_data.append(converter.convert_row(row))
    converter.export_file(ynab_file, ynab_data)
