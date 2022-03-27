# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
# -*- encoding: utf-8 -*-
{
    'name': 'XRP Payment Acquirer',
    'version': '1.0',
    'author': 'Odooist',
    'price': 0,
    'currency': 'EUR',
    'maintainer': 'Accounting/Payment Acquirers',
    'sequence': 1000,
    'support': 'odooist@gmail.com',
    'license': 'LGPL-3',
    'category': 'Tools',
    'description': """
XRP  Acquirer for online payments
Implements the XRP Ledger API for payment acquirers.""",
    'depends': ['website', 'payment'],
    'external_dependencies': {'python': ['xrpl-py']},
    'data': [
        'views/payment_views.xml',
        'views/payment_xrp_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'demo': [],
    "qweb": ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
    'images': [],
}
