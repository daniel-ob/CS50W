import io

from django.core.mail import send_mail
from django.urls import reverse
from xlsxwriter.workbook import Workbook

from baskets.models import User
from capstone import settings


def get_order_forms_xlsx(delivery):
    """Generate an 'in memory' Excel workbook containing order forms for given delivery, one sheet per user order"""

    # Create a file-like buffer
    buffer = io.BytesIO()

    # Create the Workbook object, using the buffer as its "file"
    workbook = Workbook(buffer, {'in_memory': True})

    # Add formats
    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '#.## €'})

    for order in delivery.orders.all():
        worksheet = workbook.add_worksheet(order.user.last_name)

        # order header
        row = 0
        col = 0
        worksheet.write(row, col, "Basket Order", bold)
        worksheet.write(row + 1, col, "Delivery date")
        worksheet.write(row + 1, col + 1, str(delivery.date))

        # user info
        row = 3
        worksheet.write(row, col, "User:")
        worksheet.write(row, col + 1, f"{order.user.first_name} {order.user.last_name}")
        worksheet.write(row + 1, col, "Group:")
        worksheet.write(row + 1, col + 1, order.user.groups.first().name if order.user.groups.first() else "")
        worksheet.write(row + 2, col, "Address:")
        worksheet.write(row + 2, col + 1, order.user.address)
        worksheet.write(row + 3, col, "Phone:")
        worksheet.write(row + 3, col + 1, order.user.phone)

        # order items headers
        row = 8
        worksheet.write(row, col, "Product", bold)
        worksheet.write(row, col + 1, "Unit price", bold)
        worksheet.write(row, col + 2, "Quantity", bold)
        worksheet.write(row, col + 3, "Amount", bold)
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
        # set width of other columns
        worksheet.set_column('B:D', 10)

        # order total
        row += 1  # one empty row
        worksheet.write(row, col + 2, "Total", bold)
        worksheet.write_number(row, col + 3, order.amount, money)

    workbook.close()

    buffer.seek(0)  # set pointer to beginning
    return buffer


def email_staff_ask_account_activation(user):
    """Send email to staff members to ask for user account activation"""

    staff_emails = [staff.email for staff in User.objects.filter(is_staff=True)]
    user_admin_url = settings.SERVER_URL + reverse("admin:baskets_user_change", args=[user.id])

    subject = f"[Baskets] New user {user.username} account requires validation"
    message = f"New user {user.username} has registered to Baskets app." \
              f"Its account needs to be activated. Please go to its user profile, check 'Active' and save."
    html_message = f"New user <strong>{user.username}</strong> has registered to <strong>Baskets app</strong>. " \
                   f"Its account needs to be activated.<br>" \
                   f"Please go to its <a href='{user_admin_url}'>user profile</a>, check 'Active' and save."

    send_mail(
        subject=subject,
        message=message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
    )


def email_staff_contact(from_email, subject, message):
    """Send email to staff with 'Contact' form data"""

    staff_emails = [staff.email for staff in User.objects.filter(is_staff=True)]

    subject_ = "[Baskets] Contact: " + subject
    message_ = f"Message from {from_email}:\n" + message

    send_mail(
        subject=subject_,
        message=message_,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=staff_emails,
    )


def email_user_account_activated(user):
    """Send email to user to notify its account activation"""

    index_url = settings.SERVER_URL + reverse("index")

    subject = "[Baskets] Welcome"
    message = f"Hello {user.username},"\
              "Your account has been activated. You can start using Baskets app."
    html_message = f"Hello <strong>{user.username}</strong>,<br>" \
                   f"Your account has been activated.<br>" \
                   f"You can start using <a href='{index_url}'>Baskets app</a>."

    send_mail(
        subject=subject,
        message=message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
