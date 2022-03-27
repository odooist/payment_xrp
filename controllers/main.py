# ©️ Xrp Payments by Odooist, Odoo Proprietary License v1.0, 2021
# -*- coding: utf-8 -*-
import json
import logging
import pprint
import werkzeug

from odoo import http
from werkzeug.exceptions import BadRequest
from odoo.http import request
try:
    from xrpl.clients import JsonRpcClient
    XRP = True
except ImportError:
    XRP = False


_logger = logging.getLogger(__name__)


class XrpController(http.Controller):
    _accept_url = '/payment/xrp/feedback'

    @http.route([
        '/payment_xrp/webhook',
    ], type='http', auth='public', csrf=False, method='POST')
    def xrp_webhook(self, **post):
        try:
            request.env[
                'payment.transaction'].sudo()._xrp_order_validate(post)                
            return 'OK'
        except:
            _logger.exception('Xrp checkout error:')
            return BadRequest('Error')

    @http.route([
        '/payment_xrp/pay',
    ], type='http', auth='public', csrf=False, method='POST')
    def xrp_pay(self, **post):
        return request.render('payment_xrp.pay', post)
