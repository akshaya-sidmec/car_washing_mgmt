from odoo import fields,models,api

class CarWashPackage(models.Model):
    _name = 'car.wash.package'
    _description = 'Car Wash Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, string="Package Name")
    price = fields.Float(string="Package Price", compute='_compute_package_price', store=True, readonly=True)
    service_ids = fields.Many2many('car.wash.service', string="Included Services")
    discount=fields.Integer("Discount(%)",default="10")

    @api.depends('service_ids')
    def _compute_package_price(self):
        for package in self:
            total_price = 0.0
            for service in package.service_ids:
                total_price += service.price
            package.price = total_price