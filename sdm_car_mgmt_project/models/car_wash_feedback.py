from odoo import models, fields

class CarWashFeedback(models.Model):
    _name = 'car.wash.feedback'
    _description = 'Customer Feedback'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    booking_id = fields.Many2one('car.wash.booking', string='Booking')
    rating = fields.Selection([('1', '★☆☆☆☆'), ('2', '★★☆☆☆'), ('3', '★★★☆☆'),
                               ('4', '★★★★☆'), ('5', '★★★★★')], string='Rating', required=True)
    feedback = fields.Text('Feedback')


