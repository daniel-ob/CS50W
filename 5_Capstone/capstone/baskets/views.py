from datetime import date
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from . import utils
from .forms import UserForm, ContactForm, BasketsSetPasswordForm
from .models import Order, Delivery, Product, OrderItem, User


@login_required
def index(request):
    """Render 'Next Orders' page: a list of opened deliveries and its related orders in chronological order"""

    opened_deliveries = Delivery.objects.filter(order_deadline__gte=date.today()).order_by("date")

    deliveries_orders = [
        {
            "delivery": d,
            "order": Order.objects.filter(user=request.user, delivery=d).first()
        }
        for d in opened_deliveries
    ]

    return render(request, "baskets/index.html", {
        "title": _("Next Orders"),
        "deliveries_orders": deliveries_orders
    })


@login_required
def order_history(request):
    """Render 'Order history' page: a list of closed user orders in reverse chronological order"""

    closed_user_orders = Order.objects.filter(
        user=request.user,
        delivery__order_deadline__lt=date.today()
    ).order_by("-delivery__date")

    deliveries_orders = [
        {
            "delivery": o.delivery,
            "order": o
        }
        for o in closed_user_orders
    ]

    return render(request, "baskets/index.html", {
        "title": _("Order History"),
        "deliveries_orders": deliveries_orders
    })


