from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, timedelta
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
    date_of_birth: datetime

@dataclass
class Policy:
    id: str
    policyholder_id: str
    type: str
    start_date: datetime
    end_date: datetime
    coverage_amount: float
    premium: float

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

class BusinessRuleViolation(Exception):
    pass

class ClaimsManagementSystem:
    def __init__(self):
        self.policyholders: Dict[str, Policyholder] = {}
        self.policies: Dict[str, Policy] = {}
        self.claims: Dict[str, Claim] = {}

    # Policyholder CRUD operations
    def create_policyholder(self, policyholder: Policyholder) -> None:
        self._validate_policyholder(policyholder)
        if policyholder.id in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policyholder.id} already exists")
        self.policyholders[policyholder.id] = policyholder

    def get_policyholder(self, policyholder_id: str) -> Optional[Policyholder]:
        return self.policyholders.get(policyholder_id)

    def update_policyholder(self, policyholder_id: str, name: Optional[str] = None, 
                            contact_number: Optional[str] = None, email: Optional[str] = None,
                            date_of_birth: Optional[datetime] = None) -> None:
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
        if date_of_birth:
            self._validate_date_of_birth(date_of_birth)
            policyholder.date_of_birth = date_of_birth

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
        self._validate_policy(policy)
        if policy.id in self.policies:
            raise ValidationError(f"Policy with ID {policy.id} already exists")
        self.policies[policy.id] = policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)

    def update_policy(self, policy_id: str, type: Optional[str] = None, 
                      start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                      coverage_amount: Optional[float] = None, premium: Optional[float] = None) -> None:
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
            policy.coverage_amount = coverage_amount
        if premium is not None:
            policy.premium = premium
        self._validate_policy(policy)

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
        self._validate_claim(claim)
        if claim.id in self.claims:
            raise ValidationError(f"Claim with ID {claim.id} already exists")
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
            claim.amount = amount
        if status:
            claim.status = status
        self._validate_claim(claim)

    def delete_claim(self, claim_id: str) -> None:
        if claim_id not in self.claims:
            raise ValidationError(f"Claim with ID {claim_id} does not exist")
        del self.claims[claim_id]

    # Validation methods
    def _validate_policyholder(self, policyholder: Policyholder) -> None:
        self._validate_email(policyholder.email)
        self._validate_phone_number(policyholder.contact_number)
        self._validate_date_of_birth(policyholder.date_of_birth)

    def _validate_policy(self, policy: Policy) -> None:
        if policy.policyholder_id not in self.policyholders:
            raise ValidationError(f"Policyholder with ID {policy.policyholder_id} does not exist")
        if policy.start_date >= policy.end_date:
            raise ValidationError("Policy start date must be before end date")
        if policy.coverage_amount <= 0:
            raise ValidationError("Coverage amount must be positive")
        if policy.premium <= 0:
            raise ValidationError("Premium must be positive")
        policyholder = self.policyholders[policy.policyholder_id]
        if (policy.start_date - policyholder.date_of_birth).days < 18 * 365:
            raise BusinessRuleViolation("Policyholder must be at least 18 years old at policy start date")

    def _validate_claim(self, claim: Claim) -> None:
        if claim.policy_id not in self.policies:
            raise ValidationError(f"Policy with ID {claim.policy_id} does not exist")
        policy = self.policies[claim.policy_id]
        if claim.date_of_incident < policy.start_date or claim.date_of_incident > policy.end_date:
            raise ValidationError("Claim date must be within policy period")
        if claim.amount <= 0 or claim.amount > policy.coverage_amount:
            raise ValidationError(f"Claim amount must be positive and not exceed policy coverage of {policy.coverage_amount}")
        if claim.date_submitted < claim.date_of_incident:
            raise ValidationError("Claim submission date cannot be earlier than the incident date")
        if (claim.date_submitted - claim.date_of_incident).days > 30:
            raise BusinessRuleViolation("Claims must be submitted within 30 days of the incident")

    def _validate_email(self, email: str) -> None:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValidationError("Invalid email format")

    def _validate_phone_number(self, phone: str) -> None:
        if not re.match(r"^\+?1?\d{9,15}$", phone):
            raise ValidationError("Invalid phone number format")

    def _validate_date_of_birth(self, date_of_birth: datetime) -> None:
        if date_of_birth > datetime.now():
            raise ValidationError("Date of birth cannot be in the future")
        if (datetime.now() - date_of_birth).days < 18 * 365:
            raise BusinessRuleViolation("Policyholder must be at least 18 years old")

class TestClaimsManagementSystem(unittest.TestCase):
    def setUp(self):
        self.cms = ClaimsManagementSystem()
        self.policyholder = Policyholder("PH001", "John Doe", "+1234567890", "john@example.com", datetime(1980, 1, 1))
        self.policy = Policy("POL001", "PH001", "Auto", datetime(2023, 1, 1), datetime(2024, 1, 1), 50000.0, 1000.0)
        self.claim = Claim("CL001", "POL001", datetime(2023, 6, 1), "Car accident", 5000.0)

    def test_create_valid_policyholder(self):
        self.cms.create_policyholder(self.policyholder)
        self.assertIn("PH001", self.cms.policyholders)

    def test_create_underage_policyholder(self):
        underage_policyholder = Policyholder("PH002", "Jane Doe", "+1234567890", "jane@example.com", datetime.now() - timedelta(days=17*365))
        with self.assertRaises(BusinessRuleViolation):
            self.cms.create_policyholder(underage_policyholder)

    def test_create_valid_policy(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.create_policy(self.policy)
        self.assertIn("POL001", self.cms.policies)

    def test_create_policy_with_invalid_dates(self):
        self.cms.create_policyholder(self.policyholder)
        invalid_policy = Policy("POL002", "PH001", "Auto", datetime(2024, 1, 1), datetime(2023, 1, 1), 50000.0, 1000.0)
        with self.assertRaises(ValidationError):
            self.cms.create_policy(invalid_policy)

    def test_create_valid_claim(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.create_policy(self.policy)
        self.cms.create_claim(self.claim)
        self.assertIn("CL001", self.cms.claims)

    def test_create_claim_exceeding_coverage(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.create_policy(self.policy)
        invalid_claim = Claim("CL002", "POL001", datetime(2023, 6, 1), "Expensive accident", 60000.0)
        with self.assertRaises(ValidationError):
            self.cms.create_claim(invalid_claim)

    def test_create_late_claim(self):
        self.cms.create_policyholder(self.policyholder)
        self.cms.create_policy(self.policy)
        late_claim = Claim("CL002", "POL001", datetime(2023, 1, 1), "Late report", 1000.0, date_submitted=datetime(2023, 3, 1))
        with self.assertRaises(BusinessRuleViolation):
            self.cms.create_claim(late_claim)

if __name__ == "__main__":
    unittest.main()