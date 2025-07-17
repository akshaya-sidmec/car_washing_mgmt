{
    "name": "Car Washing Management System",
    'version': '18.0.1.0',
    'category': 'Services/Car Wash',
    'summary': 'Comprehensive Car Washing System with Multi-Branch, Booking, Inventory, and CRM',
    'description': """
        This module provides a complete car washing management solution, including:
        - Multi-branch operations
        - Service catalog and dynamic pricing
        - Vehicle and customer management
        - Online booking with real-time availability
        - Job workflow automation
        - Consumables and equipment tracking
        - Invoicing and loyalty programs
        - Customer portal and reporting
    """,

    "author": "sidmec_interns",
    "depends": ['base', 'contacts', 'account', 'stock', 'hr', 'product', 'mail', 'board'],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/email_template.xml",
        "views/accounting.xml",
        "views/hr_employee.xml",
        "views/res_partner.xml",
        "views/car_wash_job.xml",
        "views/car_wash_views.xml",
        "views/service_category.xml",
        "views/view_dashboard.xml",
        "views/view_feedback.xml",
        # "views/invoices.xml",
        "portal_views/portal_booking_form.xml",
        "portal_views/portal_breadcrumbs.xml",
        "portal_views/portal_home_menu.xml",
        "portal_views/portal_menu.xml",
        "portal_views/portal_my_bookings_page.xml",
        "portal_views/portal_templates.xml",
        "views/menu.xml",
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "LGPL-3",

}
