#!/usr/bin/env python3
# coding: utf-8

import csv
import logging
import re
from collections import OrderedDict

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Converter(object):
    """
    Base class for bank transactions processing
    """

    def ordered_load(self, stream, loader=yaml.Loader, object_pairs_hook=OrderedDict):
        class OrderedLoader(loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        return yaml.load(stream, OrderedLoader)

    def __init__(self):
        with open('public_payees.yml', 'r', encoding='UTF-8') as yfile:
            # self.payees = yaml.load(yfile)
            self.payees = self.ordered_load(yfile)
        try:
            with open('private_payees.yml', 'r', encoding='UTF-8') as yfile:
                private_payees = self.ordered_load(yfile)
                if private_payees is None:
                    logger.info('private_payees.yml is empty')
                else:
                    new_payees = OrderedDict()
                    for key in private_payees.keys():
                        new_payees[key] = private_payees[key]
                    for key in self.payees.keys():
                        if key not in new_payees:
                            new_payees[key] = self.payees[key]
                    self.payees = new_payees
        except IOError:
            logger.info('Could not open private_payees.yml')

    def find_payee(self, *sources):
        """exctract matching payee name from lise of sources"""
        for payee, match in self.payees.items():
            if isinstance(match, str):
                # first check startswith
                if [source for source in sources if source.lower().startswith(match.lower())]:
                    return payee
            elif 'regex' in match and match['regex']:
                if [source for source in sources if re.match(match['value'], source)]:
                    return payee
            elif 'values' in match:
                for sub_match in match['values']:
                    if [source for source in sources if source.lower().startswith(sub_match.lower())]:
                        return payee
        for payee, match in self.payees.items():
            if isinstance(match, str):
                # then check contains
                if [source for source in sources if match.lower() in source.lower()]:
                    return payee
            elif 'values' in match:
                for sub_match in match['values']:
                    if [source for source in sources if sub_match.lower() in source.lower()]:
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
