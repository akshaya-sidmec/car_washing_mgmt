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

        # If invoice already exists (from booking), use it
        invoice = self.booking_id.invoice_id
        if not invoice:
            all_services = self.service_ids | self.package_service_ids
            if not all_services:
                raise ValidationError(_("No services selected for this job."))

            invoice_lines = []
            for service in all_services:
                invoice_lines.append((0, 0, {
                    'name': service.name,
                    'quantity': 1,
                    'price_unit': service.price,
                }))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.customer_id.id,
                'invoice_origin': self.booking_id.invoice_number or '/',
                'invoice_line_ids': invoice_lines,
            })
            self.booking_id.invoice_id = invoice

        # Set reference both ways
        invoice.washer_job_id = self.id
        self.invoice_number = invoice.name
        self.state = 'paid'

        view_id = self.env.ref('account.view_move_form').id
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
        }


    def action_view_job_invoices(self):
        self.ensure_one()
        invoices = self.env['account.move'].search([('washer_job_id', '=', self.id)])
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
            })
        else:
            action.update({
                'domain': [('id', 'in', invoices.ids)],
            })
        return action
