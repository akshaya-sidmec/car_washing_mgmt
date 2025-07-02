from odoo  import models,fields

class CarWashPaymentWizard(models.TransientModel):
    _name = 'car.wash.payment.wizard'
    _description = 'Car Wash Payment Wizard'

    # booking_id = fields.Many2one('car.wash.booking', string="Booking", required=True)
    payment_date = fields.Date(string="Payment Date")
    amount = fields.Float(string="Amount", required=True)

    def action_confirm_payment(self):
        self.ensure_one()
        booking = self.booking_id
        booking.amount_paid = self.amount
        booking.payment_date = self.payment_date
        booking.payment_state = 'paid'
        booking.message_post(body=f"Payment of {self.amount} registered on {self.payment_date}.")