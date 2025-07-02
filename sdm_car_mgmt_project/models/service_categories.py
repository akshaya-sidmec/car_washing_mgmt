from odoo import models, fields, api


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
    price = fields.Float(string="Package Price", compute='_compute_package_price', store=True, readonly=True)
    service_ids = fields.Many2many('car.wash.service', string="Included Services")

    @api.depends('service_ids')
    def _compute_package_price(self):
        for package in self:
            total_price = 0.0
            for service in package.service_ids:
                total_price += service.price
            package.price = total_price
