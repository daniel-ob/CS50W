import datetime

from django.test import Client, TestCase

from .models import User, Producer, Product, Delivery, Order, OrderItem


class BasketsTestCase(TestCase):

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
        self.d1 = Delivery.objects.create(date=datetime.date(2021, 11, 23))
        self.d1.products.set([self.product1, self.product2])

        self.d2 = Delivery.objects.create(date=datetime.date(2021, 12, 14))
        self.d2.products.set([self.product1, self.product3])

        # Create order
        self.o1 = Order.objects.create(user=self.u1, delivery=self.d1)

        # Create order items
        self.oi1 = OrderItem.objects.create(order=self.o1, product=self.product1, quantity=4)
        self.oi2 = OrderItem.objects.create(order=self.o1, product=self.product2, quantity=1)

        # Create test client
        self.c = Client()

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
