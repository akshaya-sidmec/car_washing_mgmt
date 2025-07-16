from odoo import http
from odoo.http import request


class CarWashFeedbackController(http.Controller):

    @http.route(['/feedback/<int:booking_id>'], type='http', auth='public', website=True, csrf=False)
    def feedback_form(self, booking_id, **kwargs):
        booking = request.env['car.wash.booking'].sudo().browse(booking_id)
        return request.render('sdm_car_mgmt_project.feedback_form', {
            'booking': booking,
        })

    @http.route(['/submit_feedback'], type='http', auth='public', website=True, csrf=False)
    def submit_feedback(self, **post):
        customer_id = int(post.get('customer_id'))
        booking_id = int(post.get('booking_id'))
        rating = post.get('rating')
        feedback = post.get('feedback')

        request.env['car.wash.feedback'].sudo().create({
            'customer_id': customer_id,
            'booking_id': booking_id,
            'rating': rating,
            'feedback': feedback,
        })
        return """
<html>
    <head>
        <title>Thank You</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .thankyou-box {
                background-color: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
            }
            h2 {
                color: #28a745;
                margin-bottom: 10px;
            }
            p {
                color: #555;
                font-size: 16px;
            }
        </style>
    </head>
    <body>
        <div class="thankyou-box">
            <h2>🎉 Thank You for Your Feedback!</h2>
            <p>We appreciate your time and your thoughts.</p>
        </div>
    </body>
</html>
"""
