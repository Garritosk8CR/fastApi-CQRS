from typing import Dict
from app.domain.voter import Voter
from app.domain.election import Election

voter_database: Dict[int, Voter] = {}
election_database: Dict[int, Election] = {}
