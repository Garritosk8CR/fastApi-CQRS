from datetime import timedelta

from fastapi import HTTPException
from app.application.queries import GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery, GetUserByEmailQuery, GetVotingPageDataQuery
from app.application.query_bus import query_bus
from app.application.commands import CastVoteCommand, CheckVoterExistsQuery, CreateElectionCommand, EditUserCommand, EndElectionCommand, LoginUserCommand, RegisterVoterCommand, UserSignUp
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.infrastructure.election_repo import ElectionRepository
from app.infrastructure.models import Election, User
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Voter
from app.infrastructure.user_repo import UserRepository
from app.infrastructure.voter_repo import VoterRepository
from app.security import create_access_token
from app.utils.password_utils import hash_password, verify_password

class CheckVoterExistsHandler:
    def handle(self, query: CheckVoterExistsQuery):
        with SessionLocal() as db:
            voter_exists = (
                db.query(User)
                .filter(User.id == query.voter_id, User.role == "voter")
                .first() is not None
            )
            return voter_exists


       
class GetAllElectionsHandler:
    def handle(self, query: GetAllElectionsQuery):
        with SessionLocal() as db:
            repo = ElectionRepository(db)
            elections = repo.get_all_elections()

            if not elections:  # No elections in the database
                return []  # Return an empty list instead of None

            return [
                {
                    "election_id": election.id,
                    "name": election.name,
                    "candidates": election.candidates.split(","),
                    "votes": list(map(int, election.votes.split(","))),
                    "status": election.status
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
            # Create a new user with the voter role
            new_user = User(id=command.voter_id, name=command.name, role="voter", password=hash_password(command.password))
            db.add(new_user)
            db.commit()
            
            # Create a voter linked to the user
            new_voter = Voter(user_id=new_user.id, has_voted=False)
            db.add(new_voter)
            db.commit()

        print(f"Voter registered: {new_user}")
        return new_user


class GetElectionResultsHandler:
    def handle(self, query: GetElectionResultsQuery):
        with SessionLocal() as db:
            repo = ElectionRepository(db)
            election = repo.get_election_by_id(query.election_id)

            if not election:
                raise ValueError("Election not found")

            # Process results
            results = {
                candidate: int(vote)
                for candidate, vote in zip(election.candidates.split(","), election.votes.split(","))
            }

            return results
        
class GetVotingPageDataHandler:
    def handle(self, query: GetVotingPageDataQuery):
        with SessionLocal() as db:
            voter_repo = VoterRepository(db)
            election_repo = ElectionRepository(db)

            # Fetch voters (joining User and Voter tables)
            voters = voter_repo.get_all_voters()  # Returns a list of (User, Voter) tuples
            elections = election_repo.get_all_elections()

            # Convert election objects to dictionaries
            election_data = [
                {
                    "election_id": election.id,
                    "name": election.name,
                    "candidates": election.candidates.split(",")  # Ensure candidates are in a list
                }
                for election in elections
            ]

            # Convert voter tuples to dictionaries
            voter_data = [
                {
                    "voter_id": user.id,
                    "name": user.name,
                    "has_voted": voter.has_voted
                }
                for user, voter in voters if not voter.has_voted  # Only include unvoted voters
            ]

            return {"voters": voter_data, "elections": election_data}


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

class EndElectionHandler:
    def handle(self, command: EndElectionCommand):
        with SessionLocal() as db:
            repo = ElectionRepository(db)
            election = repo.get_election_by_id(command.election_id)

            if not election:
                raise ValueError("Election not found")

            election.status = "completed"
            db.commit()

            return {"message": f"Election {command.election_id} has been ended successfully."}

class RegisterUserHandler:
    def handle(self, command: UserSignUp):
        with SessionLocal() as db:
            user_repo = UserRepository(db)
            print(f"Command: {command["name"]}, {command["email"]}, {command["password"]}")
            # Check if user already exists
            existing_user = user_repo.get_user_by_email(command["email"])
            if existing_user:
                raise ValueError("Email already exists!")

            # Use the repository to create a new user
            new_user = user_repo.create_user(
                name=command["name"],
                email=command["email"],
                password=command["password"]
            )

        return {"message": f"User {new_user.name} registered successfully as a voter!"}
    
class UserQueryHandler:
    def handle(self, query: GetUserByEmailQuery):
        with SessionLocal() as db:
            user_repository = UserRepository(db)
            return user_repository.get_user_by_email(query.email)
        

class AuthCommandHandler:
    def handle(self, command: LoginUserCommand):
        print(f"Command in AuthCommandHandler: {command.email}, {command.password}")
        with SessionLocal() as db:
            user_repository = UserRepository(db)

            # Retrieve user by email
            user = user_repository.get_user_by_email(command.email)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")

            # Verify password
            if not verify_password(command.password, user.password):
                raise HTTPException(status_code=401, detail="Invalid email or password")

            # Generate JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.email}, expires_delta=access_token_expires
            )

        return access_token
    
class EditUserHandler:
    def handle(self, user_id: int, update_data: EditUserCommand):

        with SessionLocal() as db:
            user_repository = UserRepository(db)               
        # Validate the user exists
            existing_user = user_repository.get_user_by_id(user_id)
            if not existing_user:
                raise HTTPException(status_code=404, detail="User not found")
            # Update the user
            try:
                updated_user = user_repository.update_user(user_id, update_data.model_dump())
                return updated_user
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        


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
command_bus.register_handler(EndElectionCommand, EndElectionHandler())
command_bus.register_handler(UserSignUp, RegisterUserHandler())
command_bus.register_handler(LoginUserCommand, AuthCommandHandler())
command_bus.register_handler(EditUserCommand, EditUserHandler())


# Create and register the query handler
query_bus.register_handler(CheckVoterExistsQuery, CheckVoterExistsHandler())
query_bus.register_handler(GetAllElectionsQuery, GetAllElectionsHandler())
query_bus.register_handler(GetElectionDetailsQuery, GetElectionDetailsHandler())
query_bus.register_handler(GetElectionResultsQuery, GetElectionResultsHandler())
query_bus.register_handler(GetVotingPageDataQuery, GetVotingPageDataHandler())
query_bus.register_handler(GetUserByEmailQuery, UserQueryHandler())


