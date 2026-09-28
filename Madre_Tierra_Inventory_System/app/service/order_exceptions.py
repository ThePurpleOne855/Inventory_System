class OrderNotFoundError(Exception):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"Order Not Found By Id: {order_id}")


class ProductNotFoundError(Exception):
    def __init__(self, product_id):
        self.product_id = product_id
        super().__init__(f"Product Not Found By Id: {product_id}")


class InvalidOrderQuantityError(ValueError):
    def __init__(self, product_id: int, quantity: int):
        self.product_id = product_id
        self.quantity = quantity
        super().__init__(f"Order quantity must be positive for product {product_id}")


class InsufficientProductStockError(ValueError):
    def __init__(self, product_id: int, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )


class OrderProductNotFoundError(Exception):
    def __init__(self, order_product_id: int):
        self.order_product_id = order_product_id
        super().__init__(f"Order item not found by id: {order_product_id}")
