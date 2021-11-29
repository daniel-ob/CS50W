const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {

  // Manage clicks on order list items
  document.querySelectorAll('.order-list-item').forEach(orderListItem => {
    orderListItem.addEventListener('click', () => {
      highlightOrderListItem(orderListItem);
      clearAlert();
      updateOrderView(orderListItem);
    })
  })

  // Manage clicks on 'Save' and 'Delete' order buttons
  document.querySelector('#save').addEventListener('click', () => saveOrder());
  document.querySelector('#delete').addEventListener('click', () => deleteOrder());

})

async function updateOrderView(selectedOrderListItem) {
  // Load selected order-list-item in order view. If item has no order, display an empty order form.

  const deliveryUrl = selectedOrderListItem.querySelector('.delivery').dataset.url;
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const orderView = document.querySelector('#order-view');
  const orderViewTitle = document.querySelector('#order-view-title');
  const orderViewSubtitle = document.querySelector('#order-view-subtitle');
  const orderViewItemsContainer = document.querySelector('#order-items');
  const orderAmountSpan = document.querySelector('#order-amount');
  const saveIcon = document.querySelector('#save');
  const deleteIcon = document.querySelector('#delete');

  // hide order-view while updating
  hide(orderView);

  // get selected delivery and order
  const delivery = await requestGetDelivery(deliveryUrl);
  const order = (orderUrl !== '') ? await requestGetOrder(orderUrl) : null;

  orderViewItemsContainer.innerHTML = '';
  if (order) {
      orderView.classList.add('shadow');
      orderViewTitle.innerText = `Order for ${delivery.date} delivery`;
      if (delivery.is_open) {
        // order can be updated and deleted
        orderViewSubtitle.innerText = `Can be updated until ${delivery.order_deadline}`;
        newOrderViewItems(delivery);
        updateOrderViewItems(order);
        show(deleteIcon);
        saveIcon.innerText = 'Update Order'
        show(saveIcon);
      } else {
        // order in view-only mode
        orderViewSubtitle.innerText = '';
        addOrderViewItemsViewOnlyMode(order);
        hide(deleteIcon);
        hide(saveIcon);
      }
      orderAmountSpan.innerText = parseFloat(order.amount).toFixed(2);
  } else {
    // new order
    orderView.classList.remove('shadow');
    orderViewTitle.innerText = `New order for ${delivery.date} delivery`;
    orderViewSubtitle.innerText = `Last day to order: ${delivery.order_deadline}`;
    newOrderViewItems(delivery);
    hide(deleteIcon);
    saveIcon.innerText = 'Save Order'
    show(saveIcon);
    orderAmountSpan.innerText = parseFloat(0).toFixed(2);
  }

  // Finally show order-view
  show(orderView);

  function newOrderViewItems(delivery) {
    // add a new order-view-item for each delivery product
    delivery.products.forEach(product => {
      const orderViewItem = document.createElement('tr');
      orderViewItem.className = "order-item";
      orderViewItem.dataset.productid = product.id;
      orderViewItem.innerHTML = `
        <td class="product-name">${product.name}</td>
        <td><span class="unit-price">${product.unit_price}</span> €</td>
        <td><input type="number" class="quantity form-control" value="0" min="0"></td>
        <td><span class="amount">0.00</span> €</td>`;
      // set action on quantity input change
      quantityInput = orderViewItem.querySelector('.quantity').addEventListener('input', () => {
        clearAlert();
        updateOrderViewAmounts();
      })
      orderViewItemsContainer.append(orderViewItem);
    })
  }

  function updateOrderViewItems(order) {
    // update existing order-view-items with quantities and amounts from order
    const orderViewItems = orderViewItemsContainer.querySelectorAll('.order-item');
    orderViewItems.forEach(orderViewItem => {
      productId = orderViewItem.dataset.productid;
      orderItem = order.items.find(item => item.product.id == productId)
      if (orderItem) {
        const orderViewItemQuantity = orderViewItem.querySelector('.quantity');
        const orderViewItemAmount = orderViewItem.querySelector('.amount');
        orderViewItemQuantity.value = orderItem.quantity;
        orderViewItemAmount.innerText = parseFloat(orderItem.amount).toFixed(2);
      }
    })
  }

  function addOrderViewItemsViewOnlyMode(order) {
    // add a new order-view-item for each order item. 'View-only' mode
    order.items.forEach(item => {
      const orderViewItem = document.createElement('tr');
      orderViewItem.className = "order-item";
      orderViewItem.dataset.productid = item.product.id;
      orderViewItem.innerHTML = `
        <td class="product-name">${item.product.name}</td>
        <td><span class="unit-price">${item.product.unit_price}</span> €</td>
        <td>${item.quantity}</td>
        <td><span class="amount">${item.amount}</span> €</td>`;
      orderViewItemsContainer.append(orderViewItem);
    })
  }

  function updateOrderViewAmounts() {
    // Re-calculate order-view amounts (items and total) according to items quantities

    const orderViewItems = orderViewItemsContainer.querySelectorAll('.order-item');
    let orderAmount = 0;
    orderViewItems.forEach(orderViewItem => {
      const unitPrice = orderViewItem.querySelector('.unit-price').innerText;
      const quantity = orderViewItem.querySelector('.quantity').value;
      const itemAmount = unitPrice * quantity;
      orderViewItem.querySelector('.amount').innerText = itemAmount.toFixed(2);
      orderAmount += itemAmount;
    })
    orderAmountSpan.innerText = orderAmount.toFixed(2);
  }
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

    // if order amount sent by back-end matches front-end one, order has been successfully created/updated
    if (result.amount === orderAmount) {
      updateSelectedOrderListItem(orderAmount, orderUrl);
      highlightOrderListItem(null);
      restartAnimation(selectedOrderListItem.querySelector('.order'));
      showAlert('successSave');
      hide(orderView);
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
    updateSelectedOrderListItem(null, '');
    highlightOrderListItem(null);
    showAlert('successRemove');
    hide(orderView);
  }
}

