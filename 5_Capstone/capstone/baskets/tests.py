import datetime
import json

from django.test import Client, TestCase
from django.urls import reverse

from .models import User, Producer, Product, Delivery, Order, OrderItem


class BasketsTestCase(TestCase):
    """Define shared setUp() for Baskets app tests"""

    def setUp(self):
        # Create users
        self.u1 = User.objects.create(username="user1")
        self.u2 = User.objects.create(username="user2")

        # Create producers
        self.producer1 = Producer.objects.create(name="producer1")
        self.producer2 = Producer.objects.create(name="producer2")

        # Create products
        self.product1 = Product.objects.create(producer=self.producer1, name="product1", unit_price=0.5)
        self.product2 = Product.objects.create(producer=self.producer1, name="product2", unit_price=1)
        self.product3 = Product.objects.create(producer=self.producer2, name="product3", unit_price=1.15)

        # Create deliveries
        self.d1 = Delivery.objects.create(date=datetime.date(2021, 11, 23), message="delivery 1")
        self.d1.products.set([self.product1, self.product2])

        self.d2 = Delivery.objects.create(date=datetime.date(2021, 12, 14), message="delivery 2")
        self.d2.products.set([self.product1, self.product3])

        # Create orders
        self.o1 = Order.objects.create(user=self.u1, delivery=self.d1, message="order 1")
        self.o2 = Order.objects.create(user=self.u2, delivery=self.d2, message="order 2")

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

    def test_orders_count(self):
        self.assertEqual(self.u1.orders.count(), 1)

    def test_delivery_orders_count(self):
        self.assertEqual(self.d1.orders.count(), 1)

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
    def test_order_creation(self):
        """Check that user1 can create an order through API"""

        # log-in user1
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
        response = self.c.post(reverse("create_order"), data=json.dumps(order_json), content_type="application/json")

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
        response = self.c.post(reverse("create_order"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), orders_count_initial)

    def test_order_creation_invalid_second_order_for_delivery(self):
        """Check that user1 receives an error 400 when trying to create a second order for a given delivery"""

        self.c.force_login(self.u1)
        user1_orders_count_initial = self.u1.orders.count()

        # user already has an order for d1
        order_json = {
            "delivery_id": self.d1.id
        }
        response = self.c.post(reverse("create_order"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_order_creation_invalid_product(self):
        """Check that user1 receives an error 400 when creating an order with a product not available in delivery"""

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
        response = self.c.post(reverse("create_order"), data=json.dumps(order_json), content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.u1.orders.count(), user1_orders_count_initial)

    def test_order_get(self):
        """Check that user1 can retrieve one of its orders"""

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
        """Check that user1 can update an order through API"""

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

        updated_order = self.u1.orders.last()
        self.assertEqual(updated_order.message, "order updated")
        self.assertEqual(updated_order.items.count(), 1)

    def test_order_delete(self):
        """Check that user1 can delete one of its orders, including all of its items, through API"""

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

    def test_delivery_get(self):
        """Check that a delivery can be retrieved through API"""

        d1_expected_json = {
            "date": "2021-11-23",
            "order_deadline": "2021-11-19",
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
            "message": "delivery 1"
        }

        response = self.c.get(reverse("delivery", args=[self.d1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), d1_expected_json)
