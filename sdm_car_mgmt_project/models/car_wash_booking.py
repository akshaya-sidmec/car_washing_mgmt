from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import logging
import re

_logger = logging.getLogger(__name__)


class CarWashBooking(models.Model):
    _name = 'car.wash.booking'
    _description = 'Car Wash Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "invoice_number"

    customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    vehicle_number = fields.Char(string="Vehicle Number")
    vehicle_name = fields.Char(string="Vehicle Name")
    vehicle_type = fields.Char(string="Vehicle Type")
    vehicle_id = fields.Many2one('car.vehicle', string="Vehicle")
    license_plate_id_1 = fields.Char(related="vehicle_id.license_plate", string="Vehicle Number")
    # branch_id = fields.Many2one('car.branch', string="Branch", required=True)
    branch_id = fields.Many2one('res.company', string="Branch", required=True)
    service_id = fields.Many2one('car.wash.service', string="Service")
    service_ids = fields.Many2many('car.wash.service', string="Services")
    total_price = fields.Monetary(string="Total Price", compute='_compute_total_price', store=True)

    time_slot = fields.Datetime(string="Preferred Time Slot", required=True)
    apply_promo = fields.Boolean(string="Apply Promo Code")
    promo_code = fields.Char(string="Promo Code")
    loyalty_points_used = fields.Integer(string="Loyalty Points Used", default=0)
    discount_amount = fields.Monetary(string="Discount", compute='_compute_discount', store=True) # This will now store the total monetary discount
    amount_total = fields.Monetary(string="Total Amount", compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    invoice_number = fields.Char(string="Invoice Number", readonly=True, copy=False)
    booking_date = fields.Datetime(string="Booking Date", default=fields.Datetime.now)
    select_package = fields.Selection([
        ('service', 'Service'),
        ('package', 'Package')
    ], string="Select Service option", default='service')

    package_id = fields.Many2one('car.wash.package', string="Package", domain="[('id', '!=', False)]")

    package_price = fields.Float(compute='_compute_package_details', store=True)
    discount = fields.Float(compute='_compute_package_details', store=True)
    price_after_discount = fields.Float(compute='_compute_package_details', store=True)
    package_service_ids = fields.Many2many(
        'car.wash.service',
        'car_wash_booking_package_service_rel',  # <-- Explicit relation table name
        'booking_id',
        'service_id',
        string='Package Services'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', string="Status")

    washer_id = fields.Many2one('res.users', string="Assigned Washer")
    job_id = fields.Many2one('car.wash.job', string="Scheduled Job")
    job_status = fields.Selection(
        related='job_id.state',
        string='Job Status',
        store=True,
        readonly=True
    )

    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid')
    ], string="Payment Status", compute="_compute_invoice_status", store=True)

    name = fields.Char(string="Booking Reference", required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))

    rating = fields.Selection([
        ('1', '★☆☆☆☆'),
        ('2', '★★☆☆☆'),
        ('3', '★★★☆☆'),
        ('4', '★★★★☆'),
        ('5', '★★★★★'),
    ], string="Customer Rating")
    feedback = fields.Text(string="Feedback")
    display_discount = fields.Char(compute='_compute_display_discount', store=True)
    apply_loyalty_discount = fields.Boolean(string="Apply Loyalty Points", default=False)
    price_after_loyalty = fields.Monetary(string="Price After Loyalty Discount", compute='_compute_discount',
                                          store=True)

    @api.depends('discount')
    def _compute_display_discount(self):
        for rec in self:
            if rec.discount:
                rec.display_discount = f"-{int(rec.discount)}%"
            else:
                rec.display_discount = "0%"

    @api.depends('invoice_id.payment_state')
    def _compute_invoice_status(self):
        for rec in self:
            if rec.invoice_id:
                rec.invoice_status = 'paid' if rec.invoice_id.payment_state == 'paid' else 'not_paid'
            else:
                rec.invoice_status = 'not_paid'

    def action_create_invoice(self):
        if not self.customer_id:
            raise UserError('Please select a customer before creating an invoice.')

        invoice_lines = []

        if self.select_package == 'package' and self.package_id:
            # Package: apply discount
            line_description = f"{self.package_id.name} - {self.discount}% discount applied"
            invoice_lines.append((0, 0, {
                'name': line_description,
                'quantity': 1,
                'price_unit': self.price_after_discount,
            }))
            x_actual_amount = self.total_price
            x_discount = self.display_discount
            x_final_amount = self.price_after_discount

        elif self.select_package == 'service' and self.service_ids:
            total_service_price = 0
            for service in self.service_ids:
                invoice_lines.append((0, 0, {
                    'name': service.name,
                    'quantity': 1,
                    'price_unit': service.price,
                }))
                total_service_price += service.price

            x_actual_amount = total_service_price
            x_discount = 0.0
            x_final_amount = total_service_price

        else:
            raise UserError('Please select either a package or at least one service before creating an invoice.')

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'x_actual_amount': x_actual_amount,
            'x_discount': x_discount,
            'x_final_amount': x_final_amount,
            'invoice_line_ids': invoice_lines
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    @api.depends('package_id')
    def _compute_package_details(self):
        for rec in self:
            if rec.package_id:
                rec.package_price = rec.package_id.price
                rec.discount = rec.package_id.discount
                rec.price_after_discount = rec.package_price - (rec.package_price * rec.discount / 100)
                rec.package_service_ids = rec.package_id.service_ids
            else:
                rec.package_price = 0.0
                rec.discount = 0.0
                rec.price_after_discount = 0.0
                rec.package_service_ids = False

    @api.depends('service_ids', 'service_ids.price', 'select_package', 'package_id.price')
    def _compute_total_price(self):
        """
        Computes the base total price before any additional discounts (like loyalty).
        If a package is selected, it's the package's original price.
        If services are selected, it's the sum of service prices.
        """
        for record in self:
            if record.select_package == 'package' and record.package_id:
                record.total_price = record.package_id.price
            else:
                record.total_price = sum(service.price for service in record.service_ids)

    @api.depends(
        'total_price',
        'apply_loyalty_discount',
        'select_package',
        'package_id.price',
        'customer_id.loyalty_wallet',
        'price_after_discount'
    )
    def _compute_discount(self):
        for rec in self:
            price_before_loyalty_calc = 0.0
            package_built_in_discount_value = 0.0

            if rec.select_package == 'package':
                price_before_loyalty_calc = rec.price_after_discount  # This is price after package's own % discount
                package_built_in_discount_value = rec.package_price - rec.price_after_discount
            else:
                price_before_loyalty_calc = rec.total_price  # This is sum of service prices
                package_built_in_discount_value = 0.0

            loyalty_discount_amount = 0.0
            loyalty_points_to_apply_for_calc = 0

            if rec.apply_loyalty_discount and rec.customer_id and rec.customer_id.loyalty_wallet >= 100:
                loyalty_blocks = rec.customer_id.loyalty_wallet // 100
                loyalty_points_to_apply_for_calc = loyalty_blocks * 100

                loyalty_discount_percentage = loyalty_blocks * 5.0
                loyalty_discount_percentage = min(loyalty_discount_percentage, 100.0)

                # Loyalty discount is applied on the price *after* any package discount
                loyalty_discount_amount = price_before_loyalty_calc * (loyalty_discount_percentage / 100.0)

            rec.loyalty_points_used = loyalty_points_to_apply_for_calc
            rec.price_after_loyalty = price_before_loyalty_calc - loyalty_discount_amount

            if rec.price_after_loyalty < 0:
                rec.price_after_loyalty = 0.0

            # This is the crucial monetary discount field for the invoice
            rec.discount_amount = package_built_in_discount_value + loyalty_discount_amount


    @api.depends('total_price', 'price_after_loyalty', 'select_package', 'price_after_discount')
    def _compute_total(self):
        for rec in self:
            # `amount_total` should always be the final calculated price after all discounts.
            rec.amount_total = rec.price_after_loyalty
            if rec.amount_total < 0:
                rec.amount_total = 0.0

    @api.onchange('vehicle_number')
    def _onchange_vehicle_number(self):
        if self.vehicle_number:
            cleaned = self.vehicle_number.replace(' ', '').upper()
            pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'
            if re.match(pattern, cleaned):
                # Format as "TS 10 EQ 0297"
                state = cleaned[0:2]
                district = cleaned[2:4]
                series = cleaned[4:-4]
                number = cleaned[-4:]
                self.vehicle_number = f"{state} {district} {series} {number}"
            else:
                # Temporarily show warning-style message on screen (does not block saving)
                return {
                    'warning': {
                        'title': "Invalid Vehicle Number",
                        'message': "Please enter a valid vehicle number like TS10EQ0297",
                    }
                }

    @api.constrains('vehicle_number')
    def _check_vehicle_number_format(self):
        for record in self:
            if record.vehicle_number:
                cleaned = record.vehicle_number.replace(' ', '').upper()
                pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'
                if not re.match(pattern, cleaned):
                    raise ValidationError("Vehicle Number must match format: TS 10 EQ 0297")

    @api.model
    def create(self, vals):
        if not vals.get('invoice_number'):
            booking_date = vals.get('booking_date') or fields.Datetime.now()
            date_obj = fields.Datetime.to_datetime(booking_date)
            date_str = date_obj.strftime("%d/%m/%Y")
            prefix = f"CWS/{date_str}"
            today_count = self.search_count([('invoice_number', 'like', prefix + '%')]) + 1
            seq_num = str(today_count).zfill(3)
            vals['invoice_number'] = f"{prefix}/{seq_num}"

        if vals.get('package_id'):
            package = self.env['car.wash.package'].browse(vals['package_id'])
            vals['package_price'] = package.price
            vals['package_service_ids'] = [(6, 0, package.service_ids.ids)]

        # Call super() first to create the record
        record = super(CarWashBooking, self).create(vals)

        # Logic to update visit_count and loyalty_wallet on customer
        # This will trigger IF the booking is created directly in 'confirmed' state.
        # If your default state is 'draft', this won't trigger on creation, but on write/confirm button.
        if record.state == 'confirmed' and record.customer_id:
            record.customer_id.visit_count += 1
            if record.customer_id.visit_count % 3 == 0:
                record.customer_id.loyalty_wallet += 100

        return record

    def write(self, vals):
        state_becomes_confirmed = False
        if 'state' in vals:
            for rec in self:
                if rec.state != 'confirmed' and vals['state'] == 'confirmed':
                    state_becomes_confirmed = True

        res = super(CarWashBooking, self).write(vals)

        for rec in self:
            # Handle visit count and loyalty wallet on confirming booking
            if state_becomes_confirmed and rec.customer_id:
                rec.customer_id.visit_count += 1
                if rec.customer_id.visit_count % 3 == 0:
                    rec.customer_id.loyalty_wallet += 100

            # Update package details if package_id changed
            if 'package_id' in vals and rec.package_id:
                rec.package_price = rec.package_id.price
                rec.discount = rec.package_id.discount
                rec.price_after_discount = rec.package_price - (rec.package_price * rec.discount / 100)
                rec.package_service_ids = rec.package_id.service_ids

        return res

    def action_confirm_booking(self):
        template_id = self.env.ref('sdm_car_mgmt_project.mail_template_booking_confirm')
        for rec in self:
            if rec.state != 'draft':
                continue

            rec.state = 'confirmed'

            # Send confirmation email
            if template_id:
                template_id.send_mail(rec.id, force_send=True)

            # Automatically create job on confirmation
            job = self.env['car.wash.job'].create({
                'booking_id': rec.id,
                'washer_id': rec.washer_id.id,
                'scheduled_time': rec.time_slot,
                'customer_id': rec.customer_id.id,
                'vehicle_number': rec.vehicle_number,
                'vehicle_name': rec.vehicle_name,
                'vehicle_type': rec.vehicle_type,
                'branch_id': rec.branch_id.id,
                'service_ids': [(6, 0, rec.service_ids.ids)],
                'package_id': rec.package_id.id,
                'package_price': rec.package_price,
                'package_service_ids': [(6, 0, rec.package_service_ids.ids)],
                'select_package': rec.select_package,
                'total_price': rec.total_price,
                'currency_id': rec.currency_id.id,
                'scheduled_time': rec.time_slot,

            })

            rec.job_id = job.id

    def action_schedule_job(self):
        for rec in self:
            if rec.state != 'confirmed':
                continue

            job = self.env['car.wash.job'].create({
                'booking_id': rec.id,
                'washer_id': rec.washer_id.id,
                'scheduled_time': rec.time_slot,
                'customer_id': rec.customer_id.id,
                'vehicle_number': rec.vehicle_number,
                'vehicle_name': rec.vehicle_name,
                'vehicle_type': rec.vehicle_type,
                'branch_id': rec.branch_id.id,
                'service_ids': [(6, 0, rec.service_ids.ids)],
                'package_id': rec.package_id.id,
                'package_price': rec.package_price,
                'package_service_ids': [(6, 0, rec.package_service_ids.ids)],
                'select_package': rec.select_package,
                'total_price': rec.total_price,
                'currency_id': rec.currency_id.id,
                'invoice_number': rec.invoice_number.id,
            })

            rec.job_id = job.id
            rec.state = 'scheduled'

    def _send_confirmation_email(self):
        # Placeholder for email logic
        _logger.info(f"Email sent to customer {self.customer_id.email} for booking #{self.id}")

    def _send_confirmation_sms(self):
        # Placeholder for SMS logic
        _logger.info(f"SMS sent to customer {self.customer_id.mobile} for booking #{self.id}")


