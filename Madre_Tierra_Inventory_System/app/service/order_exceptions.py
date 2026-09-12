class OrderNotFoundError(Exception):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"Order Not Found By Id: {order_id}")


class ProductNotFoundError(Exception):
    def __init__(self, product_id):
        self.product_id = product_id
        super().__init__(f"Product Not Found By Id: {product_id}")
