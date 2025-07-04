from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WasherJobInvoice(models.Model):
    _inherit = 'account.move'

    washer_job_id = fields.Many2one('car.wash.job', string='Washer Job')


class CarWashJob(models.Model):
    _inherit = 'car.wash.job'

    def action_mark_paid(self):
        self.ensure_one()

        if not self.customer_id or not self.total_price:
            raise ValidationError(_("Missing customer or total price."))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_origin': self.booking_id.invoice_number or '/',
            'invoice_line_ids': [(0, 0, {
                'name': f'Car Wash - {self.booking_id.invoice_number or "No Ref"}',
                'quantity': 1,
                'price_unit': self.total_price,
            })],
        })

        invoice.washer_job_id = self.id
        self.invoice_number = invoice.name
        self.state = 'paid'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def action_view_job_invoices(self):
        """Smart button to view related invoices"""
        self.ensure_one()
        return {
            'name': _('Invoices for Job'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('washer_job_id', '=', self.id)],
            'context': {'default_washer_job_id': self.id},
        }
