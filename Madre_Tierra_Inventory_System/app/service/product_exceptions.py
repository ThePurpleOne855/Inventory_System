class ProductNotFoundError(Exception):
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product not found by id: {product_id}")


class ProductInUseError(Exception):
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product is used by one or more order items: {product_id}")
