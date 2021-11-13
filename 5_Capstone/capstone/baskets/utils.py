from django.core.mail import mail_admins, send_mail
from django.urls import reverse

from capstone import settings


def delivery_to_order_form_book(delivery):
    bookdict = {}

    for order in delivery.orders.all():
        sheet_content = [
            ["Basket Order"],
            [""],
            ["User:", f"{order.user.first_name} {order.user.last_name}"],
            ["Delivery date:", str(delivery.date)],
            [""],
            ["Product", "Unit price", "Quantity", "Amount"]
        ]

        for item in order.items.all():
            sheet_content.append(
                [item.product.name, str(item.product.unit_price), item.quantity, str(item.amount)]
            )

        sheet_content.append(
            ["", "", "total", str(order.amount)]
        )

        bookdict[order.user.last_name] = sheet_content

    return bookdict


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
