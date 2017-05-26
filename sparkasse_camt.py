#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import re
import time
from zipfile import ZipFile

from lxml import etree

from converter import Converter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SparkasseCamt(Converter):
    """
    Implementation of Sparkasse bank with CAMT 052 file format
    """
    ns = None

    def __init__(self, *args, **kwargs):
        super(SparkasseCamt, self).__init__(*args, **kwargs)

    def load_transactions(self, folder, processed_folder):
        entries = []
        for filename in os.listdir(folder):
            if filename.lower().endswith('.zip'):
                with ZipFile(folder + filename) as zip:
                    for name in zip.namelist():
                        with zip.open(name) as f:
                            camt = self._check_camt(f)
                            if camt is not None:
                                self.ns = camt.tag[1:camt.tag.index("}")]
                                entries.extend(camt.xpath('//ns:Rpt/ns:Ntry', namespaces={'ns': self.ns}))
                os.rename(folder + filename, processed_folder + filename)
        return entries

    def _check_camt(self, data_file):
        try:
            root = etree.parse(
                data_file, parser=etree.XMLParser(recover=True)).getroot()
            ns = root.tag
            if not ns.startswith('{urn:iso:std:iso:20022:tech:xsd:camt.'):
                return None
        except:
            return None
        return root

    def convert_entry(self, entry):
        date = entry.xpath('./ns:BookgDt/ns:Dt/text()', namespaces={'ns': self.ns})[0]
        timestamp = time.strptime(date, "%Y-%m-%d")
        date = time.strftime('%m/%d/%y', timestamp)

        amount = float(entry.xpath('./ns:Amt/text()', namespaces={'ns': self.ns})[0])

        debt_indicator = entry.xpath('./ns:CdtDbtInd/text()', namespaces={'ns': self.ns})[0]
        debit = False
        if debt_indicator == 'DBIT':
            debit = True
            amount *= -1

        creditor = ''
        debitor = ''
        related_parties = entry.xpath('./ns:NtryDtls/ns:TxDtls/ns:RltdPties', namespaces={'ns': self.ns})[0]
        debitor_nodes = related_parties.xpath('./ns:Dbtr/ns:Nm/text()', namespaces={'ns': self.ns})
        if debitor_nodes:
            debitor = debitor_nodes[0]
        creditor_notes = related_parties.xpath('./ns:Cdtr/ns:Nm/text()', namespaces={'ns': self.ns})
        if creditor_notes:
            creditor = creditor_notes[0]
        raw_payee = creditor if debit else debitor

        creditor_agent = ''
        debitor_agent = ''
        related_agents = entry.xpath('./ns:NtryDtls/ns:TxDtls/ns:RltdAgts', namespaces={'ns': self.ns})[0]
        debitor_nodes = related_agents.xpath('./ns:DbtrAgt/ns:FinInstnId/ns:Nm/text()', namespaces={'ns': self.ns})
        if debitor_nodes:
            debitor_agent = debitor_nodes[0]
        creditor_notes = related_agents.xpath('./ns:CdtrAgt/ns:FinInstnId/ns:Nm/text()', namespaces={'ns': self.ns})
        if creditor_notes:
            creditor_agent = creditor_notes[0]
        agent = creditor_agent if debit else debitor_agent

        ultimate_creditor = ''
        ultimate_debitor = ''
        ultimate_debitor_nodes = related_parties.xpath('./ns:UltmtCdtr/ns:Nm/text()', namespaces={'ns': self.ns})
        if ultimate_debitor_nodes:
            ultimate_debitor = ultimate_debitor_nodes[0]
        ultimate_creditor_notes = related_parties.xpath('./ns:UltmtDbtr/ns:Nm/text()', namespaces={'ns': self.ns})
        if ultimate_creditor_notes:
            ultimate_creditor = ultimate_creditor_notes[0]
        ultimate_payee = ultimate_debitor if debit else ultimate_creditor

        mandate_id = ''
        mandate_id_nodes = entry.xpath('./ns:NtryDtls/ns:TxDtls/ns:Refs/ns:MndtId/text()', namespaces={'ns': self.ns})
        if mandate_id_nodes:
            mandate_id = mandate_id_nodes[0]

        payee = self.find_payee(raw_payee, agent, ultimate_payee, mandate_id)

        remittance_info = next(
            iter(entry.xpath('./ns:NtryDtls/ns:TxDtls/ns:RmtInf/ns:Ustrd/text()', namespaces={'ns': self.ns})), '')

        additional_info = next(iter(entry.xpath('./ns:AddtlNtryInf/text()', namespaces={'ns': self.ns})), '')

        memo = "%s %s" % (remittance_info, additional_info)
        memo = re.sub('\s+', ' ', memo).strip()

        ynab = {
            'Date': date,
            'Payee': payee,
            'Memo': memo,
            'Outflow': -amount if amount < 0 else '',
            'Inflow': amount if amount > 0 else '',
            'Category': '',
        }
        return ynab


if __name__ == '__main__':
    ynab_file = "export/ynab_data_sparkasse.csv"
    converter = SparkasseCamt()
    input_data = converter.load_transactions('import/sparkasse/', 'processed/sparkasse/')
    ynab_data = []
    for row in input_data:
        ynab_data.append(converter.convert_entry(row))
    converter.export_file(ynab_file, ynab_data)
