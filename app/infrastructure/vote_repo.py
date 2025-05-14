from sqlalchemy import func
from sqlalchemy.orm import Session
from textblob import TextBlob
from app.infrastructure.models import ObserverFeedback, Vote

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