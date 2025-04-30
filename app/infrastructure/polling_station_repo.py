from sqlalchemy.orm import Session
from app.infrastructure.models import PollingStation
class PollingStationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_polling_station(self, name: str, location: str, election_id: int, capacity: int):
        polling_station = PollingStation(name=name, location=location, election_id=election_id, capacity=capacity)
        self.db.add(polling_station)
        self.db.commit()
        self.db.refresh(polling_station)
        return polling_station
    
    def get_polling_station_by_id(self, station_id: int):
        return self.db.query(PollingStation).filter(PollingStation.id == station_id).first()