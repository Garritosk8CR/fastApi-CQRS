from app.application.commands import CheckVoterExistsQuery, CreateElectionCommand
from app.infrastructure.models import Election
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Voter
class CheckVoterExistsHandler:
    def handle(self, query: CheckVoterExistsQuery):
        with SessionLocal() as db:
            return db.query(Voter).filter(Voter.id == query.voter_id).first() is not None
        
class CreateElectionHandler:
    def handle(self, command):
        with SessionLocal() as db:
            # Ensure the election name is unique
            if db.query(Election).filter(Election.name == command.name).first():
                raise ValueError("Election name already exists!")

            # Create and save the new election
            new_election = Election(
                name=command.name,
                candidates=",".join(command.candidates),
                votes=",".join(["0"] * len(command.candidates))  # Initialize all votes to 0
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

# Create and register the command handler
command_bus = CommandBus()
command_bus.register_handler(CreateElectionCommand, CreateElectionHandler())

