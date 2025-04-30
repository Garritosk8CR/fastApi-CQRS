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
    
    def get_polling_stations_by_election(self, election_id: int):
        return self.db.query(PollingStation).filter(PollingStation.election_id == election_id).all()
    
    def update_polling_station(self, station_id: int, name: str = None, location: str = None, capacity: int = None):
        polling_station = self.get_polling_station_by_id(station_id)
        if not polling_station:
            return None

        if name:
            polling_station.name = name
        if location:
            polling_station.location = location
        if capacity:
            polling_station.capacity = capacity

        self.db.commit()
        return polling_station