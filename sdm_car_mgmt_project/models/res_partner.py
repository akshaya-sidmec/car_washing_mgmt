from odoo import models, fields, api

class InheritContacts(models.Model):
    _inherit = 'res.partner'

