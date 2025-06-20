from collections import defaultdict
from typing import Counter, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from textblob import TextBlob
from app.infrastructure.models import Candidate, Election, ObserverFeedback, Vote
import numpy as np

from app.infrastructure.observer_feedback_repo import ObserverFeedbackRepository

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
    
    def get_turnout_trends(self, election_ids: list[int]):
        # Retrieve total voter turnout for each election
        turnout_data = (
            self.db.query(Election.id, Election.name, func.count(Vote.id).label("vote_count"))
            .join(Vote, Vote.election_id == Election.id)
            .filter(Election.id.in_(election_ids))
            .group_by(Election.id, Election.name)
            .order_by(Election.id)
            .all()
        )

        if not turnout_data:
            return []

        # Compute percentage change between consecutive elections
        trends = []
        for i in range(len(turnout_data)):
            current = turnout_data[i]
            previous = turnout_data[i - 1] if i > 0 else None
            percentage_change = (
                ((current.vote_count - previous.vote_count) / previous.vote_count * 100)
                if previous and previous.vote_count > 0 else None
            )

            trends.append({
                "election_id": current.id,
                "election_name": current.name,
                "vote_count": current.vote_count,
                "percentage_change": round(percentage_change, 2) if percentage_change is not None else None
            })

        return trends
    
    def predict_turnout(self, election_id: int, lookback: int = 3):
        # Retrieve turnout data for previous elections
        past_turnout = self.db.query(Election.id, func.count(Vote.id).label("vote_count")) \
                              .join(Vote, Vote.election_id == Election.id) \
                              .filter(Election.id < election_id) \
                              .group_by(Election.id) \
                              .order_by(Election.id.desc()) \
                              .limit(lookback) \
                              .all()

        if not past_turnout:
            return {"election_id": election_id, "predicted_turnout": None, "status": "Not enough historical data"}

        # Compute simple moving average as the predicted turnout
        total_votes = sum([item.vote_count for item in past_turnout])
        predicted_turnout = total_votes // len(past_turnout)

        return {
            "election_id": election_id,
            "predicted_turnout": predicted_turnout,
            "status": "Projection based on historical trends"
        }
    
    def predict_turnout_with_seasonality(self, election_id: int, lookback: int = 5, weight_factor: float = 1.5):
        # Retrieve the first recorded vote timestamp for the election
        election_timing = self.db.query(Vote.election_id, func.min(Vote.timestamp).label("start_date")) \
                                 .filter(Vote.election_id == election_id) \
                                 .group_by(Vote.election_id) \
                                 .first()

        if not election_timing or not election_timing.start_date:
            return {"election_id": election_id, "predicted_turnout": None, "status": "Election timing unavailable"}

        upcoming_month = election_timing.start_date.month

        # Retrieve past elections for comparison
        past_turnout = self.db.query(Vote.election_id, func.min(Vote.timestamp).label("start_date"), func.count(Vote.id).label("vote_count")) \
                              .group_by(Vote.election_id) \
                              .order_by(Vote.election_id.desc()) \
                              .limit(lookback) \
                              .all()

        if not past_turnout:
            return {"election_id": election_id, "predicted_turnout": None, "status": "Not enough historical data"}

        # Apply seasonality weighting
        total_weighted_votes = 0
        total_weight = 0
        for past in past_turnout:
            weight = weight_factor if past.start_date.month == upcoming_month else 1.0
            total_weighted_votes += past.vote_count * weight
            total_weight += weight

        predicted_turnout = total_weighted_votes / total_weight

        return {
            "election_id": election_id,
            "predicted_turnout": round(predicted_turnout),
            "status": f"Projection adjusted for seasonality (month={upcoming_month})"
        }
    
    def predict_turnout_with_confidence(self, election_id: int, lookback: int = 5):
        # Retrieve past turnout data
        past_turnout = self.db.query(Election.id, func.count(Vote.id).label("vote_count")) \
                              .join(Vote, Vote.election_id == Election.id) \
                              .filter(Election.id < election_id) \
                              .group_by(Election.id) \
                              .order_by(Election.id.desc()) \
                              .limit(lookback) \
                              .all()

        if not past_turnout:
            return {"election_id": election_id, "predicted_turnout": None, "confidence_score": None, "status": "Not enough historical data"}

        vote_counts = [item.vote_count for item in past_turnout]
        predicted_turnout = sum(vote_counts) // len(vote_counts)

        # Compute standard deviation of turnout
        std_dev = np.std(vote_counts)
        print(f"Standard deviation of turnout: {std_dev}")
        # Define confidence level based on variability
        if std_dev < 5:
            confidence_score = "High Confidence 🔵"
        elif std_dev < 15:
            confidence_score = "Moderate Confidence 🟡"
        else:
            confidence_score = "Low Confidence 🔴"

        return {
            "election_id": election_id,
            "predicted_turnout": predicted_turnout,
            "confidence_score": confidence_score,
            "status": "Forecast includes confidence analysis based on turnout variability"
        }
    
    def get_detailed_comparisons(self, election_ids: list[int]):
        # Retrieve election data with vote counts and earliest vote timestamp.
        data = (
            self.db.query(
                Election.id,
                Election.name,
                func.count(Vote.id).label("vote_count"),
                func.min(Vote.timestamp).label("start_date")
            )
            .join(Vote, Vote.election_id == Election.id)
            .filter(Election.id.in_(election_ids))
            .group_by(Election.id, Election.name)
            .order_by(Election.id)
            .all()
        )
        if not data:
            return []

        comparisons = []
        for i, current in enumerate(data):
            previous = data[i - 1] if i > 0 else None
            
            if previous and previous.vote_count > 0:
                percentage_change = ((current.vote_count - previous.vote_count) / previous.vote_count * 100)
            else:
                percentage_change = None

            if previous and previous.start_date and current.start_date:
                days_diff = (current.start_date - previous.start_date).days
            else:
                days_diff = None

            # Annotation based on percentage change:
            if percentage_change is None:
                annotation = "Baseline data"
            elif percentage_change > 50:
                annotation = "Major Surge"
            elif percentage_change < -30:
                annotation = "Significant Drop"
            else:
                annotation = "Stable turnout"

            comparisons.append({
                "election_id": current.id,
                "election_name": current.name,
                "vote_count": current.vote_count,
                "start_date": current.start_date.isoformat() if current.start_date else None,
                "percentage_change": round(percentage_change, 2) if percentage_change is not None else None,
                "days_since_previous": days_diff,
                "annotation": annotation
            })

        return comparisons
    

    def get_external_data(self, election_id: int) -> dict:
        """
        Simulate an external API call which returns extra data based on the election.
        In a real system, this might be a network call using requests or an async HTTP client.
        """
        # For demonstration, we assign simulated values:
        simulated_data = {
            "weather": "Sunny" if election_id % 2 == 0 else "Cloudy",
            "economic_index": 100 + election_id * 2  # Just a sample computation
        }
        return simulated_data

    def get_detailed_comparisons_with_external(self, election_ids: list[int]) -> list:
        # Retrieve the internal detailed comparisons first.
        comparisons = self.get_detailed_comparisons(election_ids)
        # For each election record, fetch and merge external data.
        for comp in comparisons:
            external_data = self.get_external_data(comp["election_id"])
            comp["external"] = external_data
        return comparisons
    
    def get_dashboard_metrics(self, election_id: int) -> dict:
        # 1. Total votes for the specified election
        total_votes = (
            self.db.query(func.count(Vote.id))
            .filter(Vote.election_id == election_id)
            .scalar()
        )

        # 2. Vote distribution per candidate for the specified election
        candidate_distribution = (
            self.db.query(Vote.candidate_id, func.count(Vote.id).label("votes"))
            .filter(Vote.election_id == election_id)
            .group_by(Vote.candidate_id)
            .all()
        )
        candidate_distribution = [
            {"candidate_id": candidate_id, "votes": votes}
            for candidate_id, votes in candidate_distribution
        ]

        # 3. Mock observer sentiment summary (in a real system, you'd analyze feedback)
        observer_sentiment = {"positive": 70, "neutral": 20, "negative": 10}

        # 4. Historical turnout trends: average turnout of past elections and change percentage
        past_elections_data = (
            self.db.query(Election.id, func.count(Vote.id).label("vote_count"))
            .join(Vote, Vote.election_id == Election.id)
            .filter(Election.id < election_id)
            .group_by(Election.id)
            .all()
        )
        past_vote_counts = [row.vote_count for row in past_elections_data]
        historical_trend = None
        if past_vote_counts:
            historical_average = sum(past_vote_counts) / len(past_vote_counts)
            change_percentage = ((total_votes - historical_average) / historical_average * 100
                                 ) if historical_average > 0 else None
            historical_trend = {
                "historical_average": historical_average,
                "current_vs_average_change": round(change_percentage, 2)
                if change_percentage is not None
                else None,
            }
        else:
            historical_trend = {"historical_average": None, "current_vs_average_change": None}

        # 5. External data (mocked for now)
        external_data = {
            "weather": "Sunny" if election_id % 2 == 0 else "Cloudy",
            "economic_index": 100 + election_id * 3,
        }

        return {
            "election_id": election_id,
            "total_votes": total_votes,
            "candidate_distribution": candidate_distribution,
            "observer_sentiment": observer_sentiment,
            "historical_trend": historical_trend,
            "external_data": external_data,
        }
    
    def get_real_time_summary(self, election_id: int) -> dict:
        # Total votes so far for the election
        total_votes = (
            self.db.query(func.count(Vote.id))
            .filter(Vote.election_id == election_id)
            .scalar()
        )

        # Candidate vote distribution
        candidate_distribution_query = (
            self.db.query(Vote.candidate_id, func.count(Vote.id).label("votes"))
            .filter(Vote.election_id == election_id)
            .group_by(Vote.candidate_id)
            .all()
        )
        candidate_distribution = [
            {"candidate_id": cid, "votes": votes}
            for cid, votes in candidate_distribution_query
        ]

        # Get the timestamp of the latest vote for the last update time
        last_update = (
            self.db.query(func.max(Vote.timestamp))
            .filter(Vote.election_id == election_id)
            .scalar()
        )

        # Instead of mocking, use the existing observer sentiment repository:
        observer_sentiment = ObserverFeedbackRepository(self.db).get_sentiment_by_election(election_id)
        
        return {
            "election_id": election_id,
            "total_votes": total_votes,
            "candidate_distribution": candidate_distribution,
            "last_update": last_update.isoformat() if last_update else None,
            "observer_sentiment": observer_sentiment,
        }
    
    def get_geolocation_metrics(self, election_id: int) -> list:
        # Query total votes grouped by region.
        region_votes = (
            self.db.query(Vote.region, func.count(Vote.id).label("total_votes"))
            .filter(Vote.election_id == election_id)
            .group_by(Vote.region)
            .all()
        )

        # Query candidate distribution within each region.
        candidate_distribution_query = (
            self.db.query(Vote.region, Vote.candidate_id, func.count(Vote.id).label("votes"))
            .filter(Vote.election_id == election_id)
            .group_by(Vote.region, Vote.candidate_id)
            .all()
        )

        # Transform candidate distribution into a dict keyed by region.
        candidate_distribution = {}
        for region, candidate_id, votes in candidate_distribution_query:
            if region not in candidate_distribution:
                candidate_distribution[region] = []
            candidate_distribution[region].append({
                "candidate_id": candidate_id,
                "votes": votes
            })

        # Merge the data for each region.
        results = []
        for region, total_votes in region_votes:
            results.append({
                "region": region,
                "total_votes": total_votes,
                "candidate_distribution": candidate_distribution.get(region, [])
            })

        return results
    
    def get_polling_station_insights(self, election_id: int) -> list:
        """
        Computes basic analytics per polling station for the given election:
          - Total votes cast per station.
          - Average interval (in seconds) between consecutive votes.
          - Peak hour and the vote count during that hour.
        """
        # Retrieve votes for the election that have a polling station assigned.
        votes = (
            self.db.query(Vote)
            .filter(Vote.election_id == election_id, Vote.polling_station != None)
            .all()
        )

        station_dict = defaultdict(list)
        # Group vote timestamps by polling_station.
        for vote in votes:
            station_dict[vote.polling_station].append(vote.timestamp)

        results = []
        for station, timestamps in station_dict.items():
            total_votes = len(timestamps)
            # Sort timestamps to calculate time differences.
            timestamps_sorted = sorted(timestamps)
            if len(timestamps_sorted) > 1:
                intervals = [
                    (t2 - t1).total_seconds()
                    for t1, t2 in zip(timestamps_sorted, timestamps_sorted[1:])
                ]
                avg_interval = sum(intervals) / len(intervals)
            else:
                avg_interval = None  # Not enough data to compute an interval.

            # Peak hour: count votes per hour.
            hours = [timestamp.hour for timestamp in timestamps]
            hour_counts = Counter(hours)
            if hour_counts:
                peak_hour, peak_votes = hour_counts.most_common(1)[0]
            else:
                peak_hour, peak_votes = None, None

            polling_station_data = {
                "id": station.id,
                "name": station.name,
                "location": station.location,
                "capacity": station.capacity
            }
            results.append({
                "polling_station": polling_station_data,
                "total_votes": total_votes,
                "average_interval_seconds": avg_interval,
                "peak_hour": peak_hour,
                "votes_in_peak_hour": peak_votes,
            })

        return results
    
    def get_historical_trends(
        self, election_ids: List[int], polling_station_id: Optional[int] = None
    ) -> list:
        """
        For the given election IDs (and optionally filtered by a specific polling station),
        returns historical performance metrics grouped by (election, polling station):
          - total_votes
          - average_interval_seconds between consecutive votes
          - peak_hour and votes_in_peak_hour
        """
        query = self.db.query(Vote).filter(
            Vote.election_id.in_(election_ids),
            Vote.polling_station_id.isnot(None)  # only consider votes with a polling station
        )
        if polling_station_id is not None:
            query = query.filter(Vote.polling_station_id == polling_station_id)

        votes = query.all()

        # Group votes by (election_id, polling_station_id)
        groups = defaultdict(list)
        for vote in votes:
            key = (vote.election_id, vote.polling_station_id)
            groups[key].append(vote)

        results = []
        for (election_id, polling_station_id), vote_group in groups.items():
            # Extract timestamps and sort them
            timestamps = sorted([v.timestamp for v in vote_group])
            total_votes = len(timestamps)

            # Calculate average interval (in seconds) between consecutive votes
            if total_votes > 1:
                intervals = [
                    (t2 - t1).total_seconds()
                    for t1, t2 in zip(timestamps, timestamps[1:])
                ]
                avg_interval = sum(intervals) / len(intervals)
            else:
                avg_interval = None

            # Determine peak hour
            hours = [ts.hour for ts in timestamps]
            hour_counts = Counter(hours)
            if hour_counts:
                peak_hour, peak_votes = hour_counts.most_common(1)[0]
            else:
                peak_hour, peak_votes = None, None

            # We'll extract polling station details from one of the votes.
            polling_station = vote_group[0].polling_station
            # Assume polling_station is serialized as a dict when returned, or customize as needed.
            # Here, we construct a simplified dict if needed.
            polling_station_data = {
                "id": polling_station.id if polling_station else None,
                "name": polling_station.name if polling_station else None,
                "location": getattr(polling_station, "location", None),
                "capacity": getattr(polling_station, "capacity", None),
                "election_id": polling_station.election_id if hasattr(polling_station, "election_id") else None
            }

            results.append({
                "election_id": election_id,
                "polling_station": polling_station_data,
                "total_votes": total_votes,
                "average_interval_seconds": avg_interval,
                "peak_hour": peak_hour,
                "votes_in_peak_hour": peak_votes,
            })

        return results
    
    def predict_and_historical_turnout(self, upcoming_election_id: int) -> dict:
        """
        Predict the voter turnout for the upcoming election based on historical data.
        It returns a dictionary containing:
          - predicted_turnout
          - historical_turnouts: a list of dictionaries for each past election with keys election_id and turnout.
        """
        # Query historical turnout grouped by election_id for elections before the upcoming one.
        historical_data = (
            self.db.query(
                Vote.election_id,
                func.count(Vote.id).label("turnout")
            )
            .filter(Vote.election_id < upcoming_election_id)
            .group_by(Vote.election_id)
            .order_by(Vote.election_id)
            .all()
        )

        # Prepare a list of historical turnouts.
        historical_turnouts = [
            {"election_id": election_id, "turnout": turnout}
            for election_id, turnout in historical_data
        ]

        if not historical_turnouts:
            # No historical data available.
            return {"predicted_turnout": None, "historical_turnouts": []}

        if len(historical_turnouts) == 1:
            # Only one historical election available; return its turnout as the prediction.
            predicted_turnout = historical_turnouts[0]["turnout"]
        else:
            # Compute increases between consecutive elections.
            increases = []
            for i in range(1, len(historical_turnouts)):
                diff = historical_turnouts[i]["turnout"] - historical_turnouts[i-1]["turnout"]
                increases.append(diff)
            average_increase = sum(increases) / len(increases)
            # Predicted turnout is the last turnout plus the average increase.
            predicted_turnout = historical_turnouts[-1]["turnout"] + average_increase

        return {
            "predicted_turnout": predicted_turnout,
            "historical_turnouts": historical_turnouts,
        }
    
    def detect_anomalies(self, election_id: int) -> list:
        """
        Detect anomalies for a given election based on polling station performance.
        Currently, if the average interval between votes at a station is less than a threshold (e.g., 10 seconds),
        that polling station is flagged as anomalous.
        """
        # Reuse our analytics to get all station insights.
        station_insights = self.get_polling_station_insights(election_id)

        anomalies = []
        threshold = 10  # seconds; flag stations with unusually rapid vote submissions.
        for station in station_insights:
            avg_interval = station.get("average_interval_seconds")
            if avg_interval is not None and avg_interval < threshold:
                anomalies.append({
                    "polling_station": station["polling_station"],
                    "total_votes": station["total_votes"],
                    "average_interval_seconds": avg_interval,
                    "anomaly": f"High vote rate detected (avg interval {avg_interval:.1f}s is below threshold of {threshold}s)"
                })
        return anomalies
    
    def get_votes_by_region(self, election_id: int, region: str = None) -> list:
        """
        Aggregates vote data by region for the specified election.
        Optionally filter by a specific region.
        
        Returns a list of dictionaries with:
          - region
          - total_votes
          - (optionally, you can add more metrics like average vote interval or peak hour)
        """
        query = self.db.query(
            Vote.region,
            func.count(Vote.id).label("total_votes")
        ).filter(Vote.election_id == election_id)

        # If a specific region filter is provided, add it.
        if region:
            query = query.filter(Vote.region == region)
        
        query = query.group_by(Vote.region)
        results = query.all()

        # Convert results to a list of dictionaries.
        analytics = []
        for region_val, total_votes in results:
            analytics.append({
                "region": region_val,
                "total_votes": total_votes,
            })
        return analytics