const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {

  // Manage clicks on order list items
  document.querySelectorAll('.order-list-item').forEach(orderListItem => {
    orderListItem.addEventListener('click', () => {
      // highlight selected order list item
      document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
      orderListItem.classList.add('table-active');

      updateOrderView(orderListItem);
    })
  })

  // Manage clicks on 'Save' and 'Delete' order buttons
  document.querySelector('#save').addEventListener('click', () => saveOrder());
  document.querySelector('#delete').addEventListener('click', () => deleteOrder());

})

async function updateOrderView(selectedOrderListItem) {
  // Update order view with selected order information. If no order exists, display an empty order form.

  const deliveryUrl = selectedOrderListItem.querySelector('.delivery').dataset.url;
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const orderView = document.querySelector('#order-view');
  const deliveryDate = document.querySelector('#order-delivery-date');
  const orderDeadline = document.querySelector('#order-deadline');
  const orderViewItems = document.querySelector('#order-items');
  const orderAmount = document.querySelector('#order-amount');
  const deleteIcon = document.querySelector('#delete');

  // hide order view while updating
  orderView.classList.replace('block', 'd-none');

  // reset order-view
  clearAlert();
  orderViewItems.innerHTML = '';

  // get delivery and order
  const delivery = await requestGetDelivery(deliveryUrl);
  const order = (orderUrl !== '') ? await requestGetOrder(orderUrl) : null;

  // display delivery details
  deliveryDate.innerText = delivery.date;
  orderDeadline.innerText = delivery.order_deadline;

  // add a new row for each delivery product
  delivery.products.forEach(product => {
    const orderViewItem = document.createElement('tr');
    orderViewItem.className = "order-item";
    orderViewItem.dataset.productid = product.id;

    quantity = 0;
    amount = 0;
    // if product exists in order, use values from order
    if (order) {
      orderItem = order.items.find(item => item.product.id === product.id)
      if (orderItem) {
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
      updateOrderViewAmounts();
    })

    orderViewItems.append(orderViewItem);
  })

  // update total order amount
  orderAmount.innerText = order ? order.amount : 0;

  // show/hide 'delete' button
  if (order) {
    deleteIcon.classList.replace('d-none', 'block');
  } else {
    deleteIcon.classList.replace('block', 'd-none');
  }

  // Finally show order view
  orderView.classList.replace('d-none', 'block');
}

function updateOrderViewAmounts() {
  // Items amount
  const orderViewItems = document.querySelectorAll('.order-item');
  orderViewItems.forEach(orderViewItem => {
    const unitPrice = orderViewItem.querySelector('.unit-price').innerText;
    const quantity = orderViewItem.querySelector('.quantity').value;
    const itemAmount = unitPrice * quantity;
    orderViewItem.querySelector('.amount').innerText = itemAmount.toFixed(2)
  })

  // Total order amount
  let totalAmount = 0;
  orderViewItems.forEach(orderViewItem => {
    const itemAmount = parseFloat(orderViewItem.querySelector('.amount').innerText);
    totalAmount += itemAmount;
  })
  document.querySelector('#order-amount').innerText = totalAmount.toFixed(2);
}

async function saveOrder() {
  // Create or Update order
  const selectedOrderListItem = document.querySelector('.table-active');
  const deliveryId = selectedOrderListItem.querySelector('.delivery').dataset.url.split('/').pop();
  const orderAmount = document.querySelector('#order-amount').innerText;
  const deleteIcon = document.querySelector('#delete')
  let orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;

  let orderItems = getOrderItems()
  if (orderItems.length > 0) {
    if (orderUrl === '') {
      result = await requestCreateOrder(deliveryId, orderItems);
      orderUrl = result.url; // new order url
    } else {
      result = await requestUpdateOrder(orderUrl, orderItems);
    }

    // if order amount sent by back-end matches front-end one, order has been successfully created
    if (result.amount === orderAmount) {
      showAlert('successSave');
      updateSelectedOrderListItem(orderAmount, orderUrl);
      deleteIcon.classList.replace('d-none', 'block');
    } else {
      showAlert('errorSave');
    }
  } else {
    showAlert('errorItems');
  }
}

async function deleteOrder() {
  const selectedOrderListItem = document.querySelector('.table-active');
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const deleteIcon = document.querySelector('#delete')

  const result = await requestDeleteOrder(orderUrl);

  if (result.message) {
    showAlert('successRemove');

    // reset items quantities
    document.querySelectorAll('.order-item').forEach(orderViewItem => {
      orderViewItem.querySelector('.quantity').value = 0;
    });

    updateOrderViewAmounts();
    deleteIcon.classList.replace('block', 'd-none');
    updateSelectedOrderListItem(null, '');
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

async function requestCreateOrder(deliveryId, orderItems) {
  // Send 'POST' request to create order in back-end
  const createOrderUrl = document.querySelector('#create-order').dataset.url;
  const response = await fetch(createOrderUrl, {
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
  console.log(responseJSON);
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
  console.log(responseJSON);
  return responseJSON;
}

async function requestDeleteOrder(orderUrl) {
  // Send 'DELETE' order request to back-end
  const response = await fetch(orderUrl, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrftoken
    }
  })
  const responseJSON = await response.json();
  console.log(responseJSON);
  return responseJSON;
}

function updateSelectedOrderListItem(orderAmount, orderUrl) {
  const selectedOrderListItem = document.querySelector('.table-active');
  const selectedOrder = selectedOrderListItem.querySelector('.order');

  selectedOrder.innerText = orderAmount ? orderAmount + ' €' : 'No order recorded';
  selectedOrder.dataset.url = orderUrl;
}

function showAlert(alertType) {
  alert = document.querySelector('#alert');
  alert.classList.replace('d-none', 'block');

  switch(alertType) {
    case 'successSave':
      alert.classList.remove('text-danger');
      alert.classList.add('text-success');
      alert.innerText = 'Order has been successfully saved';
      break;
    case 'successRemove':
      alert.classList.remove('text-danger');
      alert.classList.add('text-success');
      alert.innerText = 'Order has been successfully removed';
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