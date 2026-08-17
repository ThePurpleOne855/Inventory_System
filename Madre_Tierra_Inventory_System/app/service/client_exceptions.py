class ClientNotFoundByIdError(Exception):
    def __init__(self, client_id: int):
        self.client_id = client_id
        super().__init__(f"Client Not Found By Id: {client_id}") 


class ClientNotFoundByEmailError(Exception):
    def __init__(self, client_email):
        self.client_email = client_email
        super().__init__(f"Client Not Found By EmailL {client_email}")