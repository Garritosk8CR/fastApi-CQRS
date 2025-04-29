from datetime import timedelta
import traceback

from fastapi import HTTPException
from app.application.queries import CandidateSupportQuery, ElectionSummaryQuery, ElectionTurnoutQuery, GetAllElectionsQuery, GetElectionDetailsQuery, GetElectionResultsQuery, GetUserByEmailQuery, GetUserByIdQuery, GetUserProfileQuery, GetVotingPageDataQuery, HasVotedQuery, InactiveVotersQuery, ListAdminsQuery, ListUsersQuery, ParticipationByRoleQuery, ResultsBreakdownQuery, TopCandidateQuery, UserStatisticsQuery, UsersByRoleQuery, VoterDetailsQuery, VotingStatusQuery
from app.application.query_bus import query_bus
from app.application.commands import CastVoteCommand, CheckVoterExistsQuery, CreateElectionCommand, EditUserCommand, EndElectionCommand, LoginUserCommand, RegisterVoterCommand, UpdateUserRoleCommand, UserSignUp
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
        
class GetUserProfileHandler:
    def handle(self, query: GetUserProfileQuery):
        with SessionLocal() as db:  # Initialize database session inside handler
            user_repository = UserRepository(db)

            # Fetch user details
            user = user_repository.get_user_by_id(query.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            return user  # Return full user object
        
class ListUsersHandler:
    def handle(self, query: ListUsersQuery):
        with SessionLocal() as db:  # Initialize database session inside handler
            user_repository = UserRepository(db)
        # Call the repository method
        users = user_repository.get_users(query.page, query.page_size)
        return users
    
class UpdateUserRoleHandler:
    def handle(self, command: UpdateUserRoleCommand):
        with SessionLocal() as db:
            user_repository = UserRepository(db)
        
        # Retrieve the user
        user = user_repository.get_user_by_id(command.user_id)
        if not user:
            raise ValueError(f"User with ID {command.user_id} not found.")

        # Update the role
        user_repository.update_role(user, command.role)
        return {"message": f"Role for user {command.user_id} updated to {command.role}"}

class HasVotedHandler:
    def handle(self, query: HasVotedQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)

            # Fetch the voter record
            voter = voter_repository.get_voter_by_user_id(query.user_id)
            if not voter:
                raise ValueError(f"User with ID {query.user_id} not found.")

            # Return the voting status
            return {"user_id": query.user_id, "has_voted": voter.has_voted}

class GetUserByIdHandler:
    def handle(self, query: GetUserByIdQuery):
        with SessionLocal() as db:
            user_repository = UserRepository(db)

        # Fetch the user by ID
            user = user_repository.get_user_by_id(query.user_id)
            if not user:
                raise ValueError(f"User with ID {query.user_id} not found.")

            # Return user details as a dictionary
            return {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            }

class ListAdminsHandler:
    def handle(self, query: ListAdminsQuery):
        with SessionLocal() as db:
            user_repository = UserRepository(db)
            print(f"Command in ListAdminsHandler: {query.page}, {query.page_size}")
        # Fetch admins with pagination
            admins = user_repository.get_users_by_role(
                role="admin", 
                page=query.page, 
                page_size=query.page_size
            )
            print(f"admin list: {admins}")
            return [
                {
                    "id": admin.id, 
                    "name": admin.name, 
                    "email": admin.email
                } for admin in admins
            ]
        
class UsersByRoleHandler:

    def handle(self, query: UsersByRoleQuery):
        with SessionLocal() as db:
            user_repository = UserRepository(db)
            # Fetch users with the specified role and pagination
            users = user_repository.get_users_by_role(query.role, query.page, query.page_size)
            return [{"id": user.id, "name": user.name, "email": user.email, "role": user.role} for user in users]
        
class VotingStatusHandler:
    def handle(self, query: VotingStatusQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)

            # Fetch users grouped by their voting status
            voted = voter_repository.get_voters_by_status(has_voted=True)
            not_voted = voter_repository.get_voters_by_status(has_voted=False)

            return {
                "voted": [{"id": voter.user.id, "name": voter.user.name, "email": voter.user.email} for voter in voted],
                "not_voted": [{"id": voter.user.id, "name": voter.user.name, "email": voter.user.email} for voter in not_voted],
            }
        


class CandidateSupportHandler:
    def handle(self, query: CandidateSupportQuery):
        with SessionLocal() as db:
            election_repository = ElectionRepository(db)

            # Fetch candidate support data
            candidate_support = election_repository.get_candidate_support(query.election_id)

            # Format the result
            return candidate_support
        
class ElectionTurnoutHandler:
    def handle(self, query: ElectionTurnoutQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)
            election_repository = ElectionRepository(db)

            # Fetch all eligible voters
            eligible_voters = voter_repository.get_all_voters_v2()
            participated_voters = voter_repository.get_voters_who_voted()

            # check if election exists
            election = election_repository.get_election_by_id(query.election_id)
            if not election:
                raise ValueError(f"Election with ID {query.election_id} not found.")

            # Calculate turnout
            total_voters = len(eligible_voters)
            total_participated = len(participated_voters)
            turnout_percentage = (total_participated / total_voters * 100) if total_voters > 0 else 0

            return {
                "election_id": query.election_id,  # For consistency
                "total_voters": total_voters,
                "voted": total_participated,
                "turnout_percentage": round(turnout_percentage, 2)
            }
        
class VoterDetailsHandler:
    def handle(self, query: VoterDetailsQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)

            # Fetch voter details
            voter = voter_repository.get_voter_by_id(query.voter_id)
            if not voter:
                raise ValueError(f"Voter with ID {query.voter_id} not found.")

            # Format the result
            return {
                "voter_id": voter.id,
                "user": {
                    "id": voter.user.id,
                    "name": voter.user.name,
                    "email": voter.user.email,
                    "role": voter.user.role,
                },
                "has_voted": voter.has_voted
            }
        
class UserStatisticsHandler:
    def handle(self, query: UserStatisticsQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)
            user_repository = UserRepository(db)
        
            # Fetch data for statistics
            total_users = user_repository.get_total_users()
            voters_count = voter_repository.get_total_voters()
            users_voted_count = voter_repository.get_voters_who_voted_count()
            role_distribution = user_repository.get_users_by_roles()

            # Calculate percentage of users who have voted
            voting_percentage = (users_voted_count / voters_count * 100) if voters_count > 0 else 0

            # Format the result
            return {
                "total_users": total_users,
                "total_voters": voters_count,
                "voting_percentage": round(voting_percentage, 2),
                "roles": role_distribution,
            }
        
class ElectionSummaryHandler:
    def handle(self, query: ElectionSummaryQuery):
        with SessionLocal() as db:
            election_repository = ElectionRepository(db)

            # Fetch all elections
            elections = election_repository.get_all_elections()

            # Aggregate summary data for each election
            summary = []
            for election in elections:
                # Use ElectionTurnoutHandler to get the correct turnout percentage
                turnout_query = ElectionTurnoutQuery(election_id=election.id)
                turnout_data = ElectionTurnoutHandler().handle(turnout_query)
                print(f"Turnout data for election {election.id}: {turnout_data}")
                turnout_percentage = turnout_data["turnout_percentage"]

                total_votes = sum(map(int, election.votes.split(","))) if election.votes else 0

                summary.append({
                    "election_id": election.id,
                    "name": election.name,
                    "turnout_percentage": turnout_percentage,
                    "total_votes": total_votes,
                })

            return summary

class TopCandidateHandler:
    def handle(self, query: TopCandidateQuery):
        with SessionLocal() as db:
            election_repository = ElectionRepository(db)

            # Fetch the election data
            election = election_repository.get_election_by_id(query.election_id)
            if not election:
                raise ValueError(f"Election with ID {query.election_id} not found.")

            # Parse candidates and votes
            candidates = election.candidates.split(",")
            votes = list(map(int, election.votes.split(",")))

            # Determine the top candidate
            max_votes = max(votes)
            max_index = votes.index(max_votes)
            top_candidate = candidates[max_index]

            # Return the result
            return {
                "election_id": election.id,
                "top_candidate": top_candidate,
                "votes": max_votes
            }
        
class ParticipationByRoleHandler:
    def handle(self, query: ParticipationByRoleQuery):
        with SessionLocal() as db:
            user_repository = UserRepository(db)
            voter_repository = VoterRepository(db)

            # Fetch voters and their roles
            voters = voter_repository.get_all_voters()  # Get all voters, no election filter
            user_roles = user_repository.get_users_by_roles()
            print(f"User roles: {user_roles}")
            print(f"Voters: {voters}")
            # Prepare participation stats by role
            participation = {}
            for role, count in user_roles:
                print(f"Processing role: {role}")
                try:
                    print(f"Voter objects: {voters} - Role: {role}")
                    role_voters = [voter for voter in voters if voter[0].role == role]
                    total_role_voters = len(role_voters)
                    voted_role_voters = len([voter for voter in role_voters if voter[1].has_voted])

                    print(f"Role: {role}, Total voters: {total_role_voters}, Voted voters: {voted_role_voters}")

                    participation[role] = {
                        "total": total_role_voters,
                        "voted": voted_role_voters,
                        "percentage": round((voted_role_voters / total_role_voters * 100), 2) if total_role_voters > 0 else 0
                    }
                except Exception as e:
                    print(f"Error processing role {role}: {e}")
                    

            return {
                "election_id": query.election_id,  # Placeholder for consistency
                "participation": participation
            }
        
class InactiveVotersHandler:
    def handle(self, query: InactiveVotersQuery):
        with SessionLocal() as db:
            voter_repository = VoterRepository(db)

            # Fetch inactive voters
            inactive_voters = voter_repository.get_inactive_voters()

            # Format the result
            return [
                {
                    "voter_id": voter.id,
                    "user_id": voter.user_id    
                }
                for voter in inactive_voters
            ]
        
class ResultsBreakdownHandler:
    def handle(self, query: ResultsBreakdownQuery):
        with SessionLocal() as db:
            election_repository = ElectionRepository(db)

            # Fetch the election data
            election = election_repository.get_election_by_id(query.election_id)
            if not election:
                raise ValueError(f"Election with ID {query.election_id} not found.")

            # Parse candidates and votes
            candidates = election.candidates.split(",")
            votes = list(map(int, election.votes.split(",")))

            # Calculate percentage breakdown
            total_votes = sum(votes)
            results = [
                {
                    "candidate": candidate,
                    "votes": vote,
                    "percentage": round((vote / total_votes * 100), 2) if total_votes > 0 else 0
                }
                for candidate, vote in zip(candidates, votes)
            ]

            return {
                "election_id": election.id,
                "results": results
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
query_bus.register_handler(GetUserProfileQuery, GetUserProfileHandler())
query_bus.register_handler(HasVotedQuery, HasVotedHandler())
query_bus.register_handler(GetUserByIdQuery, GetUserByIdHandler())
query_bus.register_handler(ListAdminsQuery, ListAdminsHandler())
query_bus.register_handler(UsersByRoleQuery, UsersByRoleHandler())
query_bus.register_handler(VotingStatusQuery, VotingStatusHandler())
query_bus.register_handler(CandidateSupportQuery, CandidateSupportHandler())
query_bus.register_handler(ElectionTurnoutQuery, ElectionTurnoutHandler())
query_bus.register_handler(VoterDetailsQuery, VoterDetailsHandler())
query_bus.register_handler(UserStatisticsQuery, UserStatisticsHandler())
query_bus.register_handler(ElectionSummaryQuery, ElectionSummaryHandler())
query_bus.register_handler(TopCandidateQuery, TopCandidateHandler())
query_bus.register_handler(ParticipationByRoleQuery, ParticipationByRoleHandler())
query_bus.register_handler(InactiveVotersQuery, InactiveVotersHandler())
query_bus.register_handler(ResultsBreakdownQuery, ResultsBreakdownHandler())



