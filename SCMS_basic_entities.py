from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict
from datetime import datetime, timedelta

class ClaimStatus(Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CLOSED = "Closed"

@dataclass
class Policyholder:
    id: str
    name: str
    contact_number: str
    email: str

@dataclass
class Policy:
    id: str
    policyholder_id: str
    type: str
    start_date: datetime
    end_date: datetime
    coverage_amount: float

@dataclass
class Claim:
    id: str
    policy_id: str
    date_of_incident: datetime
    description: str
    amount: float
    status: ClaimStatus = ClaimStatus.SUBMITTED
    date_submitted: datetime = field(default_factory=datetime.now)

class ClaimsManagementSystem:
    def __init__(self):
        self.policyholders: Dict[str, Policyholder] = {}
        self.policies: Dict[str, Policy] = {}
        self.claims: Dict[str, Claim] = {}


# Initialize the Claims Management System
cms = ClaimsManagementSystem()

# Create a policyholder
policyholder = Policyholder(
    id="PH001",
    name="John Doe",
    contact_number="123-456-7890",
    email="john.doe@example.com"
)
cms.policyholders[policyholder.id] = policyholder

# Create a policy for the policyholder
policy = Policy(
    id="POL001",
    policyholder_id=policyholder.id,
    type="Auto Insurance",
    start_date=datetime.now(),
    end_date=datetime.now() + timedelta(days=365),
    coverage_amount=50000.00
)
cms.policies[policy.id] = policy

# Submit a claim
claim = Claim(
    id="CLM001",
    policy_id=policy.id,
    date_of_incident=datetime.now() - timedelta(days=5),
    description="Car accident - front bumper damage",
    amount=2000.00
)
cms.claims[claim.id] = claim

# Print out the information
print(f"Policyholder: {cms.policyholders[policyholder.id]}")
print(f"Policy: {cms.policies[policy.id]}")
print(f"Claim: {cms.claims[claim.id]}")

# Update claim status
cms.claims[claim.id].status = ClaimStatus.UNDER_REVIEW

print(f"Updated Claim Status: {cms.claims[claim.id].status}")