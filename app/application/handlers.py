import csv
from datetime import datetime, timedelta
import io
import math
import traceback

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import numpy as np
import pandas as pd
from app.application.queries import AnomalyDetectionQuery, CandidateSupportQuery, CorrelationAnalyticsQuery, DashboardAnalyticsQuery, ElectionSummaryQuery, ElectionTurnoutQuery, EnhancedNeuralNetworkPredictiveAnalyticsQuery, EnhancedPredictiveSubscriptionAnalyticsQuery, ExportElectionResultsQuery, GeolocationAnalyticsQuery, GeolocationTrendsQuery, GetAlertsQuery, GetAlertsWSQuery, GetAllElectionsQuery, GetAuditLogsQuery, GetCandidateByIdQuery, GetCandidateVoteDistributionQuery, GetCandidatesQuery, GetDetailedHistoricalComparisonsQuery, GetDetailedHistoricalComparisonsWithExternalQuery, GetElectionDetailsQuery, GetElectionResultsQuery, GetElectionSummaryQuery, GetFeedbackByElectionQuery, GetFeedbackBySeverityQuery, GetFeedbackCategoryAnalyticsQuery, GetFeedbackExportQuery, GetHistoricalTurnoutTrendsQuery, GetIntegrityScoreQuery, GetNotificationsQuery, GetNotificationsSummaryQuery, GetObserverByIdQuery, GetObserverTrustScoresQuery, GetObserversQuery, GetPollingStationQuery, GetPollingStationsByElectionQuery, GetSeasonalTurnoutPredictionQuery, GetSentimentAnalysisQuery, GetSentimentTrendQuery, GetSeverityDistributionQuery, GetSubscriptionAnalyticsQuery, GetSubscriptionsQuery, GetTimeBasedVotingPatternsQuery, GetTimePatternsQuery, GetTopObserversQuery, GetTurnoutConfidenceQuery, GetTurnoutPredictionQuery, GetUserByEmailQuery, GetUserByIdQuery, GetUserProfileQuery, GetVotesByElectionQuery, GetVotesByVoterQuery, GetVotingPageDataQuery, HasVotedQuery, HistoricalPollingStationTrendsQuery, InactiveVotersQuery, ListAdminsQuery, ListUsersQuery, ParticipationByRoleQuery, PollingStationAnalyticsQuery, PredictiveSubscriptionAnalyticsQuery, PredictiveVoterTurnoutQuery, RealTimeElectionSummaryQuery, ResultsBreakdownQuery, SegmentSubscriptionAnalyticsQuery, SubscriptionConversionMetricsQuery, TimeSeriesSubscriptionAnalyticsQuery, TopCandidateQuery, UserStatisticsQuery, UsersByRoleQuery, VoterDetailsQuery, VotingStatusQuery
from app.application.query_bus import query_bus
from app.application.commands import BulkUpdateSubscriptionsCommand, CastVoteCommand, CastVoteCommandv2, CheckVoterExistsQuery, CreateAlertCommand, CreateAuditLogCommand, CreateCandidateCommand, CreateElectionCommand, CreateObserverCommand, CreatePollingStationCommand, DeleteCandidateCommand, DeleteObserverCommand, DeletePollingStationCommand, EditUserCommand, EndElectionCommand, LoginUserCommand, MarkAllNotificationsReadCommand, MarkNotificationReadCommand, RegisterVoterCommand, SubmitFeedbackCommand, UpdateAlertCommand, UpdateCandidateCommand, UpdateObserverCommand, UpdatePollingStationCommand, UpdateSubscriptionCommand, UpdateUserRoleCommand, UserSignUp
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.infrastructure.alert_repo import AlertRepository
from app.infrastructure.audit_log_repo import AuditLogRepository
from app.infrastructure.candidate_repo import CandidateRepository
from app.infrastructure.election_repo import ElectionRepository
from app.infrastructure.models import Election, User, VoterUploadQuery
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import Voter
from app.infrastructure.notification_repo import NotificationRepository
from app.infrastructure.observer_feedback_repo import ObserverFeedbackRepository
from app.infrastructure.observer_repo import ObserverRepository
from app.infrastructure.polling_station_repo import PollingStationRepository
from app.infrastructure.subscription_event_repo import SubscriptionEventRepository
from app.infrastructure.subscription_repo import SubscriptionRepository
from app.infrastructure.user_repo import UserRepository
from app.infrastructure.vote_repo import VoteRepository
from app.infrastructure.voter_repo import VoterRepository
from app.security import create_access_token
from app.utils.password_utils import hash_password, verify_password
from datetime import timedelta
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from keras.optimizers import Adam

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
                    "percentage": math.floor(vote / total_votes * 100) if total_votes > 0 else 0
                }
                for candidate, vote in zip(candidates, votes)
            ]

            return {
                "election_id": election.id,
                "results": results
            }
        
