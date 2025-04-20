from app.application.queries import GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery
from app.application.query_bus import query_bus
from app.application.commands import CastVoteCommand, CheckVoterExistsQuery, CreateElectionCommand, RegisterVoterCommand
from app.infrastructure.election_repo import ElectionRepository
from app.infrastructure.models import Election
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Voter
from app.infrastructure.voter_repo import VoterRepository

class CheckVoterExistsHandler:
    def handle(self, query: CheckVoterExistsQuery):
        with SessionLocal() as db:
            return db.query(Voter).filter(Voter.id == query.voter_id).first() is not None

       
class GetAllElectionsHandler:
    def handle(self, query: GetAllElectionsQuery):
        with SessionLocal() as db:
            elections = db.query(Election).all()

            if not elections:  # No elections in the database
                return []  # Return an empty list instead of None

            return [
                {
                    "election_id": election.id,
                    "name": election.name,
                    "candidates": election.candidates.split(","),
                    "votes": list(map(int, election.votes.split(",")))
                }
                for election in elections
            ]


class GetElectionDetailsHandler:
    def handle(self, query: GetElectionDetailsQuery):
        with SessionLocal() as db:
            repo = ElectionRepository(db)
            election = repo.get_election_by_id(query.election_id)

            if not election:
                raise ValueError("Election not found")

            return {
                "election_id": election.id,
                "name": election.name,
                "candidates": election.candidates.split(","),
                "votes": list(map(int, election.votes.split(",")))
            }

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
            print(f"Created election with ID: {created_election.id}")
            
            # Return the object as a dictionary
            created_election_dict = {
                "election_id": created_election.id,
                "name": created_election.name,
                "candidates": created_election.candidates.split(","),
                "votes": list(map(int, created_election.votes.split(",")))
            }
            print(f"Election created: {created_election_dict}")
            return created_election_dict



class RegisterVoterHandler:
    def handle(self, command: RegisterVoterCommand):
        query = CheckVoterExistsQuery(command.voter_id)
        voter_exists = query_bus.handle(query)

        if voter_exists:
            raise ValueError("Voter ID already exists!")

        with SessionLocal() as db:
            new_voter = Voter(id=command.voter_id, name=command.name, has_voted=False)
            db.add(new_voter)
            db.commit()
            db.refresh(new_voter)

        print(f"Voter registered: {new_voter}")

        return new_voter  # Optionally return the voter object

class GetElectionResultsHandler:
    def handle(self, query: GetElectionResultsQuery):
        with SessionLocal() as db:
            # Fetch the election by ID
            election = db.query(Election).filter(Election.id == query.election_id).first()

            if not election:
                raise ValueError("Election not found")

            # Process results
            results = {
                candidate: int(vote)
                for candidate, vote in zip(election.candidates.split(","), election.votes.split(","))
            }

            return results

class CastVoteHandler:
    def handle(self, command: CastVoteCommand):
        with SessionLocal() as db:
            voter_repo = VoterRepository(db)
            election_repo = ElectionRepository(db)

            # Fetch the voter
            voter = voter_repo.get_voter_by_id(command.voter_id)
            if not voter:
                raise ValueError("Voter not found")
            if voter.has_voted:
                raise ValueError("Voter has already voted")

            # Fetch the election dynamically using election_id
            election = election_repo.get_election_by_id(command.election_id)
            if not election:
                raise ValueError("Election not found")

            # Cast the vote
            election.increment_vote(command.candidate)
            voter.has_voted = True
            db.commit()

            return {
                "candidate": command.candidate,
                "election_name": election.name,
            }


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
        
        # Return the result from the handler
        return handler.handle(command)




# Create and register the command handler
command_bus = CommandBus()
command_bus.register_handler(CreateElectionCommand, CreateElectionHandler())
command_bus.register_handler(RegisterVoterCommand, RegisterVoterHandler())
command_bus.register_handler(CastVoteCommand, CastVoteHandler())

# Create and register the query handler
query_bus.register_handler(CheckVoterExistsQuery, CheckVoterExistsHandler())
query_bus.register_handler(GetAllElectionsQuery, GetAllElectionsHandler())
query_bus.register_handler(GetElectionDetailsQuery, GetElectionDetailsHandler())
query_bus.register_handler(GetElectionResultsQuery, GetElectionResultsHandler())
