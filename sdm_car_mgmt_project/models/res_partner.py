from odoo import models, fields, api

class InheritHrEmployee(models.Model):
    _inherit = 'hr.employee'

class InheritContacts(models.Model):
    _inherit = 'res.partner'

    car_wash_history_ids = fields.One2many(
        'car.wash.job', 'customer_id', string="Car Wash History")
    visit_count = fields.Integer("Visit Count", default=0)

    loyalty_wallet = fields.Float("Loyalty Wallet", default=0.0)

    def action_book_car_wash(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Book Car Wash',
            'res_model': 'car.wash.booking',
            'view_mode': 'form',
            'view_id': self.env.ref('sdm_car_mgmt_project.view_car_wash_booking_form').id,
            'context': {
                'default_customer_id': self.id,
            },
            'target': 'current',
        }
