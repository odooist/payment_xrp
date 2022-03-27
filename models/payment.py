# -*- encoding: utf-8 -*-
import base64
import collections

from Crypto.PublicKey import RSA
try:
    from Crypto.Hash import SHA1
except ImportError:
    # Maybe it's called SHA
    from Crypto.Hash import SHA as SHA1
try:
    from Crypto.Signature import PKCS1_v1_5
except ImportError:
    # Maybe it's called pkcs1_15
    from Crypto.Signature import pkcs1_15 as PKCS1_v1_5
import json
import logging
import phpserialize
import pprint

from werkzeug import urls
from odoo import fields, models, _
from odoo.exceptions import ValidationError

try:
    from xrpl.clients import JsonRpcClient
    xrp = True
except ImportError:
    xrp = False


_logger = logging.getLogger(__name__)


class AcquirerXRP(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('xrp', 'XRP')
    ], ondelete={'xrp': 'set default'})
    xrp_vendor = fields.Char('Vendor')
    xrp_sandbox_url = fields.Char('Sandbox URL',
        default="https://s.altnet.rippletest.net:51234/")
    xrp_api_key = fields.Char('API Key')
    xrp_sandbox_api_key = fields.Char('API Key')
    xrp_title = fields.Char('Payment Title', default='Odoo products')
    xrp_public_url = fields.Char('Public URL',
        default="https://s2.ripple.com:51234/")
    xrp_sandbox_public_key = fields.Text()
    xrp_payment_logo = fields.Image('Payment Logo')

    def _get_payment_link(self, values):        
        tx = self.env['payment.transaction'].sudo().search(
            [('reference', '=', values.get('reference'))])
        if not tx:
            raise ValidationError('Cannot get tx from data!')
        # Get xrp provider to get title
        provider = self.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'xrp')])
        if not provider:
            raise ValidationError('xrp provider not found!')
        xrp = xrpClient(
            vendor_id=provider.xrp_vendor if provider.state == 'enabled' else provider.xrp_sandbox_vendor,
            api_key=provider.xrp_api_key if provider.state == 'enabled' else provider.xrp_sandbox_api_key,
            sandbox=provider.state == 'test'
        )
        # Populate custom_message with items.
        items = []
        for order in tx.sale_order_ids:
            for line in order.order_line:
                items.append(line.name)
        # Get logo URL
        logo_url = urls.url_join(
            self.get_base_url(),
            '/web/image?model=payment.acquirer&id={}'.format(provider.id) + \
            '&field=xrp_payment_logo')
        # Generate payment link from all data.
        link = xrp.create_pay_link(
            product_id=None,
            custom_message=' & '.join(items),
            customer_country=self.env['res.country'].browse(
                values.get('billing_partner_country_id')).code,
            customer_postcode=values.get('billing_partner_zip'),
            customer_email=values['billing_partner_email'],
            passthrough=json.dumps({'tx': tx.id}),
            return_url=urls.url_join(
                self.get_base_url(), values.get('return_url')),
            title=provider.xrp_title,
            webhook_url=urls.url_join(self.get_base_url(),
                                      '/payment_xrp/webhook'),
            image_url=logo_url,
            quantity=1,
            quantity_variable=0,
            marketing_consent=0,
            prices=['{}:{}'.format(tx.currency_id.name, tx.amount)]
        )
        return link['url']

    def xrp_form_generate_values(self, values):
        provider = self.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'xrp')])        
        xrp_tx_values = dict(values)
        xrp_tx_values.update({
            'pay_link': self._get_payment_link(values),
            'payment_link': '/payment_xrp/pay',
            'test_mode': provider.state == 'test',
            'vendor': provider.xrp_vendor if provider.state != 'test'
            else provider.xrp_sandbox_vendor
        })
        return xrp_tx_values


class Txxrp(models.Model):
    _inherit = 'payment.transaction'

    def _xrp_check_public_key(self, input_data, public_key):
        # Convert key from PEM to DER - Strip the first and last lines and newlines, and decode
        public_key_encoded = public_key[26:-25].replace('\n', '')
        public_key_der = base64.b64decode(public_key_encoded)

        # input_data represents all of the POST fields sent with the request
        # Get the p_signature parameter & base64 decode it.
        signature = input_data['p_signature']

        # Remove the p_signature parameter
        del input_data['p_signature']

        # Ensure all the data fields are strings
        for field in input_data:
            input_data[field] = str(input_data[field])

        # Sort the data
        sorted_data = collections.OrderedDict(sorted(input_data.items()))

        # and serialize the fields
        serialized_data = phpserialize.dumps(sorted_data)

        # verify the data
        key = RSA.importKey(public_key_der)
        digest = SHA1.new()
        digest.update(serialized_data)
        verifier = PKCS1_v1_5.new(key)
        signature = base64.b64decode(signature)
        if verifier.verify(digest, signature):
            return True
        else:
            return False

    def _xrp_order_validate(self, data):        
        provider = self.env['payment.acquirer'].sudo().search(
            [('provider', '=', 'xrp')])
        if not provider:
            raise ValidationError('xrp provider not found!')
        # Check the public key
        if not self._xrp_check_public_key(
                data,
                provider.xrp_public_key if provider.state == 'enabled'
                else provider.xrp_sandbox_public_key):
            raise ValidationError('Public key verification failed!')
        # Get the transaction
        tx = self.search([('id', '=',
                           json.loads(data.get('passthrough')).get('tx'))])
        if not tx or len(tx) > 1:
            error_msg = _(
                'Received data for reference %s') % (pprint.pformat(data))
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            raise ValidationError(error_msg)
        res = {
            'acquirer_reference': json.loads(
                data.get('passthrough')).get('tx'),
            'date': fields.Datetime.now()
        }
        tx.write(res)
        tx._set_transaction_done()
        return True
