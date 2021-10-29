const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
  let selectedOrderListItem = null;

  // Manage clicks on order list items
  document.querySelectorAll('.order-list-item').forEach(item => {
    item.addEventListener('click', () => {
      if (item !== selectedOrderListItem) {
        selectedOrderListItem = item;

        clearAlert();

        // highlight selected order list item
        document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
        selectedOrderListItem.classList.add('table-active');

        updateOrderView(selectedOrderListItem);
      }
    })
  })

  // Manage clicks on 'Save Order' button
  document.querySelector('#save').addEventListener('click', () => saveOrder());
})

async function updateOrderView(selectedOrderListItem) {
  // Update order view with selected order information. If order method is 'post', display an empty order form.

  const deliveryUrl = selectedOrderListItem.querySelector('.delivery').dataset.url;
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const orderMethod = selectedOrderListItem.querySelector('.order').dataset.method;

  const delivery = await requestGetDelivery(deliveryUrl);
  const order = (orderMethod === 'put') ? await requestGetOrder(orderUrl) : null;

  // show order view
  document.querySelector('#order-view').classList.replace('d-none', 'block');

  // display delivery details
  document.querySelector('#order-delivery-date').innerText = delivery.date;
  document.querySelector('#order-deadline').innerText = delivery.order_deadline;

  // clear order items
  const orderViewItems = document.querySelector('#order-items');
  orderViewItems.innerHTML = '';

  // add a row for each delivery product
  delivery.products.forEach(product => {
    const orderViewItem = document.createElement('tr');
    orderViewItem.className = "order-item";
    orderViewItem.dataset.productid = product.id;

    quantity = 0;
    amount = 0;
    // if product exists in order, use values from order
    if (order !== null) {
      orderItem = order.items.find(item => item.product.id === product.id)
      if (orderItem !== undefined) {
        quantity = orderItem.quantity;
        amount = orderItem.amount;
      }
    }

    orderViewItem.innerHTML = `
      <td>${product.name}</td>
      <td><span class="unit-price">${product.unit_price}</span> €</td>
      <td><input type="number" class="quantity form-control" value="${quantity}" min="0"></td>
      <td><span class="amount">${amount}</span> €</td>`;

    // set action on quantity input change
    quantityInput = orderViewItem.querySelector('.quantity').addEventListener('input', () => {
      clearAlert();
      updateOrderViewAmounts(orderViewItem);
    })

    orderViewItems.append(orderViewItem);
  })

  // update total order amount
  document.querySelector('#order-amount').innerText = (order !== null) ? order.amount : 0;
}

function updateOrderViewAmounts(orderViewItem) {
  // Item amount
  const unitPrice = orderViewItem.querySelector('.unit-price').innerText;
  const quantity = orderViewItem.querySelector('.quantity').value;
  const itemAmount = unitPrice * quantity;
  orderViewItem.querySelector('.amount').innerText = itemAmount.toFixed(2)

  // Total order amount
  let totalAmount = 0;
  const orderViewItems = document.querySelectorAll('.order-item');
  orderViewItems.forEach(orderViewItem => {
    const itemAmount = parseFloat(orderViewItem.querySelector('.amount').innerText);
    totalAmount += itemAmount;
  })
  document.querySelector('#order-amount').innerText = totalAmount.toFixed(2);
}

async function saveOrder() {
  // Create or Update order

  const selectedOrderListItem = document.querySelector('.table-active');
  const method = selectedOrderListItem.querySelector('.order').dataset.method;
  const url = selectedOrderListItem.querySelector('.order').dataset.url;
  const deliveryId = selectedOrderListItem.querySelector('.delivery').dataset.url.split('/').pop();
  const orderAmount = document.querySelector('#order-amount').innerText;

  let savedOrderUrl = null;

  let orderItems = getOrderItems()
  if (orderItems.length > 0) {
    if (method === 'post') {
      result = await requestCreateOrder(url, deliveryId, orderItems);
      savedOrderUrl = result.url; // new order url
    } else {
      result = await requestUpdateOrder(url, orderItems);
      savedOrderUrl = url;  // order url remains the same
    }
    console.log(result);

    // if order amount sent by back-end matches front-end one, order has been successfully created
    if (result.amount === orderAmount) {
      showAlert('success');
      updateSelectedOrderListItem(savedOrderUrl);
    } else {
      showAlert('errorSave');
    }
  } else {
    showAlert('errorItems');
  }
}

function getOrderItems() {
  // Get order items from order view

  let orderItems = []
  orderViewItems = document.querySelectorAll('.order-item')
  orderViewItems.forEach(orderViewItem => {
    let quantity = orderViewItem.querySelector('.quantity').value;
    // valid order items have quantity greater than 0
    if (quantity > 0) {
      orderItems.push({
        'product_id': orderViewItem.dataset.productid,
        'quantity': quantity
      });
    }
  })
  return orderItems;
}

async function requestGetDelivery(deliveryUrl) {
  // Send 'GET' request to get delivery details

  const response = await fetch(deliveryUrl)
  const responseJSON = await response.json();
  console.log('delivery', responseJSON);
  return responseJSON;
}

async function requestGetOrder(orderUrl) {
  // Send 'GET' request to get order details

  const response = await fetch(orderUrl)
  const responseJSON = await response.json();
  console.log('order', responseJSON);
  return responseJSON;
}

async function requestCreateOrder(url, deliveryId, orderItems) {
  // Send 'POST' request to create order in back-end

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      'delivery_id': deliveryId,
      'items': orderItems,
    })
  })
  const responseJSON = await response.json();
  return responseJSON;
}

async function requestUpdateOrder(orderUrl, orderItems) {
  // Send 'PUT' request to update order in back-end

  const response = await fetch(orderUrl, {
    method: 'PUT',
    headers: {
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      'items': orderItems,
    })
  })
  const responseJSON = await response.json();
  return responseJSON;
}

function updateSelectedOrderListItem(newOrderUrl) {
  // After order saving, update order list item: amount, url and method

  const selectedOrderListItem = document.querySelector('.table-active');
  const selectedOrder = selectedOrderListItem.querySelector('.order');
  const orderAmount = document.querySelector('#order-amount').innerText;

  selectedOrder.innerText = orderAmount + ' €';
  selectedOrder.dataset.url = newOrderUrl;
  selectedOrder.dataset.method = 'put';
}

function showAlert(alertType) {
  alert = document.querySelector('#alert');
  alert.classList.replace('d-none', 'block');

  switch(alertType) {
    case 'success':
      alert.classList.remove('text-danger');
      alert.classList.add('text-success');
      alert.innerText = 'Order has been successfully saved';
      break;
    case 'errorSave':
      alert.classList.remove('text-success');
      alert.classList.add('text-danger');
      alert.innerText = 'An error occurred when trying to save order. Please reload page and try again';
      break;
    case 'errorItems':
      alert.classList.remove('text-success');
      alert.classList.add('text-danger');
      alert.innerText = 'At least one item must have quantity greater than 0';
      break;
  }
}

function clearAlert() {
  alert = document.querySelector('#alert');
  alert.classList.replace('block', 'd-none');
  alert.innerText = '';
}

// from https://docs.djangoproject.com/en/3.2/ref/csrf/
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}