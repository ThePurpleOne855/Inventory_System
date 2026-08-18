class ClientNotFoundByIdError(Exception):
    def __init__(self, client_id: int):
        self.client_id = client_id
        super().__init__(f"Client Not Found By Id: {client_id}") 


class ClientNotFoundByEmailError(Exception):
    def __init__(self, client_email):
        self.client_email = client_email
        super().__init__(f"Client Not Found By EmailL {client_email}")

class ClientNotFound(Exception):
    def __init__(self, params):
        self.params = params
        super().__init__(f"Client Not Found! Please verify client's information.")

class ClientNotFoundForUpdate(Exception):
    def __init__ (self, client_id,client_new_data):
        self.client_id = client_id
        self.client_new_data = client_new_data
        super().__init__(f"Client Not Found! Please verify the client's information before updating. \n Client ID: {client_id}.")