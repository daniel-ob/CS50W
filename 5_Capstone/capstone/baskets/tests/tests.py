from datetime import date, timedelta
import json

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Max
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from selenium import webdriver

from baskets.models import User, Producer, Product, Delivery, Order, OrderItem
from baskets.tests.pageobjects import LoginPage


class BasketsTestCase(TestCase):
    """Define shared setUp() for Baskets app tests"""

    def setUp(self):
        # Create users
        self.u1 = User.objects.create_user(
            username="user1",
            first_name="test",
            last_name="user",
            email="user1@baskets.com",
            phone="0123456789",
            address="my street, my city",
            password="secret"
        )
        self.u2 = User.objects.create(username="user2")

        # Create producers
        self.producer1 = Producer.objects.create(name="producer1")
        self.producer2 = Producer.objects.create(name="producer2")

        # Create products
        self.product1 = Product.objects.create(producer=self.producer1, name="product1", unit_price=0.5)
        self.product2 = Product.objects.create(producer=self.producer1, name="product2", unit_price=1)
        self.product3 = Product.objects.create(producer=self.producer2, name="product3", unit_price=1.15)

        # Create deliveries
        today = date.today()
        tomorrow = today + timedelta(days=1)
        after_tomorrow = today + timedelta(days=2)
        yesterday = today - timedelta(days=1)
        # closed delivery
        self.d1 = Delivery.objects.create(date=today, order_deadline=yesterday, message="delivery 1")
        self.d1.products.set([self.product1, self.product2])
        # opened deliveries
        self.d2 = Delivery.objects.create(date=tomorrow, order_deadline=today, message="delivery 2")
        self.d2.products.set([self.product1, self.product3])
        self.d3 = Delivery.objects.create(date=after_tomorrow, order_deadline=tomorrow, message="delivery 3")
        self.d3.products.set([self.product1, self.product3])

        # Create orders
        self.o1 = Order.objects.create(user=self.u1, delivery=self.d1, message="order 1")  # closed
        self.o2 = Order.objects.create(user=self.u2, delivery=self.d2, message="order 2")  # opened

        # Create order items
        self.oi1 = OrderItem.objects.create(order=self.o1, product=self.product1, quantity=4)
        self.oi2 = OrderItem.objects.create(order=self.o1, product=self.product2, quantity=1)
        # invalids
        self.oi3 = OrderItem.objects.create(order=self.o2, product=self.product2, quantity=1)
        self.oi4 = OrderItem.objects.create(order=self.o2, product=self.product1, quantity=0)

        # Create test client
        self.c = Client()


