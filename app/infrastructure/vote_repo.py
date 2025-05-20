from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import Session
from textblob import TextBlob
from app.infrastructure.models import Candidate, ObserverFeedback, Vote

class VoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def cast_vote(self, voter_id: int, candidate_id: int, election_id: int):
        vote = Vote(voter_id=voter_id, candidate_id=candidate_id, election_id=election_id)
        self.db.add(vote)
        self.db.commit()
        self.db.refresh(vote)
        return vote
    
    def get_votes_by_election(self, election_id: int):
        return self.db.query(Vote).filter(Vote.election_id == election_id).all()
    
    def get_votes_by_voter(self, voter_id: int):
        return self.db.query(Vote).filter(Vote.voter_id == voter_id).all()
    
    def get_election_summary(self, election_id: int):
        # Total votes cast for the election
        total_votes = self.db.query(func.count(Vote.id))\
                             .filter(Vote.election_id == election_id)\
                             .scalar() or 0

        # Calculate average sentiment for observer feedback in the election
        feedbacks = self.db.query(ObserverFeedback)\
                           .filter(ObserverFeedback.election_id == election_id)\
                           .all()
        if feedbacks:
            total_sentiment = 0
            count = 0
            for fb in feedbacks:
                # Calculate the sentiment polarity from the feedback description
                polarity = TextBlob(fb.description).sentiment.polarity
                total_sentiment += polarity
                count += 1
            average_sentiment = total_sentiment / count
        else:
            average_sentiment = None

        # Calculate average observer trust score based on reports per observer
        # For each observer, trust_score = min(100, (number_of_reports * 10))
        observer_data = self.db.query(
            ObserverFeedback.observer_id,
            func.count(ObserverFeedback.id).label("report_count")
        ).filter(ObserverFeedback.election_id == election_id)\
          .group_by(ObserverFeedback.observer_id)\
          .all()
        if observer_data:
            trust_scores = [min(100, x.report_count * 10) for x in observer_data]
            average_trust = sum(trust_scores) / len(trust_scores)
        else:
            average_trust = None

        return {
            "election_id": election_id,
            "total_votes": total_votes,
            "average_sentiment": average_sentiment,
            "average_observer_trust": average_trust
        }
    
    def get_sentiment_trend(self, election_id: int):
        # Retrieve all feedback entries for the election.
        feedbacks = self.db.query(ObserverFeedback)\
                           .filter(ObserverFeedback.election_id == election_id)\
                           .all()
        
        # Aggregate data by date.
        trend_data = defaultdict(lambda: {"total_sentiment": 0.0, "count": 0})
        for fb in feedbacks:
            if fb.timestamp:
                # Group by date in ISO format.
                date_str = fb.timestamp.date().isoformat()
            else:
                date_str = "unknown"
            
            # Calculate sentiment polarity.
            polarity = TextBlob(fb.description).sentiment.polarity
            trend_data[date_str]["total_sentiment"] += polarity
            trend_data[date_str]["count"] += 1

        # Create a sorted list of daily sentiment trends.
        trend_list = []
        for date_str, data in trend_data.items():
            average_sentiment = data["total_sentiment"] / data["count"] if data["count"] > 0 else None
            trend_list.append({
                "date": date_str,
                "average_sentiment": average_sentiment,
                "feedback_count": data["count"]
            })
        
        trend_list.sort(key=lambda x: x["date"])
        return trend_list
    
    def get_candidate_vote_distribution(self, election_id: int):
        # Retrieve vote counts for each candidate in the given election.
        votes_data = (
            self.db.query(
                Candidate.id,
                Candidate.name,
                func.count(Vote.id).label("vote_count")
            )
            .join(Vote, Vote.candidate_id == Candidate.id)
            .filter(Vote.election_id == election_id)
            .group_by(Candidate.id, Candidate.name)
            .all()
        )
        
        # Calculate total votes in the election.
        total_votes = sum([item.vote_count for item in votes_data])
        
        distribution = []
        for candidate in votes_data:
            percentage = (candidate.vote_count / total_votes * 100) if total_votes > 0 else 0
            distribution.append({
                "candidate_id": candidate.id,
                "candidate_name": candidate.name,
                "vote_count": candidate.vote_count,
                "vote_percentage": round(percentage, 2)
            })
        return distribution
    
    def get_time_based_voting_patterns(self, election_id: int, interval: str = "hourly"):
        # Determine time grouping (hourly or daily)
        time_group = func.date_trunc("hour", Vote.timestamp) if interval == "hourly" else func.date_trunc("day", Vote.timestamp)

        # Aggregate votes based on the chosen time interval
        vote_data = self.db.query(time_group.label("time_period"), func.count(Vote.id).label("vote_count")) \
                           .filter(Vote.election_id == election_id) \
                           .group_by(time_group) \
                           .order_by(time_group) \
                           .all()

        return [{"time_period": record.time_period.isoformat(), "vote_count": record.vote_count} for record in vote_data]