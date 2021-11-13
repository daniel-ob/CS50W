from datetime import date
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponseNotAllowed, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from .models import User, Order, Delivery, Product, OrderItem


@login_required
def index(request):
    """Render list of deliveries for which users can still order and its related orders"""

    opened_deliveries = Delivery.objects.filter(order_deadline__gte=date.today()).order_by("date")

    deliveries_orders = [
        {
            "delivery": d,
            "order": Order.objects.filter(user=request.user, delivery=d).first()
        }
        for d in opened_deliveries
    ]

    return render(request, "baskets/index.html", {
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
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "baskets/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "baskets/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "baskets/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "baskets/register.html")


def create_order(request):
    """POST: Create order for given delivery"""

    # Order creation must be via POST
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # User must be authenticated to create orders
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

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


def order(request, order_id):
    """Order:
    - GET: Get Order details
    - PUT: Update existing Order
    - DELETE: Delete Order"""

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
            # Update order items
            previous_order_items_ids = [order_item.id for order_item in o.items.all()]

            # Add new items
            for item in data["items"]:
                # Attempt to retrieve product
                try:
                    product = Product.objects.get(id=item["product_id"])
                except Product.DoesNotExist:
                    return JsonResponse({"error": f"Product with id {item['product_id']} does not exist"}, status=404)

                order_item = OrderItem.objects.create(
                    order=o,
                    product=product,
                    quantity=int(item["quantity"])
                )

                if not order_item.is_valid():
                    order_item.delete()
                    return JsonResponse({"error": "Invalid order. All products must be available in the delivery and "
                                                  "quantities must be greater than zero"}, status=400)
            # Remove previous order items
            OrderItem.objects.filter(pk__in=previous_order_items_ids).delete()

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


def delivery(request, delivery_id):
    """GET Delivery details"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    if request.method == "GET":
        return JsonResponse(d.serialize())
