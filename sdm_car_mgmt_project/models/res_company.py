from odoo import models, fields, api

class InheritHrEmployee(models.Model):
    _inherit = 'res.company'