class CreatePollingStationHandler:
    def handle(self, command: CreatePollingStationCommand):
        with SessionLocal() as db:
            repository = PollingStationRepository(db)
            return repository.create_polling_station(command.name, command.location, command.election_id, command.capacity)
    
class GetPollingStationHandler:
    def handle(self, query: GetPollingStationQuery):
        with SessionLocal() as db:
            repository = PollingStationRepository(db)
            station = repository.get_polling_station_by_id(query.station_id)
            if not station:
                raise ValueError(f"Polling station with ID {query.station_id} not found.")
            return station
        
class GetPollingStationsByElectionHandler:
    def handle(self, query: GetPollingStationsByElectionQuery):
        with SessionLocal() as db:
            repository = PollingStationRepository(db)
            return repository.get_polling_stations_by_election(query.election_id)
        
class UpdatePollingStationHandler:
    def handle(self, command: UpdatePollingStationCommand):
        with SessionLocal() as db:
            repository = PollingStationRepository(db)
            station = repository.update_polling_station(command.station_id, command.name, command.location, command.capacity)
            if not station:
                raise ValueError(f"Polling station with ID {command.station_id} not found.")
            return station
        
class DeletePollingStationHandler:
    def handle(self, command: DeletePollingStationCommand):
        with SessionLocal() as db:
            repository = PollingStationRepository(db)
            success = repository.delete_polling_station(command.station_id)
            if not success:
                raise ValueError(f"Polling station with ID {command.station_id} not found.")
            return {"message": "Polling station deleted successfully"}
        
class CreateAuditLogHandler:
    def handle(self, query: CreateAuditLogCommand):
        with SessionLocal() as db:
            repository = AuditLogRepository(db)
            return repository.create_audit_log(query.election_id, query.performed_by, query.action, query.details)
    
class GetAuditLogsHandler:
    def handle(self, query: GetAuditLogsQuery):
        with SessionLocal() as db:
            repository = AuditLogRepository(db)
            return repository.get_audit_logs_by_election(query.election_id)
        
class BulkVoterUploadHandler:
    def handle(self, query: VoterUploadQuery):
        with SessionLocal() as db:
            repository = VoterRepository(db)
        return repository.bulk_insert_voters(query.voters)
    
class ExportElectionResultsHandler:
    def handle(self, query: ExportElectionResultsQuery):
        with SessionLocal() as db:
            repository = ElectionRepository(db)
            """Export election results in CSV or JSON format."""
            results_data = repository.get_election_results(query.election_id)
            print(f"Exporting election results for election ID {query.election_id} in {query.format} format.")
            if not results_data:
                raise ValueError(f"Election with ID {query.election_id} not found.")

            if query.format == "json":
                return results_data

            elif query.format == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Candidate", "Votes", "Percentage"])
                for result in results_data["results"]:
                    writer.writerow([result["candidate"], result["votes"], result["percentage"]])
                output.seek(0)
                return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=results.csv"})

            else:
                raise ValueError("Invalid format. Supported formats: csv, json")
            
class CreateObserverHandler:
    def handle(self, query: CreateObserverCommand):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        return repository.create_observer(query.name, query.email, query.election_id, query.organization)
    
class GetObserversHandler:
    def handle(self, query: GetObserversQuery):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        return repository.get_observers_by_election(query.election_id)
    
class UpdateObserverHandler:
    def handle(self, query: UpdateObserverCommand):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        observer = repository.update_observer(query.observer_id, query.name, query.email, query.organization)
        if not observer:
            raise ValueError(f"Observer with ID {query.observer_id} not found.")
        print(f"Observer updated successfully: {observer.name}, {observer.email}, {observer.organization}")
        return observer
    
class DeleteObserverHandler:
    def handle(self, query: DeleteObserverCommand):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        success = repository.delete_observer(query.observer_id)
        if not success:
            raise ValueError(f"Observer with ID {query.observer_id} not found.")
        return {"message": "Observer deleted successfully"}
    
