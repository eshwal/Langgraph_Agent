class EntityNotFoundError(Exception):

    def __init__(self,entity,identifier):
        self.message = f'{entity} entity with Id {identifier} does not exists.'
        super().__init__(self.message)


class EntityAlreadyExistsError(Exception):

    def __init__(self, entity,identifier):
        self.message = f'{entity} entity with ID {identifier} already exists.'
        super().__init__(self.message)