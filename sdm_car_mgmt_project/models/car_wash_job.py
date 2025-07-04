from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarWashChecklistLine(models.Model):
    _name = 'car.wash.checklist.line'
    _description = 'Checklist Step'

    name = fields.Char(required=True)
    is_done = fields.Boolean(string="Done")
    job_id = fields.Many2one('car.wash.job', ondelete='cascade')


class CarWashJob(models.Model):
    _name = 'car.wash.job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Washer Job Scheduler'
    _rec_name = "booking_id"

    booking_id = fields.Many2one('car.wash.booking', string="Booking ID", required=True)
    washer_id = fields.Many2one('hr.employee', string="Assigned To", domain="[('category_ids.name', 'ilike', 'Supervisor')]")
    scheduled_time = fields.Datetime(required=True)

    customer_id = fields.Many2one('res.partner', string="Customer")
    vehicle_number = fields.Char(string="Vehicle Number")
    vehicle_name = fields.Char(string="Vehicle Name")
    vehicle_type = fields.Char(string="Vehicle Type")
    branch_id = fields.Many2one('car.branch', string="Branch")
    service_ids = fields.Many2many('car.wash.service', string="Services")
    package_id = fields.Many2one('car.wash.package', string="Package")
    package_price = fields.Float(string="Package Price")
    package_service_ids = fields.Many2many(
        'car.wash.service',
        'car_wash_job_package_service_rel',  # Must be a new relation table
        'job_id',
        'service_id',
        string="Included Services from Package"
    )
    select_package = fields.Boolean(string="Is Package?")
    total_price = fields.Monetary(string="Total Price")
    currency_id = fields.Many2one('res.currency', readonly=True)
    invoice_number = fields.Char(string="Invoice Number", readonly=True, copy=False)
    time_slot = fields.Datetime(string="Preferred Time Slot")



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
    is_checked = fields.Boolean()

    merged_services_html = fields.Html(string="Checklist", compute="_compute_merged_services_html")

    def action_regenerate_checklist(self):
        for job in self:
            job.checklist_line_ids.unlink()  # delete existing
            services = job.booking_id.service_ids | job.booking_id.package_service_ids
            lines = [(0, 0, {'name': s.name}) for s in services]
            job.checklist_line_ids = lines

    @api.model
    def create(self, vals):
        job = super().create(vals)

        booking = job.booking_id

        # Merge all service names from both service_ids and package_service_ids
        all_services = booking.service_ids | booking.package_service_ids

        # Create checklist lines
        checklist_lines = [(0, 0, {'name': service.name, 'is_done': False}) for service in all_services]

        job.checklist_line_ids = checklist_lines

        return job

    @api.depends('service_ids', 'package_service_ids')
    def _compute_merged_services_html(self):
        for rec in self:
            all_services = rec.service_ids | rec.package_service_ids
            names = all_services.mapped('name')
            items = "".join(f"<li><input type='checkbox'> {name}</li>" for name in names)
            rec.merged_services_html = f"<ul>{items}</ul>"

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
