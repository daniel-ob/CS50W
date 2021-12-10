from decimal import Decimal

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait


class BasePage(object):
    """Base page object"""

    TITLE = (By.TAG_NAME, "h2")
    USERNAME = (By.ID, "username")

    url = None

    def __init__(self, driver, live_server_url):
        self.driver = driver
        self.live_server_url = live_server_url

    def load(self):
        self.driver.get(self.live_server_url + self.url)

    @property
    def title(self):
        return self.driver.find_element(*self.TITLE).text

    @property
    def username(self):
        return self.driver.find_element(*self.USERNAME).text

    def fill_form_by_name(self, name, value):
        field = self.driver.find_element(By.NAME, name)
        field.send_keys(value)


class LoginPage(BasePage):
    """Abstracts interactions with login.html template"""

    LOGIN_BUTTON = (By.CLASS_NAME, "btn")

    url = reverse("login")

    def set_username(self, username):
        self.fill_form_by_name("username", username)

    def set_password(self, password):
        self.fill_form_by_name("password", password)

    def submit(self):
        login_button = self.driver.find_element(*self.LOGIN_BUTTON)
        login_button.click()
        return IndexPage(self.driver, self.live_server_url)


class IndexPage(BasePage):
    """Abstracts interactions with index.html template"""

    # page locators
    DELIVERIES = (By.CLASS_NAME, "delivery")
    ORDERS = (By.CLASS_NAME, "order")
    SELECTED_ORDER = (By.CLASS_NAME, "table-active")
    ORDER_VIEW = (By.ID, "order-view")
    ORDER_VIEW_TITLE = (By.ID, "order-view-title")
    ITEMS = (By.CLASS_NAME, "order-view-item")
    ITEM_NAMES = (By.CLASS_NAME, "product-name")
    ITEM_UNIT_PRICES = (By.CLASS_NAME, "unit-price")
    ITEM_QUANTITIES = (By.CLASS_NAME, "quantity")
    ITEM_AMOUNTS = (By.CLASS_NAME, "amount")
    ORDER_AMOUNT = (By.ID, "order-amount")
    SAVE_BUTTON = (By.ID, "save")
    DELETE_BUTTON = (By.ID, "delete")

    MAX_WAIT_SECONDS = 2

    url = reverse("index")

    def get_order_url(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        url = order.get_attribute("data-url")
        return url if url else None

    def get_order_amount(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        return Decimal(order.text.split()[0]) if order.text.count("€") else None

    def get_order_delivery_date(self, index):
        delivery = self.driver.find_elements(*self.DELIVERIES)[index]
        return delivery.text

    def open_order(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        order.click()
        # wait until order view is displayed
        wait = WebDriverWait(self.driver, self.MAX_WAIT_SECONDS)
        order_view = self.driver.find_element(*self.ORDER_VIEW)
        wait.until(ec.visibility_of(order_view))

    def get_order_view_title(self):
        return self.driver.find_element(*self.ORDER_VIEW_TITLE).text

    def get_items_count(self):
        items = self.driver.find_elements(*self.ITEMS)
        return len(items)

    def get_item_name(self, index):
        return self.driver.find_elements(*self.ITEM_NAMES)[index].text

    def get_item_unit_price(self, index):
        return Decimal(self.driver.find_elements(*self.ITEM_UNIT_PRICES)[index].text)

    def get_item_quantity(self, index):
        quantity_elem = self.driver.find_elements(*self.ITEM_QUANTITIES)[index]
        if self.item_quantity_is_writable(index):
            return int(quantity_elem.get_attribute("value"))
        else:
            return int(quantity_elem.text)

    def get_item_amount(self, index):
        return Decimal(self.driver.find_elements(*self.ITEM_AMOUNTS)[index].text)

    def item_quantity_is_writable(self, index):
        item_quantity = self.driver.find_elements(*self.ITEM_QUANTITIES)[index]
        tag = item_quantity.tag_name
        # Quantity is an <input> on 'Next Orders' page and a <td> on 'Order History' page
        return True if tag == "input" else False

    def set_item_quantity(self, index, quantity):
        quantity_input = self.driver.find_elements(*self.ITEM_QUANTITIES)[index]
        quantity_input.clear()
        quantity_input.send_keys(quantity)

    def get_order_view_amount(self):
        return Decimal(self.driver.find_element(*self.ORDER_AMOUNT).text)

    def save_order(self):
        save_button = self.driver.find_element(*self.SAVE_BUTTON)
        save_button.click()
        self.wait_until_order_view_closed()

    def delete_order(self):
        delete_button = self.driver.find_element(*self.DELETE_BUTTON)
        delete_button.click()
        self.wait_until_order_view_closed()

    def wait_until_order_view_closed(self):
        wait = WebDriverWait(self.driver, self.MAX_WAIT_SECONDS)
        order_view = self.driver.find_element(*self.ORDER_VIEW)
        wait.until(ec.invisibility_of_element(order_view))
