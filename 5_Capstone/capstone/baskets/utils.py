import io

from django.core.mail import mail_admins, send_mail
from django.urls import reverse
from xlsxwriter.workbook import Workbook

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
    wrap = workbook.add_format({'text_wrap': True})

    for order in delivery.orders.all():
        worksheet = workbook.add_worksheet(order.user.last_name)
        row = 0
        col = 0

        # order headers
        main_headers = (
            ["Basket Order", ""],
            ["Delivery date:", str(delivery.date)],
            ["", ""],
            ["User:", f"{order.user.first_name} {order.user.last_name}"],
            ["Group:", order.user.groups.first().name if order.user.groups.first() else ""],
            ["Address:", order.user.address],
            ["Phone:", order.user.phone],
            ["", ""],
        )
        for title, value in main_headers:
            worksheet.write(row, col, title)
            worksheet.merge_range(row, col + 1, row, col + 3, value, wrap)  # values takes up 3 cols
            row += 1
        # set height for 'address' row
        worksheet.set_row(5, 50)

        # order items headers
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

        # set width of 'product' column
        max_column_size = max([len(item.product.name) for item in order.items.all()])
        worksheet.set_column('A:A', max_column_size)
        # set width of other order items columns
        worksheet.set_column(1, 3, 10)

        # order total
        row += 1  # one empty row
        worksheet.write(row, col + 2, "Total", bold)
        worksheet.write_number(row, col + 3, order.amount, money)

    workbook.close()

    buffer.seek(0)  # set pointer to beginning
    return buffer


def email_admin_ask_account_activation(user):
    """Send email to admin to ask for user account activation"""

    user_admin_url = settings.SERVER_URL + reverse("admin:baskets_user_change", args=[user.id])

    subject = f"New user {user.username} account requires validation"
    message = f"New user {user.username} has registered to Baskets app." \
              f"Its account needs to be activated. Please go to its user profile, check 'Active' and save."
    html_message = f"New user <strong>{user.username}</strong> has registered to <strong>Baskets app</strong>. " \
                   f"Its account needs to be activated.<br>" \
                   f"Please go to its <a href='{user_admin_url}'>user profile</a>, check 'Active' and save."

    mail_admins(
        subject=subject,
        message=message,
        html_message=html_message,
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
        from_email=settings.SERVER_EMAIL,
        recipient_list=[user.email],
    )