class GetObserverByIdHandler:
    def handle(self, query: GetObserverByIdQuery):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        observer = repository.get_observer_by_id(query.observer_id)
        if not observer:
            raise ValueError(f"Observer with ID {query.observer_id} not found.")
        return observer
    
class CreateCandidateHandler:
    def handle(self, query: CreateCandidateCommand):
        with SessionLocal() as db:
            repository = CandidateRepository(db)
        return repository.create_candidate(query.name, query.party, query.bio, query.election_id)
    
class GetCandidatesHandler:
    def handle(self, query: GetCandidatesQuery):
        with SessionLocal() as db:
            repository = CandidateRepository(db)
        return repository.get_candidates_by_election(query.election_id)
    
class UpdateCandidateHandler:
    def handle(self, query: UpdateCandidateCommand):
        with SessionLocal() as db:
            repository = CandidateRepository(db)
            candidate = repository.update_candidate(query.candidate_id, query.name, query.party, query.bio)
            if not candidate:
                raise ValueError(f"Candidate with ID {query.candidate_id} not found.")
            print(f"Candidate updated successfully: {candidate.name}, {candidate.party}, {candidate.bio}")
            return candidate
        
class DeleteCandidateHandler:
    def handle(self, query: DeleteCandidateCommand):
        with SessionLocal() as db:
            repository = CandidateRepository(db)
        success = repository.delete_candidate(query.candidate_id)
        if not success:
            raise ValueError(f"Candidate with ID {query.candidate_id} not found.")
        return {"message": "Candidate deleted successfully"}
    
class GetCandidateByIdHandler:
    def handle(self, query: GetCandidateByIdQuery):
        with SessionLocal() as db:
            repository = CandidateRepository(db)
            candidate = repository.get_candidate_by_id(query.candidate_id)
            if not candidate:
                raise ValueError(f"Candidate with ID {query.candidate_id} not found.")
            return candidate
        
class CastVoteHandlerv2:
    def handle(self, query: CastVoteCommandv2):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            print(f"Voter ID: {query.voter_id}, Candidate ID: {query.candidate_id}, Election ID: {query.election_id}")
            return repository.cast_vote(query.voter_id, query.candidate_id, query.election_id)
        
