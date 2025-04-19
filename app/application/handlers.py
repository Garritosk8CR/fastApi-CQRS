from app.application.queries import GetAllElectionsQuery
from app.application.query_bus import query_bus
from app.application.commands import CheckVoterExistsQuery, CreateElectionCommand, RegisterVoterCommand
from app.infrastructure.election_repo import ElectionRepository
from app.infrastructure.models import Election
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Voter
class CheckVoterExistsHandler:
    def handle(self, query: CheckVoterExistsQuery):
        with SessionLocal() as db:
            return db.query(Voter).filter(Voter.id == query.voter_id).first() is not None

       
class GetAllElectionsHandler:
    def handle(self, query: GetAllElectionsQuery):
        with SessionLocal() as db:
            elections = db.query(Election).all()
            return [
                {
                    "election_id": election.id,
                    "name": election.name,
                    "candidates": election.candidates.split(","),
                    "votes": list(map(int, election.votes.split(",")))
                }
                for election in elections
            ]

class CreateElectionHandler:
    def handle(self, command: CreateElectionCommand):
        with SessionLocal() as db:
            repo = ElectionRepository(db)

            # Create the election object
            new_election = Election(
                name=command.name,
                candidates=",".join(command.candidates),
                votes=",".join(["0"] * len(command.candidates))  # Initialize all votes to 0
            )

            # Save the election using the repository
            created_election = repo.create_election(new_election)

            # Return the created election
            return created_election


class RegisterVoterHandler:
    def handle(self, command: RegisterVoterCommand):
        # Delegate the existence check to the query bus
        query = CheckVoterExistsQuery(command.voter_id)
        voter_exists = query_bus.handle(query)  # Use query bus to check if voter exists

        # Raise an error if the voter already exists
        if voter_exists:
            raise ValueError("Voter ID already exists!")

        # Proceed with voter registration
        with SessionLocal() as db:
            new_voter = Voter(id=command.voter_id, name=command.name, has_voted=False)
            db.add(new_voter)
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
command_bus.register_handler(RegisterVoterCommand, RegisterVoterHandler())

# Create and register the query handler
query_bus.register_handler(CheckVoterExistsQuery, CheckVoterExistsHandler())
query_bus.register_handler(GetAllElectionsQuery, GetAllElectionsHandler())
