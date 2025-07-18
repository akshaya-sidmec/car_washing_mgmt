import base64
import mimetypes
from odoo import models, fields, api
from odoo.exceptions import UserError


class CarWashSendWizard(models.TransientModel):
    _name = 'car.wash.send.wizard'
    _description = 'Car Wash Booking Send Wizard'

    booking_id = fields.Many2one('car.wash.booking', required=True, readonly=True)
    mail_partner_ids = fields.Many2many('res.partner', string="To", required=True)
    mail_subject = fields.Char("Subject", required=True)
    mail_body = fields.Html("Body")
    mail_attachments_widget = fields.Many2many('ir.attachment', string="Attachments")
    mail_template_id = fields.Many2one('mail.template', string="Email Template")

    def action_send_and_print(self):
        self.ensure_one()

        template = self.mail_template_id
        if not template:
            raise UserError("Please select a template to send.")

        attachment_ids = self.mail_attachments_widget.ids

        ctx = {
            'default_model': 'car.wash.booking',
            'default_res_ids': [self.booking_id.id],
            'default_use_template': True,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_attachment_ids': attachment_ids,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        booking = self.env['car.wash.booking'].browse(self.env.context.get('default_booking_id'))
        if booking:
            dynamic_report_id = 'sdm_car_mgmt_project.report_car_wash_booking_email'
            try:
                report_action = self.env.ref(dynamic_report_id)
            except ValueError:
                raise UserError(f"Could not find report with ID '{dynamic_report_id}'")

            pdf_content, _ = self.env['ir.actions.report'] \
                .with_company(booking.company_id or booking.branch_id.company_id) \
                .with_context(from_send_wizard=True) \
                ._render(dynamic_report_id, [booking.id])

            filename = f"{booking.invoice_number or 'Booking'} Report.pdf"
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'car.wash.booking',
                'res_id': booking.id,
                'mimetype': mimetype or 'application/pdf',
            })

            res['mail_attachments_widget'] = [(6, 0, [attachment.id])]
        return res

    @api.model
    def create(self, vals):
        for attachment in self.env['ir.attachment'].browse(vals.get('mail_attachments_widget', [])):
            if not attachment.name:
                attachment.name = 'file.pdf'
            if not attachment.mimetype:
                attachment.mimetype = 'application/pdf'
        return super().create(vals)
