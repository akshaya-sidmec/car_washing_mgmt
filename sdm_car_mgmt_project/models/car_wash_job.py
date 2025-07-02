from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarWashChecklistLine(models.Model):
    _name = 'car.wash.checklist.line'
    _description = 'Checklist Step'

    name = fields.Char(required=True)
    is_done = fields.Boolean()
    job_id = fields.Many2one('car.wash.job', ondelete='cascade')


class CarWashJob(models.Model):
    _name = 'car.wash.job'
    _description = 'Washer Job Scheduler'

    booking_id = fields.Many2one('car.wash.booking', required=True)
    washer_id = fields.Many2one('res.users', string="Assigned Washer", required=True)
    scheduled_time = fields.Datetime(required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('checklist_review', 'Checklist Review'),
        ('supervisor_review', 'Supervisor Review'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('paid', 'Paid'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    before_photos = fields.Many2many(
        'ir.attachment',
        'car_wash_job_before_photos_rel',
        'job_id',
        'attachment_id',
        string='Before Photos'
    )

    after_photos = fields.Many2many(
        'ir.attachment',
        'car_wash_job_after_photos_rel',
        'job_id',
        'attachment_id',
        string='After Photos'
    )

    checklist_notes = fields.Text(string="Checklist Notes")
    supervisor_signature = fields.Binary(string="Supervisor Signature")
    checklist_line_ids = fields.One2many('car.wash.checklist.line', 'job_id', string='Checklist')

    rating = fields.Selection([
        ('1', '★☆☆☆☆'),
        ('2', '★★☆☆☆'),
        ('3', '★★★☆☆'),
        ('4', '★★★★☆'),
        ('5', '★★★★★'),
    ], string="Customer Rating")

    def action_set_scheduled(self):
        self.state = 'scheduled'

    def action_start_job(self):
        self.state = 'in_progress'

    def action_upload_checklist(self):
        self.state = 'checklist_review'

    def action_supervisor_review(self):
        self.state = 'supervisor_review'

    def action_approve_by_supervisor(self):
        for rec in self:
            if not rec.supervisor_signature:
                raise ValidationError("Supervisor must sign before approval.")
            rec.state = 'awaiting_payment'

    def action_mark_paid(self):
        self.state = 'paid'

    def action_mark_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'