def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "baskets/login.html", {
                "message": _("Invalid username and/or password.")
            })
    else:
        return render(request, "baskets/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        user_form = UserForm(request.POST)
        password_form = BasketsSetPasswordForm(user=request.user, data=request.POST)
        if not (user_form.is_valid() and password_form.is_valid()):
            # render the same page adding existing forms data, so users can see the errors they made
            return render(request, "baskets/register.html", {
                "user_form": user_form,
                "password_form": password_form
            })

        # Create new user
        user = user_form.save(commit=False)
        # check that passwords matches and save hashed password
        password = password_form.clean_new_password2()
        user.set_password(password)
        # user account will be activated by admin
        user.is_active = False
        user.save()

        utils.email_staff_ask_account_activation(user)
        return render(request, "baskets/register.html", {
            "message": _("Your register request has been sent to staff for validation. "
                         "You will receive an email as soon as your account is activated."),
            "user_form": user_form,
            "password_form": password_form
        })
    else:
        # render empty forms
        return render(request, "baskets/register.html", {
            "user_form": UserForm(),
            "password_form": BasketsSetPasswordForm(user=request.user)
        })


@login_required
def profile(request):
    """User profile:
    - GET: render 'User profile' page
    - POST: update user profile
    """

    user = User.objects.get(username=request.user)
    message = ""

    if request.method == "POST":
        form = UserForm(instance=user, data=request.POST)
        if not form.is_valid():
            # render the same page adding existing form data, so users can see the errors they made
            return render(request, "baskets/profile.html", {
                "form": form
            })
        user.save()
        message = _("Your information has been correctly updated")

    # render user information
    return render(request, "baskets/profile.html", {
        "message": message,
        "form": UserForm(instance=user)
    })


def contact(request):
    """Contact admins:
    - GET: render 'Contact' page
    - POST: submit contact form to admins by email
    """

    message = ""

    if request.method == "POST":
        form = ContactForm(request.POST)
        if not form.is_valid():
            return render(request, "baskets/contact.html", {
                "form": form
            })

        utils.email_staff_contact(
            from_email=form.cleaned_data["from_email"],
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"]
        )
        message = _("Your message has been submitted.")

    default_data = {"from_email": request.user.email if request.user.is_authenticated else None}
    return render(request, "baskets/contact.html", {
        "message": message,
        "form": ContactForm(initial=default_data)
    })


def orders(request):
    """Orders API:
    - GET: Get the list of user orders
    - POST: Create order for given delivery
    """

    # User must be authenticated to create/retrieve orders
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    if request.method == "GET":
        order_list = [
            {
                "id": o.id,
                "delivery_id": o.delivery.id,
            }
            for o in request.user.orders.all()
        ]
        return JsonResponse(order_list, safe=False)

    if request.method == "POST":
        data = json.loads(request.body)

        # Attempt to retrieve delivery
        d_id = data["delivery_id"]
        try:
            d = Delivery.objects.get(id=d_id)
        except Delivery.DoesNotExist:
            return JsonResponse({"error": f"Delivery with id {d_id} does not exist"}, status=404)

        # Orders for given delivery can only be created until deadline
        if date.today() > d.order_deadline:
            return JsonResponse({"error": "Order deadline is passed for this delivery"}, status=400)

        # User can only have one order per delivery
        if d.orders.filter(user=request.user):
            return JsonResponse({"error": "User already has an order for this delivery"}, status=400)

        o = Order.objects.create(
            user=request.user,
            delivery=d,
            message=data.get("message", "")
        )

        # Add order items
        if data.get("items") is None:
            o.delete()
            return JsonResponse({"error": "Order must contain at least one item"}, status=400)
        else:
            for item in data["items"]:
                # Attempt to retrieve product
                try:
                    product = Product.objects.get(id=item["product_id"])
                except Product.DoesNotExist:
                    o.delete()
                    return JsonResponse({"error": f"Product with id {item['product_id']} does not exist"}, status=404)

                order_item = OrderItem.objects.create(
                    order=o,
                    product=product,
                    quantity=int(item["quantity"])
                )

                if not order_item.is_valid():
                    # Delete order with related items
                    o.delete()
                    return JsonResponse({"error": "Invalid order. All products must be available in the delivery and "
                                                  "quantities must be greater than zero"}, status=400)
            o.save()

        return JsonResponse({
            "message": "Order has been successfully created",
            "url": reverse("order", args=[o.id]),
            "amount": "{:.2f}".format(o.amount)
        }, status=201)

    else:
        return HttpResponseNotAllowed(["GET", "POST"])


def order(request, order_id):
    """Order API:
    - GET: Get Order details
    - PUT: Update existing Order (items, message)
    - DELETE: Delete Order
    """

    # User must be authenticated to access orders
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    # Attempt to retrieve order
    o = get_object_or_404(Order, id=order_id)

    # User can only access its own orders
    if o.user != request.user:
        raise PermissionDenied

    if request.method == "GET":
        return JsonResponse(o.serialize())

    elif request.method == "PUT":
        # Orders can only be updated until its delivery deadline
        if date.today() > o.delivery.order_deadline:
            return JsonResponse({"error": "Related delivery is closed. Order can't be updated"}, status=400)

        data = json.loads(request.body)

        if data.get("items") is not None:
            # Update order items (remove old, add new)
            old_order_items = o.items.all()
            new_order_items = []

            for item in data["items"]:
                # Attempt to retrieve product
                try:
                    product = Product.objects.get(id=item["product_id"])
                except Product.DoesNotExist:
                    return JsonResponse({"error": f"Product with id {item['product_id']} does not exist"}, status=404)

                order_item = OrderItem(
                    order=o,
                    product=product,
                    quantity=int(item["quantity"])
                )

                if not order_item.is_valid():
                    return JsonResponse({"error": "All products must be available in the delivery and "
                                                  "quantities must be greater than zero"}, status=400)
                new_order_items.append(order_item)

            for order_item in old_order_items:
                order_item.delete()

            for order_item in new_order_items:
                order_item.save()

        if data.get("message") is not None:
            o.message = data["message"]

        o.save()

        return JsonResponse({
            "message": "Order has been successfully updated",
            "amount": "{:.2f}".format(o.amount)
        }, status=200)

    elif request.method == "DELETE":
        o.delete()
        return JsonResponse({
            "message": "Order has been successfully deleted",
        }, status=200)

    else:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


def deliveries(request):
    """Deliveries API: GET the list of opened deliveries"""

    opened_deliveries = Delivery.objects.filter(order_deadline__gte=date.today()).order_by("date")
    d_list = [
        {
            "id": d.id,
            "date": d.date
        }
        for d in opened_deliveries
    ]
    return JsonResponse(d_list, safe=False)


def delivery(request, delivery_id):
    """Delivery API: GET Delivery details"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    if request.method == "GET":
        return JsonResponse(d.serialize())


@staff_member_required
def delivery_export(request, delivery_id):
    """Download delivery related orders forms"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    buffer = utils.get_order_forms_xlsx(d)
    return FileResponse(buffer, as_attachment=True, filename=f"{d.date}_order_forms.xlsx")
