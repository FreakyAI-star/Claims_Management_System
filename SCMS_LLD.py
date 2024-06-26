from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict
from datetime import datetime
import re
import unittest

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

class ValidationError(Exception):
    pass

class ClaimsManagementSystem:
    def __init__(self):
        self.policyholders: Dict[str, Policyholder] = {}
        self.policies: Dict[str, Policy] = {}
        self.claims: Dict[str, Claim] = {}

    def add_policyholder(self, policyholder: Policyholder) -> None:
        self._validate_email(policyholder.email)
        self._validate_phone_number(policyholder.contact_number)
        if policyholder.id in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policyholder.id} already exists")
        self.policyholders[policyholder.id] = policyholder

    def add_policy(self, policy: Policy) -> None:
        if policy.policyholder_id not in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policy.policyholder_id} does not exist")
        if policy.id in self.policies:
            raise ValidationError(f"Policy with ID {policy.id} already exists")
        if policy.start_date >= policy.end_date:
            raise ValidationError("Policy start date must be before end date")
        if policy.coverage_amount <= 0:
            raise ValidationError("Coverage amount must be positive")
        self.policies[policy.id] = policy

    def submit_claim(self, claim: Claim) -> None:
        if claim.policy_id not in self.policies:
            raise ValidationError(f"Policy with ID {claim.policy_id} does not exist")
        if claim.id in self.claims:
            raise ValidationError(f"Claim with ID {claim.id} already exists")
        policy = self.policies[claim.policy_id]
        if claim.date_of_incident < policy.start_date or claim.date_of_incident > policy.end_date:
            raise ValidationError("Claim date must be within policy period")
        if claim.amount <= 0 or claim.amount > policy.coverage_amount:
            raise ValidationError(f"Claim amount must be positive and not exceed policy coverage of {policy.coverage_amount}")
        self.claims[claim.id] = claim

    def update_claim_status(self, claim_id: str, new_status: ClaimStatus) -> None:
        if claim_id not in self.claims:
            raise ValidationError(f"Claim with ID {claim_id} does not exist")
        claim = self.claims[claim_id]
        if claim.status == ClaimStatus.CLOSED:
            raise ValidationError("Cannot update a closed claim")
        claim.status = new_status

    def _validate_email(self, email: str) -> None:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValidationError("Invalid email format")

    def _validate_phone_number(self, phone: str) -> None:
        if not re.match(r"^\+?1?\d{9,15}$", phone):
            raise ValidationError("Invalid phone number format")

class TestClaimsManagementSystem(unittest.TestCase):
    def setUp(self):
        self.cms = ClaimsManagementSystem()
        self.policyholder = Policyholder("PH001", "John Doe", "+1234567890", "john@example.com")
        self.policy = Policy("POL001", "PH001", "Auto", datetime(2023, 1, 1), datetime(2024, 1, 1), 50000.0)
        self.claim = Claim("CL001", "POL001", datetime(2023, 6, 1), "Car accident", 5000.0)

    def test_add_policyholder(self):
        self.cms.add_policyholder(self.policyholder)
        self.assertIn("PH001", self.cms.policyholders)

    def test_add_policy(self):
        self.cms.add_policyholder(self.policyholder)
        self.cms.add_policy(self.policy)
        self.assertIn("POL001", self.cms.policies)

    def test_submit_claim(self):
        self.cms.add_policyholder(self.policyholder)
        self.cms.add_policy(self.policy)
        self.cms.submit_claim(self.claim)
        self.assertIn("CL001", self.cms.claims)

    def test_update_claim_status(self):
        self.cms.add_policyholder(self.policyholder)
        self.cms.add_policy(self.policy)
        self.cms.submit_claim(self.claim)
        self.cms.update_claim_status("CL001", ClaimStatus.APPROVED)
        self.assertEqual(self.cms.claims["CL001"].status, ClaimStatus.APPROVED)

    def test_invalid_email(self):
        invalid_policyholder = Policyholder("PH002", "Jane Doe", "+1234567890", "invalid_email")
        with self.assertRaises(ValidationError):
            self.cms.add_policyholder(invalid_policyholder)

    def test_invalid_claim_amount(self):
        self.cms.add_policyholder(self.policyholder)
        self.cms.add_policy(self.policy)
        invalid_claim = Claim("CL002", "POL001", datetime(2023, 6, 1), "Invalid claim", 60000.0)
        with self.assertRaises(ValidationError):
            self.cms.submit_claim(invalid_claim)

if __name__ == "__main__":
    unittest.main()