# car_wash_service.py
class CarWashService(models.Model):
    _name = 'car.wash.service'
    _description = 'Car Wash Service'

    name = fields.Char(required=True)
    price = fields.Monetary(required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    Description = fields.Text(string="Service Description")
    product_id = fields.Many2many('product.product', string="Product", required=True)


class CarVehicle(models.Model):
    _name = 'car.vehicle'
    _description = 'Customer Vehicle'
    _rec_name = 'license_plate'

    name = fields.Char(string="Vehicle Name", required=True)
    vehicle_id = fields.Many2one('car.vehicle', string="Vehicle")
    license_plate = fields.Char(string="Vehicle Number", required=True)
    customer_id = fields.Many2one('res.partner', string="Owner", required=True)

    @api.constrains('license_plate')
    def _check_license_plate_format(self):
        pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'
        for rec in self:
            if rec.license_plate and not re.match(pattern, rec.license_plate.upper().replace(" ", "")):
                raise ValidationError("Invalid License Plate format. Please enter in the format")

    @api.model
    def create(self, vals):
        if vals.get('license_plate'):
            vals['license_plate'] = vals['license_plate'].upper().replace(" ", "")
        return super().create(vals)

    def write(self, vals):
        if vals.get('license_plate'):
            vals['license_plate'] = vals['license_plate'].upper().replace(" ", "")
        return super().write(vals)


class CarBranch(models.Model):
    _name = 'car.branch'
    _description = 'Car Wash Branch'

    name = fields.Char(required=True)
    address = fields.Text()