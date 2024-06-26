from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
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

    # Policyholder CRUD operations
    def create_policyholder(self, policyholder: Policyholder) -> None:
        self._validate_email(policyholder.email)
        self._validate_phone_number(policyholder.contact_number)
        if policyholder.id in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policyholder.id} already exists")
        self.policyholders[policyholder.id] = policyholder

    def get_policyholder(self, policyholder_id: str) -> Optional[Policyholder]:
        return self.policyholders.get(policyholder_id)

    def update_policyholder(self, policyholder_id: str, name: Optional[str] = None, 
                            contact_number: Optional[str] = None, email: Optional[str] = None) -> None:
        if policyholder_id not in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policyholder_id} does not exist")
        policyholder = self.policyholders[policyholder_id]
        if name:
            policyholder.name = name
        if contact_number:
            self._validate_phone_number(contact_number)
            policyholder.contact_number = contact_number
        if email:
            self._validate_email(email)
            policyholder.email = email

    def delete_policyholder(self, policyholder_id: str) -> None:
        if policyholder_id not in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policyholder_id} does not exist")
        del self.policyholders[policyholder_id]
        # Delete associated policies
        policies_to_delete = [policy_id for policy_id, policy in self.policies.items() if policy.policyholder_id == policyholder_id]
        for policy_id in policies_to_delete:
            self.delete_policy(policy_id)

    # Policy CRUD operations
    def create_policy(self, policy: Policy) -> None:
        if policy.policyholder_id not in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policy.policyholder_id} does not exist")
        if policy.id in self.policies:
            raise ValidationError(f"Policy with ID {policy.id} already exists")
        if policy.start_date >= policy.end_date:
            raise ValidationError("Policy start date must be before end date")
        if policy.coverage_amount <= 0:
            raise ValidationError("Coverage amount must be positive")
        self.policies[policy.id] = policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)

    def update_policy(self, policy_id: str, type: Optional[str] = None, 
                      start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                      coverage_amount: Optional[float] = None) -> None:
        if policy_id not in self.policies:
            raise ValidationError(f"Policy with ID {policy_id} does not exist")
        policy = self.policies[policy_id]
        if type:
            policy.type = type
        if start_date:
            policy.start_date = start_date
        if end_date:
            policy.end_date = end_date
        if coverage_amount is not None:
            if coverage_amount <= 0:
                raise ValidationError("Coverage amount must be positive")
            policy.coverage_amount = coverage_amount
        if policy.start_date >= policy.end_date:
            raise ValidationError("Policy start date must be before end date")

    def delete_policy(self, policy_id: str) -> None:
        if policy_id not in self.policies:
            raise ValidationError(f"Policy with ID {policy_id} does not exist")
        del self.policies[policy_id]
        # Delete associated claims
        claims_to_delete = [claim_id for claim_id, claim in self.claims.items() if claim.policy_id == policy_id]
        for claim_id in claims_to_delete:
            self.delete_claim(claim_id)

    # Claim CRUD operations
    def create_claim(self, claim: Claim) -> None:
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

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self.claims.get(claim_id)

    def update_claim(self, claim_id: str, description: Optional[str] = None, 
                     amount: Optional[float] = None, status: Optional[ClaimStatus] = None) -> None:
        if claim_id not in self.claims:
            raise ValidationError(f"Claim with ID {claim_id} does not exist")
        claim = self.claims[claim_id]
        if description:
            claim.description = description
        if amount is not None:
            policy = self.policies[claim.policy_id]
            if amount <= 0 or amount > policy.coverage_amount:
                raise ValidationError(f"Claim amount must be positive and not exceed policy coverage of {policy.coverage_amount}")
            claim.amount = amount
        if status:
            if claim.status == ClaimStatus.CLOSED:
                raise ValidationError("Cannot update a closed claim")
            claim.status = status

    def delete_claim(self, claim_id: str) -> None:
        if claim_id not in self.claims:
            raise ValidationError(f"Claim with ID {claim_id} does not exist")
        del self.claims[claim_id]

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

    # Add tests for CRUD operations here
    def test_create_and_get_policyholder(self):
        self.cms.create_policyholder(self.policyholder)
        retrieved_policyholder = self.cms.get_policyholder("PH001")
        self.assertEqual(retrieved_policyholder, self.policyholder)

    def test_update_policyholder(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.update_policyholder("PH001", name="Jane Doe", email="jane@example.com")
        updated_policyholder = self.cms.get_policyholder("PH001")
        self.assertEqual(updated_policyholder.name, "Jane Doe")
        self.assertEqual(updated_policyholder.email, "jane@example.com")

    def test_delete_policyholder(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.create_policy(self.policy)
        self.cms.delete_policyholder("PH001")
        self.assertIsNone(self.cms.get_policyholder("PH001"))
        self.assertIsNone(self.cms.get_policy("POL001"))

# Similar tests for Policy and Claim CRUD operations

if __name__ == "__main__":
    unittest.main()