async function requestGetDelivery(deliveryUrl) {
  // Send 'GET' request to get delivery details
  const response = await fetch(deliveryUrl)
  .catch(error => showAlert(error.message));
  const responseJSON = await response.json();
  console.log('delivery', responseJSON);
  return responseJSON;
}

async function requestGetOrder(orderUrl) {
  // Send 'GET' request to get order details
  const response = await fetch(orderUrl)
  .catch(error => showAlert(error.message));
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
  .catch(error => showAlert(error.message));
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
  .catch(error => showAlert(error.message));
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
  .catch(error => showAlert(error.message));
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

function highlightOrderListItem(orderListItem) {
  document.querySelectorAll('.order-list-item').forEach(order => order.classList.remove('table-active'));
  if (orderListItem) {
    orderListItem.classList.add('table-active');
  }
}

function showAlert(alertType) {
  alert = document.querySelector('#alert');
  clearAlert();
  switch(alertType) {
    case 'successSave':
      alert.classList.add('text-success');
      alert.innerText = 'Order has been successfully saved';
      break;
    case 'successRemove':
      alert.classList.add('text-success');
      alert.innerText = 'Order has been successfully removed';
      break;
    case 'errorSave':
      alert.classList.add('text-danger');
      alert.innerText = 'An error occurred when trying to save order. Please reload page and try again';
      break;
    case 'errorItems':
      alert.classList.add('text-danger');
      alert.innerText = 'At least one item must have quantity greater than 0';
      break;
    default:
      alert.classList.add('text-danger');
      alert.innerText = alertType;
  }
  show(alert);
  window.scrollTo(0, 0);
}

function clearAlert() {
  alert = document.querySelector('#alert');
  hide(alert);
  alert.classList.remove('text-success');
  alert.classList.remove('text-danger');
  alert.innerText = '';
}

function show(element) {
  element.classList.replace('d-none', 'block');
}

function hide(element) {
  element.classList.replace('block', 'd-none');
}

function restartAnimation(element) {
  element.classList.remove('run-animation');
  element.offsetWidth;  // trigger reflow
  element.classList.add('run-animation');
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