class GetVotesByElectionHandler:
    def handle(self, query: GetVotesByElectionQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.get_votes_by_election(query.election_id)
        
class GetVotesByVoterHandler:
    def handle(self, query: GetVotesByVoterQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.get_votes_by_voter(query.voter_id)
        
class SubmitFeedbackHandler:
    def handle(self, query: SubmitFeedbackCommand):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.submit_feedback(query.observer_id, query.election_id, query.description, query.severity)
    
class GetFeedbackByElectionHandler:
    def handle(self, query: GetFeedbackByElectionQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.get_feedback_by_election(query.election_id)
    
class GetFeedbackBySeverityHandler:
    def handle(self, query: GetFeedbackBySeverityQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.get_feedback_by_severity(query.severity)
    
class GetIntegrityScoreHandler:
    def handle(self, query: GetIntegrityScoreQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.get_integrity_score(query.election_id)
    
class GetSeverityDistributionHandler:
    def handle(self, query: GetSeverityDistributionQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
            return repository.get_severity_distribution()
        
class GetTopObserversHandler:
    def handle(self, query: GetTopObserversQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.get_top_observers(limit=query.limit)
    
class GetTimePatternsHandler:
    def handle(self, query: GetTimePatternsQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
            return repository.get_time_patterns()
        
class GetSentimentAnalysisHandler:
    def handle(self, query: GetSentimentAnalysisQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.analyze_sentiment()
    
class GetTurnoutPredictionHandler:
    def handle(self, query: GetTurnoutPredictionQuery):
        with SessionLocal() as db:
            repository = ElectionRepository(db)
        return repository.predict_turnout(query.election_id)
    
class GetObserverTrustScoresHandler:
    def handle(self, query: GetObserverTrustScoresQuery):
        with SessionLocal() as db:
            repository = ObserverRepository(db)
        return repository.calculate_observer_trust_scores()
    
class GetFeedbackExportHandler:
    def handle(self, query: GetFeedbackExportQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
            return repository.export_observer_feedback(query.export_format)
        
class GetElectionSummaryHandler:
    def handle(self, query: GetElectionSummaryQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.get_election_summary(query.election_id)
    
class GetSentimentTrendHandler:
    def handle(self, query: GetSentimentTrendQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.get_sentiment_trend(query.election_id)
    
class GetFeedbackCategoryAnalyticsHandler:
    def handle(self, query: GetFeedbackCategoryAnalyticsQuery):
        with SessionLocal() as db:
            repository = ObserverFeedbackRepository(db)
        return repository.get_feedback_category_analytics(query.election_id)
    
class GetCandidateVoteDistributionHandler:
    def handle(self, query: GetCandidateVoteDistributionQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.get_candidate_vote_distribution(query.election_id)
    
class GetTimeBasedVotingPatternsHandler:
    def handle(self, query: GetTimeBasedVotingPatternsQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.get_time_based_voting_patterns(query.election_id, query.interval)
    
class GetHistoricalTurnoutTrendsHandler:
    def handle(self, query: GetHistoricalTurnoutTrendsQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.get_turnout_trends(query.election_ids)
    
class GetTurnoutPredictionHandler:
    def handle(self, query: GetTurnoutPredictionQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
        return repository.predict_turnout(query.election_id, query.lookback)

class GetSeasonalTurnoutPredictionHandler:
    def handle(self, query: GetSeasonalTurnoutPredictionQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.predict_turnout_with_seasonality(query.election_id, query.lookback, query.weight_factor)
        
class GetTurnoutConfidenceHandler:
    def handle(self, query: GetTurnoutConfidenceQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.predict_turnout_with_confidence(query.election_id, query.lookback)
        
class GetDetailedHistoricalComparisonsHandler:
    def handle(self, query: GetDetailedHistoricalComparisonsQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.get_detailed_comparisons(query.election_ids)
    
class GetDetailedHistoricalComparisonsWithExternalHandler:
    def handle(self, query: GetDetailedHistoricalComparisonsWithExternalQuery):
        with SessionLocal() as db:
            repository = VoteRepository(db)
            return repository.get_detailed_comparisons_with_external(query.election_ids)
        
class DashboardAnalyticsHandler:
    def handle(self, query: DashboardAnalyticsQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_dashboard_metrics(query.election_id)
        
class RealTimeElectionSummaryHandler:
    def handle(self, query: RealTimeElectionSummaryQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_real_time_summary(query.election_id)
        
class GeolocationAnalyticsHandler:
    def handle(self, query: GeolocationAnalyticsQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_geolocation_metrics(query.election_id)
        
class PollingStationAnalyticsHandler:
    def handle(self, query: PollingStationAnalyticsQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_polling_station_insights(query.election_id)
        
class HistoricalPollingStationTrendsHandler:
    def handle(self, query: HistoricalPollingStationTrendsQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_historical_trends(query.election_ids, query.polling_station_id)
    
class PredictiveVoterTurnoutHandler:
    def handle(self, query: PredictiveVoterTurnoutQuery) -> dict:
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.predict_and_historical_turnout(query.upcoming_election_id) 

class AnomalyDetectionHandler:
    def handle(self, query: AnomalyDetectionQuery):
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.detect_anomalies(query.election_id)
        
class GeolocationTrendsHandler:
    def handle(self, query: GeolocationTrendsQuery) -> list:
        with SessionLocal() as db:
            repo = VoteRepository(db)
            return repo.get_votes_by_region(query.election_id, query.region)
        
class GetAlertsHandler:
    def handle(self, query: GetAlertsQuery) -> list:
        with SessionLocal() as db:
            repo = AlertRepository(db)
            return repo.get_alerts(query.election_id)
        
class CreateAlertHandler:
    def handle(self, command: CreateAlertCommand) -> dict:
        with SessionLocal() as db:
            repo = AlertRepository(db)
            return repo.create_alert(command.election_id, command.alert_type, command.message)
        
class UpdateAlertHandler:
    def handle(self, command: UpdateAlertCommand) -> dict:
        with SessionLocal() as db:
            repo = AlertRepository(db)
            return repo.update_alert(command.alert_id, command.status)
        
class GetAlertsWebSocketHandler:
    def handle(self, query: GetAlertsWSQuery) -> list:
        with SessionLocal() as db:
            repo = AlertRepository(db)
            # Pass both election_id and status if provided.
            return repo.get_alerts(query.election_id, query.status)
        
class GetNotificationsHandler:
    def handle(self, query: GetNotificationsQuery) -> list:
        with SessionLocal() as db:
            repo = NotificationRepository(db)
            return repo.get_notifications(query.user_id)
        
class MarkNotificationReadHandler:
    def handle(self, command: MarkNotificationReadCommand) -> dict:
        with SessionLocal() as db:
            repo = NotificationRepository(db)
            return repo.mark_notification_as_read(command.notification_id)
        
class GetNotificationsSummaryHandler:
    def handle(self, query: GetNotificationsSummaryQuery) -> dict:
        with SessionLocal() as db:
            repo = NotificationRepository(db)
            return repo.get_notifications_summary(query.user_id)
        
class MarkAllNotificationsReadHandler:
    def handle(self, command: MarkAllNotificationsReadCommand) -> dict:
        with SessionLocal() as db:
            repo = NotificationRepository(db)
            return repo.mark_all_notifications_as_read(command.user_id)
        
class GetSubscriptionsHandler:
    def handle(self, query: GetSubscriptionsQuery) -> list:
        with SessionLocal() as db:
            repo = SubscriptionRepository(db)
            return repo.get_subscriptions(query.user_id)
        
class UpdateSubscriptionHandler:
    def handle(self, command: UpdateSubscriptionCommand) -> dict:
        with SessionLocal() as db:
            repo = SubscriptionRepository(db)
            return repo.update_subscription(command.user_id, command.alert_type, command.is_subscribed)
        
class BulkUpdateSubscriptionsHandler:
    def handle(self, command: BulkUpdateSubscriptionsCommand) -> list:
        with SessionLocal() as db:
            repo = SubscriptionRepository(db)
            return repo.bulk_update_subscriptions(command.user_id, [u.model_dump() for u in command.updates])
        
class GetSubscriptionAnalyticsHandler:
    def handle(self, query: GetSubscriptionAnalyticsQuery) -> list:
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            return repo.get_subscription_analytics(query.user_id)
        
class TimeSeriesSubscriptionAnalyticsHandler:
    def handle(self, query: TimeSeriesSubscriptionAnalyticsQuery) -> dict:
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            return repo.get_extended_time_series_analytics(
                user_id=query.user_id,
                group_by=query.group_by,
                start_date=query.start_date,
                end_date=query.end_date
            )
        
class SegmentSubscriptionAnalyticsHandler:
    def handle(self, query: SegmentSubscriptionAnalyticsQuery) -> list:
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            return repo.get_subscription_analytics_by_region(query.region)
        
class SubscriptionConversionMetricsHandler:
    def handle(self, query: SubscriptionConversionMetricsQuery) -> dict:
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            return repo.get_subscription_conversion_metrics(query.user_id)

class PredictiveSubscriptionAnalyticsHandler:
    def handle(self, query: PredictiveSubscriptionAnalyticsQuery) -> dict:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from datetime import timedelta

        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            time_series = repo.get_time_series_data_for_alert(query.user_id, query.alert_type)
        
        if not time_series:
            return {"message": "No data to forecast."}
        
        # Convert dates to ordinals for regression
        periods = np.array([t[0].toordinal() for t in time_series]).reshape(-1, 1)
        counts = np.array([t[1] for t in time_series])
        
        model = LinearRegression()
        model.fit(periods, counts)
        
        last_date = max(t[0] for t in time_series)
        forecast = []
        for i in range(1, query.forecast_days + 1):
            future_date = last_date + timedelta(days=i)
            pred = model.predict(np.array([[future_date.toordinal()]]))
            forecast.append({
                "date": future_date.isoformat(),
                "predicted_changes": float(pred[0])
            })
        
        return {
            "alert_type": query.alert_type,
            "forecast_days": query.forecast_days,
            "forecast": forecast
        }
    
class EnhancedPredictiveSubscriptionAnalyticsHandler:
    def handle(self, query: EnhancedPredictiveSubscriptionAnalyticsQuery) -> dict:
        from statsmodels.tsa.arima.model import ARIMA
        
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            # Retrieve time series data grouped by day for the alert type
            time_series = repo.get_time_series_data_for_alert(query.user_id, query.alert_type, group_by="day")
        
        if not time_series:
            return {"message": "No data available to forecast."}
        
        # Convert time_series data into a pandas DataFrame
        df = pd.DataFrame(time_series, columns=['date', 'count'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        
        # Reindex so that every day is present between the first and last date
        idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(idx, fill_value=0)
        df.index.name = 'date'
        
        # Use the 'count' column as our time series
        series = df['count']
        
        # Fit the ARIMA model (using an order of (1, 1, 1) as a starting point)
        try:
            model = ARIMA(series, order=(1, 1, 1))
            model_fit = model.fit()
        except Exception as e:
            return {"message": f"ARIMA model failed: {str(e)}"}
        
        # Forecast future subscription event counts
        forecast_values = model_fit.forecast(steps=query.forecast_days)
        
        # Compute the forecast dates, starting the day after our last date
        last_date = df.index.max()
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, query.forecast_days + 1)]
        
        forecast = []
        for date, pred in zip(forecast_dates, forecast_values):
            forecast.append({
                "date": date.isoformat(),
                "predicted_changes": float(pred)
            })
        
        return {
            "alert_type": query.alert_type,
            "forecast_days": query.forecast_days,
            "forecast": forecast,
            "model": "ARIMA(1,1,1)"
        }
    
class EnhancedNeuralNetworkPredictiveAnalyticsHandler:
    def handle(self, query: EnhancedNeuralNetworkPredictiveAnalyticsQuery) -> dict:
        # Retrieve time series data (grouped by day)
        with SessionLocal() as db:
            repo = SubscriptionEventRepository(db)
            time_series = repo.get_time_series_data_for_alert(query.user_id, query.alert_type, group_by="day")
        
        if not time_series:
            return {"message": "No data available to forecast."}
        
        # Convert data into a pandas DataFrame
        df = pd.DataFrame(time_series, columns=['date', 'count'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        
        # Reindex the DataFrame so that every day is present
        idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(idx, fill_value=0)
        df.index.name = 'date'
    
        series = df['count'].values  # this is a 1D numpy array
        series = series.astype(np.float32)
        
        # Create a dataset for time-series forecasting using a sliding window
        # Example: using a window of 3 days to predict the next day
        window_size = 3
        X, y = [], []
        for i in range(len(series) - window_size):
            X.append(series[i:i+window_size])
            y.append(series[i+window_size])
        X = np.array(X)
        y = np.array(y)
        
        # Reshape X for LSTM: (samples, time steps, features)
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # Build a simple LSTM model
        model = Sequential([
            LSTM(50, activation='relu', input_shape=(window_size, 1)),
            Dropout(0.2),
            Dense(1)
        ])
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        
        # Train the model, using a small number of epochs for demonstration.
        model.fit(X, y, epochs=50, verbose=0)
        
        # Forecast for query.forecast_days using rolling predictions
        predictions = []
        last_window = series[-window_size:]
        for _ in range(query.forecast_days):
            # reshape last window to model input shape
            input_window = last_window.reshape((1, window_size, 1))
            pred = model.predict(input_window, verbose=0)
            predictions.append(float(pred[0, 0]))
            # update the window by appending the predicted value and removing the oldest
            last_window = np.append(last_window[1:], pred)
        
        # Compute forecast dates starting the day after the last date in our original data
        last_date = df.index.max()
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, query.forecast_days + 1)]
        
        forecast = []
        for date, pred in zip(forecast_dates, predictions):
            forecast.append({
                "date": date.isoformat(),
                "predicted_changes": pred
            })
        
        return {
            "alert_type": query.alert_type,
            "forecast_days": query.forecast_days,
            "forecast": forecast,
            "model": "LSTM Neural Network"
        }

class CorrelateFeedbackAnalyticsHandler:
    def handle(self, query: CorrelationAnalyticsQuery) -> dict:
        with SessionLocal() as db:
            # Retrieve subscription data.
            sub_repo = SubscriptionEventRepository(db)
            # The updated repository method now accepts date filters.
            # Here we assume we're interested in alert type "anomaly" (adjust as needed).
            sub_data = sub_repo.get_time_series_data_for_alert(
                user_id=query.user_id,
                alert_type="anomaly",
                group_by="day",
                start_date=query.start_date,
                end_date=query.end_date
            )
            # Convert the subscription data to a DataFrame.
            # Expected columns: ["date", "changes"]
            df_sub = pd.DataFrame(sub_data, columns=["date", "total_changes"])
            if not df_sub.empty:
                # Convert the date to a common format (using just the date part)
                df_sub["date"] = pd.to_datetime(df_sub["date"]).dt.date
                # (In this simple case the repository returns one record per day because of grouping.)
            else:
                df_sub = pd.DataFrame(columns=["date", "total_changes"])
            
            # Retrieve observer feedback aggregated by day.
            feedback_repo = ObserverFeedbackRepository(db)
            feedback_data = feedback_repo.get_feedback_by_date(
                observer_id=query.user_id,  # assuming observer_id equates to user_id for correlation
                start_date=query.start_date,
                end_date=query.end_date
            )
            # Expected columns: ["date", "avg_severity", "feedback_count"]
            df_feed = pd.DataFrame(feedback_data, columns=["date", "avg_severity", "feedback_count"])
            if not df_feed.empty:
                df_feed["date"] = pd.to_datetime(df_feed["date"]).dt.date
            
            # Merge the two datasets on the date.
            # Using inner join to only include days present in both.
            df_merged = pd.merge(df_sub, df_feed, on="date", how="inner")
            
            # Compute Pearson correlation between daily subscription changes and average feedback severity.
            correlation = None
            if not df_merged.empty and len(df_merged) > 1:
                correlation = df_merged["total_changes"].corr(df_merged["avg_severity"])
            
            return {
                "user_id": query.user_id,
                "data_points": len(df_merged),
                "correlation": float(correlation) if correlation is not None else None,
                "merged_data": df_merged.to_dict(orient="records")
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
command_bus.register_handler(CreatePollingStationCommand, CreatePollingStationHandler())
command_bus.register_handler(UpdatePollingStationCommand, UpdatePollingStationHandler())
command_bus.register_handler(DeletePollingStationCommand, DeletePollingStationHandler())
command_bus.register_handler(CreateAuditLogCommand, CreateAuditLogHandler())
command_bus.register_handler(VoterUploadQuery, BulkVoterUploadHandler())
command_bus.register_handler(CreateObserverCommand, CreateObserverHandler())
command_bus.register_handler(UpdateObserverCommand, UpdateObserverHandler())
command_bus.register_handler(DeleteObserverCommand, DeleteObserverHandler())
command_bus.register_handler(CreateCandidateCommand, CreateCandidateHandler())
command_bus.register_handler(UpdateCandidateCommand, UpdateCandidateHandler())
command_bus.register_handler(DeleteCandidateCommand, DeleteCandidateHandler())
command_bus.register_handler(CastVoteCommandv2, CastVoteHandlerv2())
command_bus.register_handler(SubmitFeedbackCommand, SubmitFeedbackHandler())
command_bus.register_handler(CreateAlertCommand, CreateAlertHandler())
command_bus.register_handler(UpdateAlertCommand, UpdateAlertHandler())
command_bus.register_handler(MarkNotificationReadCommand, MarkNotificationReadHandler())
command_bus.register_handler(MarkAllNotificationsReadCommand, MarkAllNotificationsReadHandler())
command_bus.register_handler(UpdateSubscriptionCommand, UpdateSubscriptionHandler())
command_bus.register_handler(BulkUpdateSubscriptionsCommand, BulkUpdateSubscriptionsHandler())


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
query_bus.register_handler(GetPollingStationQuery, GetPollingStationHandler())
query_bus.register_handler(GetPollingStationsByElectionQuery, GetPollingStationsByElectionHandler())
query_bus.register_handler(GetAuditLogsQuery, GetAuditLogsHandler())
query_bus.register_handler(ExportElectionResultsQuery, ExportElectionResultsHandler())
query_bus.register_handler(GetObserversQuery, GetObserversHandler())
query_bus.register_handler(GetObserverByIdQuery, GetObserverByIdHandler())
query_bus.register_handler(GetCandidatesQuery, GetCandidatesHandler())
query_bus.register_handler(GetCandidateByIdQuery, GetCandidateByIdHandler())
query_bus.register_handler(GetVotesByElectionQuery, GetVotesByElectionHandler())
query_bus.register_handler(GetVotesByVoterQuery, GetVotesByVoterHandler())
query_bus.register_handler(GetFeedbackByElectionQuery, GetFeedbackByElectionHandler())
query_bus.register_handler(GetFeedbackBySeverityQuery, GetFeedbackBySeverityHandler())
query_bus.register_handler(GetIntegrityScoreQuery, GetIntegrityScoreHandler())
query_bus.register_handler(GetSeverityDistributionQuery, GetSeverityDistributionHandler())
query_bus.register_handler(GetTopObserversQuery, GetTopObserversHandler())
query_bus.register_handler(GetTimePatternsQuery, GetTimePatternsHandler())
query_bus.register_handler(GetSentimentAnalysisQuery, GetSentimentAnalysisHandler())
query_bus.register_handler(GetTurnoutPredictionQuery, GetTurnoutPredictionHandler())
query_bus.register_handler(GetObserverTrustScoresQuery, GetObserverTrustScoresHandler())
query_bus.register_handler(GetFeedbackExportQuery, GetFeedbackExportHandler())
query_bus.register_handler(GetElectionSummaryQuery, GetElectionSummaryHandler())
query_bus.register_handler(GetSentimentTrendQuery, GetSentimentTrendHandler())
query_bus.register_handler(GetFeedbackCategoryAnalyticsQuery, GetFeedbackCategoryAnalyticsHandler())
query_bus.register_handler(GetCandidateVoteDistributionQuery, GetCandidateVoteDistributionHandler())
query_bus.register_handler(GetTimeBasedVotingPatternsQuery, GetTimeBasedVotingPatternsHandler())
query_bus.register_handler(GetHistoricalTurnoutTrendsQuery, GetHistoricalTurnoutTrendsHandler())
query_bus.register_handler(GetTurnoutPredictionQuery, GetTurnoutPredictionHandler())
query_bus.register_handler(GetSeasonalTurnoutPredictionQuery, GetSeasonalTurnoutPredictionHandler())
query_bus.register_handler(GetTurnoutConfidenceQuery, GetTurnoutConfidenceHandler())
query_bus.register_handler(GetDetailedHistoricalComparisonsQuery, GetDetailedHistoricalComparisonsHandler())
query_bus.register_handler(GetDetailedHistoricalComparisonsWithExternalQuery, GetDetailedHistoricalComparisonsWithExternalHandler())
query_bus.register_handler(DashboardAnalyticsQuery, DashboardAnalyticsHandler())
query_bus.register_handler(RealTimeElectionSummaryQuery, RealTimeElectionSummaryHandler())
query_bus.register_handler(GeolocationAnalyticsQuery, GeolocationAnalyticsHandler())
query_bus.register_handler(PollingStationAnalyticsQuery, PollingStationAnalyticsHandler())
query_bus.register_handler(HistoricalPollingStationTrendsQuery, HistoricalPollingStationTrendsHandler())
query_bus.register_handler(PredictiveVoterTurnoutQuery, PredictiveVoterTurnoutHandler())
query_bus.register_handler(AnomalyDetectionQuery, AnomalyDetectionHandler())
query_bus.register_handler(GeolocationTrendsQuery, GeolocationTrendsHandler())
query_bus.register_handler(GetAlertsQuery, GetAlertsHandler())
query_bus.register_handler(GetAlertsWSQuery, GetAlertsWebSocketHandler())
query_bus.register_handler(GetNotificationsQuery, GetNotificationsHandler())
query_bus.register_handler(GetNotificationsSummaryQuery, GetNotificationsSummaryHandler())
query_bus.register_handler(GetSubscriptionsQuery, GetSubscriptionsHandler())
query_bus.register_handler(GetSubscriptionAnalyticsQuery, GetSubscriptionAnalyticsHandler())
query_bus.register_handler(TimeSeriesSubscriptionAnalyticsQuery, TimeSeriesSubscriptionAnalyticsHandler())
query_bus.register_handler(SegmentSubscriptionAnalyticsQuery, SegmentSubscriptionAnalyticsHandler())
query_bus.register_handler(SubscriptionConversionMetricsQuery, SubscriptionConversionMetricsHandler())
query_bus.register_handler(PredictiveSubscriptionAnalyticsQuery, PredictiveSubscriptionAnalyticsHandler())
query_bus.register_handler(EnhancedPredictiveSubscriptionAnalyticsQuery, EnhancedPredictiveSubscriptionAnalyticsHandler())
query_bus.register_handler(EnhancedNeuralNetworkPredictiveAnalyticsQuery, EnhancedNeuralNetworkPredictiveAnalyticsHandler())
query_bus.register_handler(CorrelationAnalyticsQuery, CorrelateFeedbackAnalyticsHandler())




