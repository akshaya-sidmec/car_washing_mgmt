from odoo import http
from odoo.http import request
from datetime import datetime

class CarWashPortal(http.Controller):

    @http.route(['/my/bookings'], type='http', auth="user", website=True)
    def portal_my_bookings(self, **kw):
        partner = request.env.user.partner_id
        bookings = request.env['car.wash.booking'].sudo().search([('customer_id', '=', partner.id)])
        return request.render('sdm_car_mgmt_project.portal_my_bookings_page', {
            'bookings': bookings,
        })

    @http.route(['/my/bookings/<model("car.wash.booking"):booking>'], type='http', auth="user", website=True)
    def portal_booking_detail(self, booking, **kw):
        job = booking.job_id
        return request.render('sdm_car_mgmt_project.portal_booking_detail', {
            'booking': booking,
            'job': job,
            'now': datetime.now()
        })

    @http.route(['/my/bookings/<int:booking_id>/cancel'], type='http', auth="user", website=True, csrf=False)
    def portal_booking_cancel(self, booking_id, **post):
        booking = request.env['car.wash.booking'].sudo().browse(booking_id)
        reason = post.get("cancel_reason", "")
        if booking.time_slot > datetime.now():
            if booking.job_id and booking.job_id.state != 'cancelled':
                booking.job_id.action_cancel()
                booking.job_id.cancellation_reason = reason
        return request.redirect('/my/bookings')

    @http.route(['/my/bookings/<int:booking_id>/feedback'], type='http', auth="user", website=True, csrf=False)
    def portal_booking_feedback(self, booking_id, **post):
        booking = request.env['car.wash.booking'].sudo().browse(booking_id)
        rating = post.get("rating")
        comment = post.get("feedback")
        booking.write({'rating': rating, 'feedback': comment})
        return request.redirect('/my/bookings/%s' % booking_id)

    @http.route(['/my/bookings/<int:booking_id>/reschedule'], type='http', auth="user", website=True)
    def portal_booking_reschedule(self, booking_id, **kw):
        return request.redirect('/contactus')  # placeholder for rescheduling logic

    # ✅ BOOKING CREATION ROUTES (MOVED INSIDE CLASS)
    @http.route(['/my/bookings/new'], type='http', auth="user", website=True)
    def portal_booking_create(self, **kw):
        packages = request.env['car.wash.package'].sudo().search([])
        branches = request.env['res.company'].sudo().search([])
        return request.render('sdm_car_mgmt_project.portal_booking_create_form', {
            'packages': packages,
            'branches': branches,
        })

    @http.route(['/my/bookings/new/submit'], type='http', auth="user", website=True, csrf=False)
    def portal_booking_create_submit(self, **post):
        partner = request.env.user.partner_id
        if not (post.get("vehicle_number") and post.get("package_id") and post.get("time_slot") and post.get(
                "branch_id")):
            return request.redirect("/my/bookings/new")

        try:
            time_slot = datetime.strptime(post.get("time_slot"), "%Y-%m-%dT%H:%M")
        except ValueError:
            return request.redirect("/my/bookings/new")

        booking = request.env['car.wash.booking'].sudo().create({
            'customer_id': partner.id,
            'vehicle_number': post.get("vehicle_number"),
            'package_id': int(post.get("package_id")),
            'branch_id': int(post.get("branch_id")),
            'time_slot': time_slot,
            'state': 'draft',
            'name': 'New',
        })
        return request.redirect(f'/my/bookings/{booking.id}')


    @http.route(['/my/booking/<int:booking_id>/feedback'], type='http', auth="user", website=True)
    def submit_feedback(self, booking_id, **post):
        booking = request.env['car.wash.booking'].sudo().browse(booking_id)
        if booking.customer_id.id == request.env.user.partner_id.id:
            rating = int(post.get('rating', 0))
            comment = post.get('comment', '')
            booking.write({
                'feedback_rating': rating,
                'feedback_comment': comment,
            })
        return request.redirect(f'/my/bookings/{booking_id}')