class ModelsTestCase(BasketsTestCase):

    def test_producer_products_count(self):
        self.assertEqual(self.producer1.products.count(), 2)
        self.assertEqual(self.producer2.products.count(), 1)

    def test_product_deliveries_count(self):
        self.assertEqual(self.product1.deliveries.count(), 3)

    def test_user_orders_count(self):
        self.assertEqual(self.u1.orders.count(), 1)

    def test_delivery_orders_count(self):
        self.assertEqual(self.d1.orders.count(), 1)

    def test_delivery_deadline_auto(self):
        """Check that delivery.order_deadline is set to ORDER_DEADLINE_DAYS_BEFORE days before delivery.date
        when it's not specified at delivery creation"""

        yesterday = date.today() - timedelta(days=1)
        d = Delivery.objects.create(date=yesterday)
        self.assertEqual(d.order_deadline, d.date - timedelta(days=self.d1.ORDER_DEADLINE_DAYS_BEFORE))

    def test_delivery_deadline_custom(self):
        self.assertEqual(self.d2.order_deadline, date.today())

    def test_order_items_count(self):
        self.assertEqual(self.o1.items.count(), 2)

    def test_items_amount(self):
        self.assertEqual(self.oi1.amount, 2)
        self.assertEqual(self.oi2.amount, 1)

    def test_order_amount(self):
        self.assertEqual(self.o1.amount, 3)

    def test_order_amount_persistence(self):
        """Test that saved order doesn't change its amount when updating its related products price"""

        initial_order_amount = self.o1.amount
        initial_product1_unit_price = self.product1.unit_price
        initial_product2_unit_price = self.product2.unit_price

        # Update related products unit price
        self.product1.unit_price = 1
        self.product2.unit_price = 2.5

        # Order total amount must not change
        self.assertEqual(self.o1.amount, initial_order_amount)

        # Reset products unit price
        self.product1.unit_price = initial_product1_unit_price
        self.product2.unit_price = initial_product2_unit_price

    def test_order_items_amount_persistence(self):
        """Test that order item doesn't change its amount when updating its related product unit price"""

        initial_order_item_amount = self.oi1.amount
        initial_product1_unit_price = self.product1.unit_price

        # Update related product unit price
        self.product1.unit_price = 1

        # Order item amount must not change
        self.assertEqual(self.oi1.amount, initial_order_item_amount)

        # Reset product unit price
        self.product1.unit_price = initial_product1_unit_price

    def test_valid_order_item(self):
        """Check that order item is valid if product is available in delivery and quantity is greater than 0"""

        self.assertEqual(self.oi1.is_valid(), True)
        self.assertEqual(self.oi2.is_valid(), True)

    def test_invalid_order_item_product(self):
        """Check that order item is invalid if product is not available in delivery"""

        self.assertEqual(self.oi3.is_valid(), False)

    def test_invalid_order_item_quantity(self):
        """Check that order item is invalid if quantity is not greater than 0"""

        self.assertEqual(self.oi4.is_valid(), False)


