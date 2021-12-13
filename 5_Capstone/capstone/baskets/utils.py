import io

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from xlsxwriter.workbook import Workbook

from baskets.models import User
from capstone import settings

APP_NAME = _("Baskets")


def get_order_forms_xlsx(delivery):
    """Generate an 'in memory' Excel workbook containing order forms for given delivery, one sheet per user order"""

    # Create a file-like buffer
    buffer = io.BytesIO()

    # Create the Workbook object, using the buffer as its "file"
    workbook = Workbook(buffer, {'in_memory': True})

    # Add formats
    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '0.00 €'})

    for order in delivery.orders.all():
        worksheet = workbook.add_worksheet(order.user.last_name)

        # order header
        row = 0
        col = 0
        worksheet.write(row, col, gettext("Basket Order"), bold)
        worksheet.write(row + 1, col, gettext("Delivery date"))
        worksheet.write(row + 1, col + 1, str(delivery.date))

        # user info
        row = 3
        worksheet.write(row, col, gettext("User:"))
        worksheet.write(row, col + 1, f"{order.user.first_name} {order.user.last_name}")
        worksheet.write(row + 1, col, gettext("Group:"))
        worksheet.write(row + 1, col + 1, order.user.groups.first().name if order.user.groups.first() else "")
        worksheet.write(row + 2, col, gettext("Address:"))
        worksheet.write(row + 2, col + 1, order.user.address)
        worksheet.write(row + 3, col, gettext("Phone:"))
        worksheet.write(row + 3, col + 1, order.user.phone)

        # order items headers
        row = 8
        worksheet.write(row, col, gettext("Product"), bold)
        worksheet.write(row, col + 1, gettext("Unit price"), bold)
        worksheet.write(row, col + 2, gettext("Quantity"), bold)
        worksheet.write(row, col + 3, gettext("Amount"), bold)
        row += 1

        # order items
        for item in order.items.all():
            worksheet.write_string(row, col, item.product.name)
            worksheet.write_number(row, col + 1, item.product.unit_price, money)
            worksheet.write_number(row, col + 2, item.quantity)
            worksheet.write_number(row, col + 3, item.amount, money)
            row += 1

        # adjust width of 'product' column to maximum length of product.name
        max_column_size = max([len(item.product.name) for item in order.items.all()])
        worksheet.set_column('A:A', max_column_size)
        # set width of other columns to length of 'Unit price' translation
        column_size = len(gettext("Unit price"))
        worksheet.set_column('B:D', column_size)

        # order total
        row += 1  # one empty row
        worksheet.write(row, col + 2, gettext("Total"), bold)
        worksheet.write_number(row, col + 3, order.amount, money)

    workbook.close()

    buffer.seek(0)  # set pointer to beginning
    return buffer


def email_staff_ask_account_activation(user):
    """Send email to staff members to ask for user account activation"""

    staff_emails = [staff.email for staff in User.objects.filter(is_staff=True)]
    user_admin_url = settings.SERVER_URL + reverse("admin:baskets_user_change", args=[user.id])

    subject = f"[{APP_NAME}] " + _("New user {} account requires validation").format(user.username)
    message = _("New user {} has registered to {}.\n"
                "Its account needs to be activated. Please go to its user profile:\n"
                "{}\n"
                "Then check 'Active' and save.").format(user.username, APP_NAME, user_admin_url)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
    )


def email_staff_contact(from_email, subject, message):
    """Send email to staff with 'Contact' form data"""

    staff_emails = [staff.email for staff in User.objects.filter(is_staff=True)]

    subject_ = f"[{APP_NAME}] " + _("Contact: ") + subject
    message_ = _("Message from {}:\n").format(from_email) + message

    send_mail(
        subject=subject_,
        message=message_,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
    )


def email_user_account_activated(user):
    """Send email to user to notify its account activation"""

    index_url = settings.SERVER_URL + reverse("index")

    subject = f"[{APP_NAME}] " + _("Welcome")
    message = _("Hello {},\n"
                "Your account has been activated.\n"
                "You can start using {}:\n"
                "{}").format(user.username, APP_NAME, index_url)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
