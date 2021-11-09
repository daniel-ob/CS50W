def delivery_to_order_form_book(delivery):
    bookdict = {}

    for order in delivery.orders.all():
        sheet_content = [
            ["Basket Order"],
            [""],
            ["User:", order.user.username],
            ["Delivery date:", str(delivery.date)],
            [""],
            ["Product", "Unit price", "Quantity", "Amount"]
        ]

        for item in order.items.all():
            sheet_content.append(
                [item.product.name, str(item.product.unit_price), item.quantity, str(item.amount)]
            )

        sheet_content.append(
            ["", "", "total", str(order.amount)]
        )

        bookdict[order.user.username] = sheet_content

    return bookdict
