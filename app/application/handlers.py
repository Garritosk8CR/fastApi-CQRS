from app.application.commands import CreateElectionCommand
from app.infrastructure.models import Election
from app.infrastructure.database import SessionLocal

class CreateElectionHandler:
    def handle(self, command):
        # Create a new session for the database
        with SessionLocal() as db:
            # Check if election with the same name already exists
            if db.query(Election).filter(Election.name == command.name).first():
                raise ValueError("Election name already exists!")

            # Create and persist the new election
            new_election = Election(
                name=command.name,
                candidates=",".join(command.candidates),
                votes=",".join(["0"] * len(command.candidates))
            )
            db.add(new_election)
            db.commit()


class CommandBus:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, command_type, handler):
        self.handlers[command_type] = handler

    def handle(self, command):
        command_type = type(command)
        if command_type not in self.handlers:
            raise ValueError(f"No handler registered for {command_type}")
        handler = self.handlers[command_type]
        handler.handle(command)

# Initialize and register the CreateElectionHandler
command_bus = CommandBus()
command_bus.register_handler(CreateElectionCommand, CreateElectionHandler())
