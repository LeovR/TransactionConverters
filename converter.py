#!/usr/bin/env python3
# coding: utf-8

import csv
import logging

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Converter(object):
    """
    Base class for bank transactions processing
    """

    def __init__(self):
        with open('public_payees.yml', 'r', encoding='UTF-8') as yfile:
            self.payees = yaml.load(yfile)
        try:
            with open('private_payees.yml', 'r', encoding='UTF-8') as yfile:
                yaml_loaded = yaml.load(yfile)
                if yaml_loaded is None:
                    logger.info('private_payees.yml is empty')
                else:
                    self.payees.update(yaml_loaded)
        except IOError:
            logger.info('Could not open private_payees.yml')

    def find_payee(self, *sources):
        """exctract matching payee name from lise of sources"""
        for match, payee in self.payees.items():
            # first check startswith
            if [source for source in sources if source.lower().startswith(match.lower())]:
                return payee
        for match, payee in self.payees.items():
            # then check contains
            if [source for source in sources if match.lower() in source.lower()]:
                return payee
        return next((source for source in sources if source), sources[0])

    def export_file(self, filename, data):
        with open(filename, 'w', encoding='UTF-8') as csvfile:
            fieldnames = ['Date', 'Payee', 'Category', 'Memo', 'Outflow',
                          'Inflow']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
