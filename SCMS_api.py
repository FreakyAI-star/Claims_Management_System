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

#-------------------------------------------------------------
#                       API DEVELOPMENT
#-------------------------------------------------------------

from flask import Flask, request, jsonify

app = Flask(__name__)
cms = ClaimsManagementSystem()

# Helper function to parse dates
def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")

# Policyholder endpoints
@app.route('/policyholders', methods=['POST'])
def create_policyholder():
    data = request.json
    try:
        policyholder = Policyholder(
            id=data['id'],
            name=data['name'],
            contact_number=data['contact_number'],
            email=data['email'],
            date_of_birth=parse_date(data['date_of_birth'])
        )
        cms.create_policyholder(policyholder)
        return jsonify({"message": "Policyholder created successfully"}), 201
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/policyholders/<policyholder_id>', methods=['GET'])
def get_policyholder(policyholder_id):
    policyholder = cms.get_policyholder(policyholder_id)
    if policyholder:
        return jsonify({
            "id": policyholder.id,
            "name": policyholder.name,
            "contact_number": policyholder.contact_number,
            "email": policyholder.email,
            "date_of_birth": policyholder.date_of_birth.strftime("%Y-%m-%d")
        })
    return jsonify({"error": "Policyholder not found"}), 404

@app.route('/policyholders/<policyholder_id>', methods=['PUT'])
def update_policyholder(policyholder_id):
    data = request.json
    try:
        cms.update_policyholder(
            policyholder_id,
            name=data.get('name'),
            contact_number=data.get('contact_number'),
            email=data.get('email'),
            date_of_birth=parse_date(data['date_of_birth']) if 'date_of_birth' in data else None
        )
        return jsonify({"message": "Policyholder updated successfully"})
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/policyholders/<policyholder_id>', methods=['DELETE'])
def delete_policyholder(policyholder_id):
    try:
        cms.delete_policyholder(policyholder_id)
        return jsonify({"message": "Policyholder deleted successfully"})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

# Policy endpoints
@app.route('/policies', methods=['POST'])
def create_policy():
    data = request.json
    try:
        policy = Policy(
            id=data['id'],
            policyholder_id=data['policyholder_id'],
            type=data['type'],
            start_date=parse_date(data['start_date']),
            end_date=parse_date(data['end_date']),
            coverage_amount=data['coverage_amount'],
            premium=data['premium']
        )
        cms.create_policy(policy)
        return jsonify({"message": "Policy created successfully"}), 201
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    policy = cms.get_policy(policy_id)
    if policy:
        return jsonify({
            "id": policy.id,
            "policyholder_id": policy.policyholder_id,
            "type": policy.type,
            "start_date": policy.start_date.strftime("%Y-%m-%d"),
            "end_date": policy.end_date.strftime("%Y-%m-%d"),
            "coverage_amount": policy.coverage_amount,
            "premium": policy.premium
        })
    return jsonify({"error": "Policy not found"}), 404

@app.route('/policies/<policy_id>', methods=['PUT'])
def update_policy(policy_id):
    data = request.json
    try:
        cms.update_policy(
            policy_id,
            type=data.get('type'),
            start_date=parse_date(data['start_date']) if 'start_date' in data else None,
            end_date=parse_date(data['end_date']) if 'end_date' in data else None,
            coverage_amount=data.get('coverage_amount'),
            premium=data.get('premium')
        )
        return jsonify({"message": "Policy updated successfully"})
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    try:
        cms.delete_policy(policy_id)
        return jsonify({"message": "Policy deleted successfully"})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

# Claim endpoints
@app.route('/claims', methods=['POST'])
def create_claim():
    data = request.json
    try:
        claim = Claim(
            id=data['id'],
            policy_id=data['policy_id'],
            date_of_incident=parse_date(data['date_of_incident']),
            description=data['description'],
            amount=data['amount'],
            status=ClaimStatus(data.get('status', 'Submitted')),
            date_submitted=parse_date(data.get('date_submitted', datetime.now().strftime("%Y-%m-%d")))
        )
        cms.create_claim(claim)
        return jsonify({"message": "Claim created successfully"}), 201
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/claims/<claim_id>', methods=['GET'])
def get_claim(claim_id):
    claim = cms.get_claim(claim_id)
    if claim:
        return jsonify({
            "id": claim.id,
            "policy_id": claim.policy_id,
            "date_of_incident": claim.date_of_incident.strftime("%Y-%m-%d"),
            "description": claim.description,
            "amount": claim.amount,
            "status": claim.status.value,
            "date_submitted": claim.date_submitted.strftime("%Y-%m-%d")
        })
    return jsonify({"error": "Claim not found"}), 404

@app.route('/claims/<claim_id>', methods=['PUT'])
def update_claim(claim_id):
    data = request.json
    try:
        cms.update_claim(
            claim_id,
            description=data.get('description'),
            amount=data.get('amount'),
            status=ClaimStatus(data['status']) if 'status' in data else None
        )
        return jsonify({"message": "Claim updated successfully"})
    except (ValidationError, BusinessRuleViolation) as e:
        return jsonify({"error": str(e)}), 400

@app.route('/claims/<claim_id>', methods=['DELETE'])
def delete_claim(claim_id):
    try:
        cms.delete_claim(claim_id)
        return jsonify({"message": "Claim deleted successfully"})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)