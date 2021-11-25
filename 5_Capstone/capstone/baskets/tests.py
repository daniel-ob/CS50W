from decimal import Decimal
from datetime import date, datetime, timedelta
import json
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Max
from django.test import Client, TestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.common.by import By

from .models import User, Producer, Product, Delivery, Order, OrderItem


class BasketsTestCase(TestCase):
    """Define shared setUp() for Baskets app tests"""

    def setUp(self):
        # Create users
        self.u1 = User.objects.create_user(
            username="user1",
            first_name="test",
            last_name="user",
            email="user1@baskets.com",
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
        yesterday = today - timedelta(days=1)
        # closed delivery
        self.d1 = Delivery.objects.create(date=today, order_deadline=yesterday, message="delivery 1")
        self.d1.products.set([self.product1, self.product2])
        # opened delivery
        self.d2 = Delivery.objects.create(date=tomorrow, order_deadline=today, message="delivery 2")
        self.d2.products.set([self.product1, self.product3])

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
        self.assertEqual(self.product1.deliveries.count(), 2)

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
        """Check that 'index' page contains only opened deliveries (deadline not passed)"""

        self.c.force_login(self.u1)
        response = self.c.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries_orders"]), 1)
        self.assertEqual(response.context["deliveries_orders"][0]["delivery"], self.d2)

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


class EndToEndWebPageTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        cls.SLEEP_TIME = 0.1

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        BasketsTestCase.setUp(self)

    def test_end_to_end(self):
        """End to end test: Login, Create order, Update order, Delete order"""

        login_url = self.live_server_url + reverse("login")
        index_url = self.live_server_url + reverse("index")

        # Log-in
        # ------
        self.driver.get(login_url)
        username_input = self.driver.find_element(By.NAME, "username")
        username_input.send_keys("user1")
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys("secret")
        login_button = self.driver.find_element(By.CLASS_NAME, "btn")
        login_button.click()

        self.assertEqual(self.driver.current_url, index_url)
        self.assertEqual(self.driver.find_element(By.ID, "username").text, self.u1.username)

        # Create order
        # ------------
        # 'Next orders' page (index). Check date of first delivery
        first_delivery = self.driver.find_element(By.CLASS_NAME, "delivery")
        first_delivery_date = first_delivery.text
        self.assertEqual(first_delivery_date, self.d2.date.isoformat())

        # Check that first delivery has no order
        first_order = self.driver.find_element(By.CLASS_NAME, "order")
        first_order_url = first_order.get_attribute("data-url")
        self.assertEqual(first_order_url, "")

        # Open new order view
        first_delivery.click()
        time.sleep(self.SLEEP_TIME)

        # Check available products
        items = self.driver.find_elements(By.CLASS_NAME, "order-item")
        self.assertEqual(len(items), self.d2.products.count())

        quantity = 2
        expected_order_amount = 0
        for idx, item in enumerate(items):
            name = item.find_element(By.CLASS_NAME, "product-name")
            unit_price = item.find_element(By.CLASS_NAME, "unit-price")
            quantity_input = item.find_element(By.CLASS_NAME, "quantity")
            amount = item.find_element(By.CLASS_NAME, "amount")
            expected_product_name = self.d2.products.all()[idx].name
            expected_unit_price = self.d2.products.all()[idx].unit_price

            # check product details
            self.assertEqual(name.text, expected_product_name)
            self.assertEqual(unit_price.text, str(expected_unit_price))
            self.assertEqual(amount.text, "0.00")

            # set item quantity and check item amount
            quantity_input.clear()
            quantity_input.send_keys(quantity)
            expected_amount = quantity * expected_unit_price
            self.assertEqual(amount.text, str(expected_amount))

            expected_order_amount += expected_amount

        # Check total order amount
        order_amount = self.driver.find_element(By.ID, "order-amount")
        self.assertEqual(order_amount.text, str(expected_order_amount))

        # Save order and check that order list is updated
        save_button = self.driver.find_element(By.ID, "save")
        save_button.click()
        time.sleep(self.SLEEP_TIME)
        self.assertEqual(first_order.text, str(expected_order_amount) + " €")

        # Check that order has been created in database
        self.assertEqual(self.u1.orders.last().amount, expected_order_amount)
        first_order_url = first_order.get_attribute("data-url")
        self.assertNotEqual(first_order_url, "")

        # Update order
        # ------------
        first_delivery.click()
        time.sleep(self.SLEEP_TIME)

        first_item_unit_price = Decimal(self.driver.find_element(By.CLASS_NAME, "unit-price").text)
        first_item_quantity_input = self.driver.find_element(By.CLASS_NAME, "quantity")
        first_item_amount = self.driver.find_element(By.CLASS_NAME, "amount")
        order_amount = self.driver.find_element(By.ID, "order-amount")

        initial_first_item_quantity = int(first_item_quantity_input.get_attribute("value"))
        initial_order_amount = Decimal(order_amount.text)

        # Increase by 1 item quantity
        new_quantity = initial_first_item_quantity + 1
        first_item_quantity_input.clear()
        first_item_quantity_input.send_keys(new_quantity)

        expected_amount = new_quantity * first_item_unit_price
        self.assertEqual(first_item_amount.text, str(expected_amount))
        expected_order_amount = initial_order_amount + first_item_unit_price
        self.assertEqual(order_amount.text, str(expected_order_amount))

        # Update order and check that it has been updated in database
        save_button.click()
        time.sleep(self.SLEEP_TIME)
        self.assertEqual(self.u1.orders.last().amount, expected_order_amount)

        # Delete order
        # ------------
        first_delivery.click()
        time.sleep(self.SLEEP_TIME)
        delete_button = self.driver.find_element(By.ID, "delete")
        delete_button.click()
        time.sleep(self.SLEEP_TIME)
        first_order_url = first_order.get_attribute("data-url")
        self.assertEqual(first_order_url, "")
