const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {

  // Manage clicks on order list items
  document.querySelectorAll('.order-list-item').forEach(orderListItem => {
    orderListItem.addEventListener('click', () => {
      // highlight selected order list item
      document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
      orderListItem.classList.add('table-active');

      clearAlert();
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
  const orderViewTitle = document.querySelector('#order-view-title');
  const orderViewSubtitle = document.querySelector('#order-view-subtitle');
  const orderViewItems = document.querySelector('#order-items');
  const orderAmountSpan = document.querySelector('#order-amount');
  const saveIcon = document.querySelector('#save');
  const deleteIcon = document.querySelector('#delete');

  // hide order view while updating
  hide(orderView);

  // get delivery and order
  const delivery = await requestGetDelivery(deliveryUrl);
  const order = (orderUrl !== '') ? await requestGetOrder(orderUrl) : null;

  // update border
  if (order) {
    orderView.classList.replace('border-light', 'border-dark');
  } else {
    orderView.classList.replace('border-dark', 'border-light');
  }

  // update title and subtitle
  orderViewTitle.innerText = order ? 'Order for ' : 'New order for ';
  orderViewTitle.innerText += `${delivery.date} delivery`;
  orderViewSubtitle.innerText = order ? 'Can be updated until: ' : 'Last day to order: ';
  orderViewSubtitle.innerText += delivery.order_deadline;

  // Update order view items
  orderViewItems.innerHTML = '';
  // add a new row for each delivery product
  delivery.products.forEach(product => {
    const orderViewItem = document.createElement('tr');
    orderViewItem.className = "order-item";
    orderViewItem.dataset.productid = product.id;
    let itemQuantity = 0;
    let itemAmount = 0;
    // if product exists in order, use values from order
    if (order) {
      orderItem = order.items.find(item => item.product.id === product.id)
      if (orderItem) {
        itemQuantity = orderItem.quantity;
        itemAmount = parseFloat(orderItem.amount);
      }
    }
    orderViewItem.innerHTML = `
      <td>${product.name}</td>
      <td><span class="unit-price">${product.unit_price}</span> €</td>
      <td><input type="number" class="quantity form-control" value="${itemQuantity}" min="0"></td>
      <td><span class="amount">${itemAmount.toFixed(2)}</span> €</td>`;
    // set action on quantity input change
    quantityInput = orderViewItem.querySelector('.quantity').addEventListener('input', () => {
      clearAlert();
      updateOrderViewAmounts();
    })
    orderViewItems.append(orderViewItem);
  })

  // update total order amount
  let orderAmount = order ? parseFloat(order.amount) : 0;
  orderAmountSpan.innerText = orderAmount.toFixed(2);

  // update 'delete' and 'save' buttons
  if (order) {
    show(deleteIcon);
    saveIcon.innerText = 'Update Order'
  } else {
    hide(deleteIcon);
    saveIcon.innerText = 'Save Order'
  }

  // Finally show order view
  show(orderView);
}

function updateOrderViewAmounts() {
  // Re-calculate order view amounts (items and total) according to items quantities

  const orderViewItems = document.querySelectorAll('.order-item');
  const orderTotalAmountSpan = document.querySelector('#order-amount');

  let orderTotalAmount = 0;
  orderViewItems.forEach(orderViewItem => {
    const unitPrice = orderViewItem.querySelector('.unit-price').innerText;
    const quantity = orderViewItem.querySelector('.quantity').value;
    const itemAmount = unitPrice * quantity;
    orderViewItem.querySelector('.amount').innerText = itemAmount.toFixed(2);
    orderTotalAmount += itemAmount;
  })

  orderTotalAmountSpan.innerText = orderTotalAmount.toFixed(2);
}

async function saveOrder() {
  // Create or Update order
  const selectedOrderListItem = document.querySelector('.table-active');
  const deliveryId = selectedOrderListItem.querySelector('.delivery').dataset.url.split('/').pop();
  const orderView = document.querySelector('#order-view');
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
      hide(orderView);
      document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
    } else {
      showAlert('errorSave');
    }
  } else {
    showAlert('errorItems');
  }

  function getOrderItems() {
    // Get order items from order-view
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
}

async function deleteOrder() {
  // delete selected order
  const selectedOrderListItem = document.querySelector('.table-active');
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const orderView = document.querySelector('#order-view');
  const deleteIcon = document.querySelector('#delete')

  const result = await requestDeleteOrder(orderUrl);

  if (result.message) {
    showAlert('successRemove');

    // reset items quantities
    document.querySelectorAll('.order-item').forEach(orderViewItem => {
      orderViewItem.querySelector('.quantity').value = 0;
    });

    updateSelectedOrderListItem(null, '');
    hide(orderView);
    document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
  }
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
  show(alert);

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
  hide(alert);
  alert.innerText = '';
}

function show(element) {
  element.classList.replace('d-none', 'block');
}

function hide(element) {
  element.classList.replace('block', 'd-none');
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