class APITestCase(BasketsTestCase):
    def test_order_list_get(self):
        """Check that user can get the list of all of its orders through API"""

        # log-in user1
        self.c.force_login(self.u1)

        user_order_list_expected_json = [
            {
                "id": self.o1.id,
                "delivery_id": self.o1.delivery.id
            }
        ]

        response = self.c.get(reverse("orders"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), user_order_list_expected_json)

    def test_order_list_get_not_authenticated(self):
        """Check that a non authenticated user gets an "Unauthorized" error when trying to get order list through API"""

        response = self.c.get(reverse("orders"))

        self.assertEqual(response.status_code, 401)

    def test_order_creation(self):
        """Check that user can create an order through API"""

        self.c.force_login(self.u1)

        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery_id": self.d2.id,
            "items": [
                {
                    "product_id": self.product1.id,
                    "quantity": 1
                },
                {
                    "product_id": self.product3.id,
                    "quantity": 2
                }
            ],
            "message": "One product1 and two product3"
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.json()["amount"]), 2.80)
        self.assertEqual(response.json()["url"], reverse("order", args=[Order.objects.last().id]))

        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial + 1)

        new_order = Order.objects.last()
        self.assertEqual(new_order.delivery, self.d2)
        self.assertEqual(new_order.message, "One product1 and two product3")
        self.assertEqual(new_order.items.count(), 2)

    def test_order_creation_not_authenticated(self):
        """Check that a non authenticated user gets an "Unauthorized" error when trying to create order through API"""

        orders_count_initial = Order.objects.count()

        order_json = {
            "delivery_id": self.d2.id,
            "items": [
                {
                    "product_id": self.product1.id,
                    "quantity": 1
                }
            ]
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), orders_count_initial)

    def test_order_creation_deadline_passed(self):
        """Check that when a user tries to create an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not created"""

        self.c.force_login(self.u2)
        u2_initial_orders_count = self.u1.orders.count()

        order_json = {
            "delivery_id": self.d1.id,
            "items": [
                {
                    "product_id": self.product1.id,
                    "quantity": 1
                }
            ]
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u2.orders.count(), u2_initial_orders_count)

    def test_order_creation_second_order_for_delivery(self):
        """Check that user receives a 'Bad request' error when trying to create a second order for a given delivery"""

        self.c.force_login(self.u2)
        user2_orders_count_initial = self.u2.orders.count()

        # user already has an order for d2
        order_json = {
            "delivery_id": self.d2.id
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u2.orders.count(), user2_orders_count_initial)

    def test_order_creation_no_item(self):
        """Check that user receives a 'bad request' error when trying to create an order without items"""

        self.c.force_login(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        order_json = {
            "delivery_id": self.d2.id,
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_order_creation_invalid_product(self):
        """Check that user receives an error 400 when creating an order with a product not available in delivery"""

        self.c.force_login(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        # product2 is not available in d2
        order_json = {
            "delivery_id": self.d2.id,
            "items": [
                {
                    "product_id": self.product1.id,
                    "quantity": 1
                },
                {
                    "product_id": self.product2.id,
                    "quantity": 1
                }
            ],
        }
        response = self.c.post(reverse("orders"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_order_get(self):
        """Check that user can retrieve one of its orders"""

        self.c.force_login(self.u1)

        o1_expected_json = {
            'delivery_id': 1,
            'items': [
                {
                    'product': {
                        'id': 1,
                        'name': 'product1',
                        'unit_price': '0.50'
                    },
                    'quantity': 4,
                    'amount': '2.00'
                },
                {
                    'product': {
                        'id': 2,
                        'name': 'product2',
                        'unit_price': '1.00'
                    },
                    'quantity': 1,
                    'amount': '1.00'
                }
            ],
            'amount': '3.00',
            'message': 'order 1'
        }

        response = self.c.get(reverse("order", args=[self.o1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), o1_expected_json)

    def test_order_get_invalid_user(self):
        """Check that user1 gets a 'Forbidden' error when trying to retrieve an user2 order"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("order", args=[self.u2.orders.last().id]))
        self.assertEqual(response.status_code, 403)

    def test_order_update(self):
        """Check that user can update one of its orders through API"""

        # log-in user1
        self.c.force_login(self.u1)

        # Create an order for this test
        order = Order.objects.create(user=self.u1, delivery=self.d2, message="test order")
        order_item1 = OrderItem.objects.create(order=order, product=self.product1, quantity=1)
        order_item2 = OrderItem.objects.create(order=order, product=self.product3, quantity=3)

        updated_order_json = {
            "items": [
                {
                    "product_id": self.product3.id,
                    "quantity": 2
                }
            ],
            "message": "order updated"
        }
        response = self.c.put(reverse("order", args=[self.u1.orders.last().id]),
                              data=json.dumps(updated_order_json),
                              content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.json()['amount']), 2.30)

        order.refresh_from_db()
        self.assertEqual(order.message, "order updated")
        self.assertEqual(order.items.count(), 1)

    def test_order_update_deadline_passed(self):
        """Check that when a user tries to update an order for a delivery which deadline is passed:
        - A 'Bad request' error is received
        - Order is not updated"""

        self.c.force_login(self.u2)

        # Create an order for this test
        order = Order.objects.create(user=self.u2, delivery=self.d1, message="test order")
        order_item1 = OrderItem.objects.create(order=order, product=self.product1, quantity=1)
        order_item2 = OrderItem.objects.create(order=order, product=self.product2, quantity=1)

        updated_order_json = {
            "items": [
                {
                    "product_id": self.product1.id,
                    "quantity": 2
                }
            ],
            "message": "order updated"
        }
        response = self.c.put(reverse("order", args=[order.id]),
                              data=json.dumps(updated_order_json),
                              content_type="application/json")

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.items.first().quantity, order_item1.quantity)

    def test_order_update_invalid_product(self):
        """Check that, when trying to update an order with a non existing product:
        - A 'Not found' error is received
        - Order is not updated"""

        # log-in user1
        self.c.force_login(self.u1)

        # Create an order
        order = Order.objects.create(user=self.u1, delivery=self.d2, message="test order")
        order_item1 = OrderItem.objects.create(order=order, product=self.product1, quantity=1)
        order_item2 = OrderItem.objects.create(order=order, product=self.product3, quantity=3)

        invalid_product_id = Product.objects.all().aggregate(Max("id"))["id__max"] + 1
        updated_order_json = {
            "items": [
                {
                    "product_id": invalid_product_id,
                    "quantity": 2
                }
            ],
            "message": "try to update"
        }
        response = self.c.put(reverse("order", args=[order.id]),
                              data=json.dumps(updated_order_json),
                              content_type="application/json")

        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.items.all()[0].product.id, self.product1.id)
        self.assertEqual(order.items.all()[0].quantity, 1)
        self.assertEqual(order.items.all()[1].product.id, self.product3.id)
        self.assertEqual(order.items.all()[1].quantity, 3)
        self.assertEqual(order.message, "test order")

    def test_order_delete(self):
        """Check that user can delete one of its orders, including all of its items, through API"""

        self.c.force_login(self.u1)

        # Create an order for this test
        order = Order.objects.create(user=self.u1, delivery=self.d2)
        order_item1 = OrderItem.objects.create(order=order, product=self.product1, quantity=1)
        order_item2 = OrderItem.objects.create(order=order, product=self.product3, quantity=3)

        response = self.c.delete(reverse("order", args=[order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(order, self.u1.orders.all())
        self.assertNotIn(order_item1, OrderItem.objects.all())
        self.assertNotIn(order_item2, OrderItem.objects.all())

    def test_order_delete_not_authenticated(self):
        """Check that a not authenticated user gets an "Unauthorized" error when trying to delete order through API"""

        response = self.c.delete(reverse("order", args=[self.o1.id]))

        self.assertEqual(response.status_code, 401)
        self.assertIn(self.o1, Order.objects.all())

    def test_delivery_list_get(self):
        """Check that next deliveries (opened) list can be retrieved through API"""

        deliveries_list_expected_json = [
            {
                "id": self.d2.id,
                "date": self.d2.date.isoformat()
            },
            {
                "id": self.d3.id,
                "date": self.d3.date.isoformat()
            }
        ]
        response = self.c.get(reverse("deliveries"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), deliveries_list_expected_json)

    def test_delivery_get(self):
        """Check that a delivery can be retrieved through API"""

        today = date.today()
        yesterday = today - timedelta(days=1)
        d1_expected_json = {
            "date": today.isoformat(),
            "order_deadline": yesterday.isoformat(),
            "products": [
                {
                    "id": 1,
                    "name": "product1",
                    "unit_price": "0.50"
                },
                {
                    "id": 2,
                    "name": "product2",
                    "unit_price": "1.00"
                }
            ],
            "message": "delivery 1",
            "is_open": False
        }

        response = self.c.get(reverse("delivery", args=[self.d1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), d1_expected_json)


class WebPageTestCase(BasketsTestCase):
    def test_index_opened_deliveries(self):
        """Check that 'index' page contains only opened deliveries (deadline not passed) in chronological order"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 2)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d2)
        self.assertEqual(response.context["deliveries_orders"][1]["delivery"], self.d3)

    def test_order_history_closed_deliveries(self):
        """Check that 'order history' page contains only closed deliveries (deadline passed)"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("order_history"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 1)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d1)

    def test_profile_page(self):
        """Check that 'profile' page shows user information"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["username"], self.u1.username)
        self.assertEqual(response.context["form"].initial["first_name"], self.u1.first_name)
        self.assertEqual(response.context["form"].initial["last_name"], self.u1.last_name)
        self.assertEqual(response.context["form"].initial["email"], self.u1.email)
        self.assertEqual(response.context["form"].initial["phone"], self.u1.phone)
        self.assertEqual(response.context["form"].initial["address"], self.u1.address)


class FunctionalTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.driver.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        BasketsTestCase.setUp(self)

    def test_end_to_end(self):
        """End-to-end test: Login, Create order, Update order, Delete order"""

        # Log in
        # ------
        login_page = LoginPage(self.driver, self.live_server_url)
        login_page.load()
        self.assertEqual(login_page.title, _("Login"))
        login_page.set_username("user1")
        login_page.set_password("secret")
        next_orders_page = login_page.submit()  # next_orders_page is from type IndexPage

        # Check that 'Next orders' page is correctly loaded
        self.assertEqual(next_orders_page.title, _("Next Orders"))
        self.assertEqual(next_orders_page.username, self.u1.username)

        # Create order
        # ------------
        selected_order_index = 0
        # Check that delivery has no order
        order_url = next_orders_page.get_order_url(selected_order_index)
        order_amount = next_orders_page.get_order_amount(selected_order_index)
        self.assertIsNone(order_url)
        self.assertIsNone(order_amount)

        # Open new order view
        next_orders_page.open_order(selected_order_index)
        delivery_date = next_orders_page.get_order_delivery_date(selected_order_index)
        order_view_title = next_orders_page.get_order_view_title()
        self.assertIn(delivery_date, order_view_title)

        # Check available products count
        items_count = next_orders_page.get_items_count()
        self.assertEqual(items_count, self.d2.products.count())

        expected_order_amount = 0
        for index in range(items_count):
            expected_product_name = self.d2.products.all()[index].name
            expected_unit_price = self.d2.products.all()[index].unit_price

            item_name = next_orders_page.get_item_name(index)
            item_unit_price = next_orders_page.get_item_unit_price(index)

            # check product details
            self.assertEqual(item_name, expected_product_name)
            self.assertEqual(item_unit_price, expected_unit_price)

            # check item initial amount
            item_amount = next_orders_page.get_item_amount(index)
            self.assertEqual(item_amount, 0.00)

            # set item quantity and check new amount
            quantity = 2
            self.assertEqual(next_orders_page.item_quantity_is_writable(index), True)
            next_orders_page.set_item_quantity(index, quantity)
            expected_amount = quantity * item_unit_price
            item_amount = next_orders_page.get_item_amount(index)
            self.assertEqual(item_amount, expected_amount)

            expected_order_amount += item_amount

        # Check total order amount
        order_view_amount = next_orders_page.get_order_view_amount()
        self.assertEqual(order_view_amount, expected_order_amount)

        # Save order and check that order list is updated
        next_orders_page.save_order()
        order_url = next_orders_page.get_order_url(selected_order_index)
        order_amount = next_orders_page.get_order_amount(selected_order_index)
        self.assertIsNotNone(order_url)
        self.assertEqual(order_amount, order_view_amount)

        # Check that order has been created in database
        self.assertEqual(self.u1.orders.last().amount, order_amount)

        # Update order
        # ------------
        next_orders_page.open_order(selected_order_index)

        item_index = 0
        item_unit_price = next_orders_page.get_item_unit_price(item_index)
        initial_item_quantity = next_orders_page.get_item_quantity(item_index)
        initial_order_view_amount = next_orders_page.get_order_view_amount()

        # Increase by 1 item quantity
        new_quantity = initial_item_quantity + 1
        next_orders_page.set_item_quantity(item_index, new_quantity)

        expected_amount = new_quantity * item_unit_price
        item_amount = next_orders_page.get_item_amount(item_index)
        self.assertEqual(item_amount, expected_amount)
        expected_order_amount = initial_order_view_amount + item_unit_price
        order_view_amount = next_orders_page.get_order_view_amount()
        self.assertEqual(order_view_amount, expected_order_amount)

        # Update order and check that it has been correctly updated in order list and database
        next_orders_page.save_order()
        order_amount = next_orders_page.get_order_amount(selected_order_index)
        self.assertEqual(order_amount, order_view_amount)
        self.assertEqual(self.u1.orders.last().amount, order_amount)

        # Delete order
        # ------------
        next_orders_page.open_order(selected_order_index)
        next_orders_page.delete_order()
        order_url = next_orders_page.get_order_url(selected_order_index)
        order_amount = next_orders_page.get_order_amount(selected_order_index)
        self.assertIsNone(order_url)
        self.assertIsNone(order_amount)
