from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
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
    branch_id = fields.Many2one('car.branch', string="Branch", required=True)
    service_id = fields.Many2one('car.wash.service', string="Service")
    service_ids = fields.Many2many('car.wash.service', string="Services")
    total_price = fields.Monetary(string="Total Price", compute='_compute_total_price', store=True)

    time_slot = fields.Datetime(string="Preferred Time Slot", required=True)
    apply_promo = fields.Boolean(string="Apply Promo Code")
    promo_code = fields.Char(string="Promo Code")
    loyalty_points_used = fields.Integer(string="Loyalty Points Used", default=0)
    discount_amount = fields.Monetary(string="Discount", compute='_compute_discount', store=True)
    amount_total = fields.Monetary(string="Total Amount", compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    invoice_number = fields.Char(string="Invoice Number", readonly=True, copy=False)
    booking_date = fields.Datetime(string="Booking Date", default=fields.Datetime.now)
    select_package = fields.Boolean(string="Select Package")

    package_id = fields.Many2one('car.wash.package', string="Package", domain="[('id', '!=', False)]")

    package_price = fields.Float(string="Package Price", readonly=True)
    package_service_ids = fields.Many2many(
        'car.wash.service',
        'car_wash_booking_package_service_rel',  # Unique relation table name
        'booking_id',
        'service_id',
        string="Included Services from Package",
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('scheduled', 'Scheduled'),
    ], default='draft', string="Status")

    washer_id = fields.Many2one('res.users', string="Assigned Washer")
    job_id = fields.Many2one('car.wash.job', string="Scheduled Job")

    @api.onchange('package_id')
    def _onchange_package_id(self):
        if self.package_id:
            self.package_price = self.package_id.price
            self.package_service_ids = self.package_id.service_ids
        else:
            self.package_price = 0.0
            self.package_service_ids = [(5, 0, 0)]

    @api.depends('service_ids', 'service_ids.price')
    def _compute_total_price(self):
        for record in self:
            if record.select_package and record.package_id:
                record.total_price = record.package_id.price
            else:
                record.total_price = sum(service.price for service in record.service_ids)

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

            # Count how many bookings already have invoice number for this date
            today_count = self.search_count([
                ('invoice_number', 'like', prefix + '%')
            ]) + 1

            seq_num = str(today_count).zfill(3)
            vals['invoice_number'] = f"{prefix}/{seq_num}"

        if vals.get('package_id'):
            package = self.env['car.wash.package'].browse(vals['package_id'])
            vals['package_price'] = package.price
            vals['package_service_ids'] = [(6, 0, package.service_ids.ids)]

        return super(CarWashBooking, self).create(vals)

    def write(self, vals):
        if vals.get('package_id'):
            package = self.env['car.wash.package'].browse(vals['package_id'])
            vals['package_price'] = package.price
            vals['package_service_ids'] = [(6, 0, package.service_ids.ids)]
        return super(CarWashBooking, self).write(vals)

    @api.depends('service_id.price', 'loyalty_points_used')
    def _compute_discount(self):
        for rec in self:
            rec.discount_amount = rec.loyalty_points_used * 1  # Assume 1 point = 1 currency unit

    @api.depends('service_id.price', 'discount_amount')
    def _compute_total(self):
        for rec in self:
            rec.amount_total = rec.service_id.price - rec.discount_amount

    def action_apply_promo(self):
        for rec in self:
            if rec.promo_code == "SAVE10":
                rec.discount_amount += 10

    # def action_confirm_booking(self):
    #     template_id = self.env.ref('sdm_car_mgmt_project.mail_template_booking_confirm')
    #     for rec in self:
    #         if rec.state != 'draft':
    #             continue
    #         rec.state = 'confirmed'
    #         if template_id:
    #             template_id.send_mail(rec.id, force_send=True)
    #         # rec._send_confirmation_sms()

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


# class CarWashJob(models.Model):
#     _name = 'car.wash.job'
#     _description = 'Washer Job Scheduler'
#
#     booking_id = fields.Many2one('car.wash.booking', required=True)
#     washer_id = fields.Many2one('res.users', string="Assigned Washer", required=True)
#     scheduled_time = fields.Datetime(required=True)
