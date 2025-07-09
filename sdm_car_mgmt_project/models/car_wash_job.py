from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


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
    washer_id = fields.Many2one('hr.employee', string="Assigned To",
                                domain="[('category_ids.name', 'ilike', 'Supervisor')]")
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
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('work_done', 'Work Done'),
        ('quality_check', 'Quality Check'),
        ('ready_to_deliver', 'Ready to Deliver'),
        ('awaiting_payment', 'Payment verification'),
        ('paid', 'Paid'),
        ('done', 'Service Completed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string="Job Status", default='draft', tracking=True)

    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('scheduled', 'Scheduled'),
    #     ('in_progress', 'In Progress'),
    #     ('checklist_review', 'Checklist Review'),
    #     ('supervisor_review', 'Supervisor Review'),
    #     ('awaiting_payment', 'Awaiting Payment'),
    #     ('paid', 'Paid'),
    #     ('done', 'Done'),
    #     ('cancelled', 'Cancelled')
    # ], string='Status', default='draft')

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

    quality_checked_by = fields.Char(string="Quality Check by")

    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        related='booking_id.invoice_id',
        store=True,
        readonly=True
    )

    invoice_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid')
    ], string="Payment Status", related='booking_id.invoice_status', store=True, readonly=True)

    invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count")
    related_invoice_ids = fields.Many2many('account.move', string="Invoices")
    delivery_count = fields.Integer(string="Delivery Orders", compute="_compute_delivery_count")

    @api.depends('booking_id.invoice_id', 'invoice_status')
    def _compute_invoice_count(self):
        for rec in self:
            if rec.invoice_status != 'paid' or not rec.booking_id.invoice_id:
                rec.invoice_count = 0
                rec.related_invoice_ids = [(5, 0, 0)]  # clear
            else:
                rec.related_invoice_ids = rec.booking_id.invoice_id
                rec.invoice_count = len(rec.related_invoice_ids)

    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = self.env['stock.picking'].search_count([
                ('origin', 'ilike', rec.booking_id.display_name or str(rec.id))
            ])

    def action_regenerate_checklist(self):
        for job in self:
            job.checklist_line_ids.unlink()  # delete existing
            services = job.booking_id.service_ids | job.booking_id.package_service_ids
            lines = [(0, 0, {'name': s.name}) for s in services]
            job.checklist_line_ids = lines

    def write(self, vals):
        res = super(CarWashJob, self).write(vals)
        for rec in self:
            if vals.get('washer_id') and rec.state == 'draft':
                rec.state = 'assigned'
        return res

    @api.model
    def create(self, vals):
        job = super(CarWashJob, self).create(vals)
        if vals.get('washer_id') and job.state == 'draft':
            job.state = 'assigned'
        return job

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

    product_ids = fields.Many2many('product.product', string='Products')

    package_ids = fields.Many2many('car.wash.package', string="Packages")

    # def action_schedule_job(self):
    #     for job in self:
    #         # Use a set to avoid duplicates
    #         product_ids = set()
    #         services = job.service_ids | job.package_service_ids
    #
    #         for service in services:
    #             product = service.product_id
    #             if not product or product.id in product_ids:
    #                 continue
    #             product_ids.add(product.id)
    #
    #             available_qty = product.qty_available - product.outgoing_qty
    #
    #             if available_qty <= 0:
    #                 raise ValidationError(
    #                     _(f"Cannot schedule job: '{product.display_name}' has no available stock.")
    #                 )
    #
    #         # If all products have sufficient stock, schedule the job
    #         job.state = 'assigned'

    @api.depends('service_ids', 'package_service_ids')
    def _compute_merged_services_html(self):
        for rec in self:
            all_services = rec.service_ids | rec.package_service_ids
            names = all_services.mapped('name')
            items = "".join(f"<li><input type='checkbox'> {name}</li>" for name in names)
            rec.merged_services_html = f"<ul>{items}</ul>"

    def action_start_job(self):
        self.ensure_one()
        self.state = 'in_progress'

    def action_confirm_work_done(self):
        self.ensure_one()
        self.state = 'work_done'

    def action_quality_check(self):
        self.ensure_one()
        self.state = 'quality_check'
        self.quality_checked_by = self.env.user.name

    def action_ready_to_deliver(self):
        self.ensure_one()
        self.state = 'ready_to_deliver'

    # def action_set_scheduled(self):
    #     self.state = 'scheduled'

    # def action_start_job(self):
    #     self.state = 'in_progress'

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
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)

        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')

        for job in self:

            # Create the picking
            picking = StockPicking.create({
                'picking_type_id': picking_type.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
                'origin': f'Car Wash Job {job.booking_id.display_name or job.id}',
            })

            # Use a set to avoid duplicate moves
            product_ids = set()
            services = job.service_ids | job.package_service_ids

            for service in services:
                products = service.product_id  # now Many2many
                if not products:
                    continue
                for product in products:
                    if product.id in product_ids:
                        continue
                    product_ids.add(product.id)

                    StockMove.create({
                        'name': product.display_name,
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'product_uom': product.uom_id.id,
                        'location_id': stock_location.id,
                        'location_dest_id': customer_location.id,
                        'picking_id': picking.id,
                    })

            if not picking.move_ids:
                raise UserError("No consumable products found in the selected services or packages for this job.")

            picking.action_confirm()
            picking.action_assign()
            picking.button_validate()

            job.state = 'done'

        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_mark_delivered(self):
        for rec in self:
            rec.state = 'delivered'

    ##to add product to smart button
    product_count = fields.Integer(string="Products", compute="_compute_product_ids")
    product_ids = fields.Many2many('product.template', string="Products")

    @api.depends('service_ids', 'package_service_ids', 'state')
    def _compute_product_ids(self):
        for rec in self:
            if rec.state != 'done':
                rec.product_ids = [(5, 0, 0)]  # clear
                rec.product_count = 0
            else:
                products = self.env['product.template'].browse()
                services = rec.service_ids | rec.package_service_ids

                for service in services:
                    products |= service.product_id.mapped('product_tmpl_id')

                rec.product_ids = products
                rec.product_count = len(products)

    def _compute_product_count(self):
        for rec in self:
            rec.product_count = self.env['product.template'].search_count([])

    def action_open_related_product_templates(self):
        self.ensure_one()
        template_ids = self.product_ids.mapped('product_tmpl_id').ids

        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'view_mode': 'list,form',
            'res_model': 'product.template',
            'target': 'current',
        }

    def action_open_delivery_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Orders',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('origin', 'ilike', self.booking_id.display_name or str(self.id))],
            'target': 'current',
        }

    def action_open_related_invoices(self):
        self.ensure_one()
        # if self.invoice_status != 'paid':
        #     raise UserError("Invoices are visible only after payment is marked as Paid.")
        # if not self.related_invoice_ids:
        #     raise UserError("No invoices found for this job.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.related_invoice_ids.ids)],
            'target': 'current',
        }
