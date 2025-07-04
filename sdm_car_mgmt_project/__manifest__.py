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
    "depends": ['base', 'contacts', 'account', 'stock', 'hr', 'product', 'mail','board'],

    "data": [
        "security/ir.model.access.csv",
        "data/email_template.xml",
        "views/hr_employee.xml",
        "views/res_partner.xml",
        "views/car_wash_job.xml",
        "views/car_wash_views.xml",
        "views/service_category.xml",
        "data/email_template.xml",
        "views/accounting.xml",
        "views/menu.xml",
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    "license": "LGPL-3",

}
