
from odoo import models, fields

class CarWashCategory(models.Model):
    _name = 'car.wash.category'
    _description = 'Car Wash Service Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, string="Category Name")
    is_package = fields.Boolean(string="Is Package Category?")
    package_id = fields.Many2one('car.wash.package', string="Package")
    package_price = fields.Float(related='package_id.price', string="Package Price", readonly=True)
    service_ids = fields.Many2many('car.wash.service', related='package_id.service_ids', readonly=True)


class CarWashPackage(models.Model):
    _name = 'car.wash.package'
    _description = 'Car Wash Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, string="Package Name")
    price = fields.Float(required=True, string="Package Price")
    service_ids = fields.Many2many('car.wash.service', string="Included Services")

