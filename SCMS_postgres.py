from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os

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

# Custom exception for database errors
class DatabaseError(Exception):
    pass

@contextmanager
def get_db_connection():
    # conn = psycopg2.connect(
    #     dbname="claims_management",
    #     user="postgres",
    #     password="********",
    #     host="localhost",
    #     port="5432"
    # )
    DATABASE_URL = os.environ['DATABASE_URL']
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

class ClaimsManagementSystem:
    def _execute_transaction(self, func, *args, **kwargs):
        with get_db_connection() as conn:
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    result = func(cur, *args, **kwargs)
                conn.commit()
                return result
            except psycopg2.Error as e:
                conn.rollback()
                raise DatabaseError(str(e))

    # Policyholder CRUD operations
    def create_policyholder(self, policyholder: Policyholder) -> None:
        def _create(cur):
            self._validate_policyholder(policyholder)
            cur.execute("""
                INSERT INTO policyholders (id, name, contact_number, email, date_of_birth)
                VALUES (%(id)s, %(name)s, %(contact_number)s, %(email)s, %(date_of_birth)s)
            """, policyholder.__dict__)
        self._execute_transaction(_create)

    def get_policyholder(self, policyholder_id: str) -> Optional[Policyholder]:
        def _get(cur):
            cur.execute("SELECT * FROM policyholders WHERE id = %(id)s", {'id': policyholder_id})
            result = cur.fetchone()
            if result:
                return Policyholder(**result)
            return None
        return self._execute_transaction(_get)

    def update_policyholder(self, policyholder_id: str, name: Optional[str] = None, 
                            contact_number: Optional[str] = None, email: Optional[str] = None,
                            date_of_birth: Optional[datetime] = None) -> None:
        def _update(cur):
            policyholder = self.get_policyholder(policyholder_id)
            if not policyholder:
                raise ValidationError(f"Policyholder with ID {policyholder_id} does not exist")
            
            update_fields = []
            values = {'id': policyholder_id}
            if name:
                update_fields.append("name = %(name)s")
                values['name'] = name
            if contact_number:
                self._validate_phone_number(contact_number)
                update_fields.append("contact_number = %(contact_number)s")
                values['contact_number'] = contact_number
            if email:
                self._validate_email(email)
                update_fields.append("email = %(email)s")
                values['email'] = email
            if date_of_birth:
                self._validate_date_of_birth(date_of_birth)
                update_fields.append("date_of_birth = %(date_of_birth)s")
                values['date_of_birth'] = date_of_birth
            
            if update_fields:
                cur.execute(f"""
                    UPDATE policyholders
                    SET {', '.join(update_fields)}
                    WHERE id = %(id)s
                """, values)
        self._execute_transaction(_update)

    def delete_policyholder(self, policyholder_id: str) -> None:
        def _delete(cur):
            cur.execute("DELETE FROM policyholders WHERE id = %s", (policyholder_id,))
            if cur.rowcount == 0:
                raise ValidationError(f"Policyholder with ID {policyholder_id} does not exist")
        self._execute_transaction(_delete)

    # Policy CRUD operations
    def create_policy(self, policy: Policy) -> None:
        def _create(cur):
            self._validate_policy(cur, policy)
            cur.execute("""
                INSERT INTO policies (id, policyholder_id, type, start_date, end_date, coverage_amount, premium)
                VALUES (%(id)s, %(policyholder_id)s, %(type)s, %(start_date)s, %(end_date)s, %(coverage_amount)s, %(premium)s)
            """, policy.__dict__)
        self._execute_transaction(_create)

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        def _get(cur):
            cur.execute("SELECT * FROM policies WHERE id = %(id)s", {'id': policy_id})
            result = cur.fetchone()
            if result:
                return Policy(**result)
            return None
        return self._execute_transaction(_get)

    def update_policy(self, policy_id: str, type: Optional[str] = None, 
                      start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                      coverage_amount: Optional[float] = None, premium: Optional[float] = None) -> None:
        def _update(cur):
            policy = self.get_policy(policy_id)
            if not policy:
                raise ValidationError(f"Policy with ID {policy_id} does not exist")
            
            update_fields = []
            values = {'id': policy_id}
            if type:
                update_fields.append("type = %(type)s")
                values['type'] = type
            if start_date:
                update_fields.append("start_date = %(start_date)s")
                values['start_date'] = start_date
            if end_date:
                update_fields.append("end_date = %(end_date)s")
                values['end_date'] = end_date
            if coverage_amount is not None:
                update_fields.append("coverage_amount = %(coverage_amount)s")
                values['coverage_amount'] = coverage_amount
            if premium is not None:
                update_fields.append("premium = %(premium)s")
                values['premium'] = premium
            
            if update_fields:
                cur.execute(f"""
                    UPDATE policies
                    SET {', '.join(update_fields)}
                    WHERE id = %(id)s
                """, values)
            
            updated_policy = self.get_policy(policy_id)
            self._validate_policy(cur, updated_policy)
        self._execute_transaction(_update)

    def delete_policy(self, policy_id: str) -> None:
        def _delete(cur):
            cur.execute("DELETE FROM policies WHERE id = %s", (policy_id,))
            if cur.rowcount == 0:
                raise ValidationError(f"Policy with ID {policy_id} does not exist")
        self._execute_transaction(_delete)

    # Claim CRUD operations
    def create_claim(self, claim: Claim) -> None:
        def _create(cur):
            self._validate_claim(cur, claim)
            claim_dict = claim.__dict__.copy()
            claim_dict['status'] = claim.status.value  # Convert Enum to string
            cur.execute("""
                INSERT INTO claims (id, policy_id, date_of_incident, description, amount, status, date_submitted)
                VALUES (%(id)s, %(policy_id)s, %(date_of_incident)s, %(description)s, %(amount)s, %(status)s, %(date_submitted)s)
            """, claim_dict)
        self._execute_transaction(_create)

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        def _get(cur):
            cur.execute("SELECT * FROM claims WHERE id = %(id)s", {'id': claim_id})
            result = cur.fetchone()
            if result:
                result['status'] = ClaimStatus(result['status'])
                return Claim(**result)
            return None
        return self._execute_transaction(_get)

    def update_claim(self, claim_id: str, description: Optional[str] = None, 
                     amount: Optional[float] = None, status: Optional[ClaimStatus] = None) -> None:
        def _update(cur):
            claim = self.get_claim(claim_id)
            if not claim:
                raise ValidationError(f"Claim with ID {claim_id} does not exist")
            
            update_fields = []
            values = {'id': claim_id}
            if description:
                update_fields.append("description = %(description)s")
                values['description'] = description
            if amount is not None:
                update_fields.append("amount = %(amount)s")
                values['amount'] = amount
            if status:
                update_fields.append("status = %(status)s")
                values['status'] = status.value  # Convert Enum to string
            
            if update_fields:
                cur.execute(f"""
                    UPDATE claims
                    SET {', '.join(update_fields)}
                    WHERE id = %(id)s
                """, values)
            
            updated_claim = self.get_claim(claim_id)
            self._validate_claim(cur, updated_claim)
        self._execute_transaction(_update)

    def delete_claim(self, claim_id: str) -> None:
        def _delete(cur):
            cur.execute("DELETE FROM claims WHERE id = %s", (claim_id,))
            if cur.rowcount == 0:
                raise ValidationError(f"Claim with ID {claim_id} does not exist")
        self._execute_transaction(_delete)

    # Validation methods
    def _validate_policyholder(self, policyholder: Policyholder) -> None:
        self._validate_email(policyholder.email)
        self._validate_phone_number(policyholder.contact_number)
        self._validate_date_of_birth(policyholder.date_of_birth)

    def _validate_policy(self, cur, policy: Policy) -> None:
        cur.execute("SELECT * FROM policyholders WHERE id = %(id)s", {'id': policy.policyholder_id})
        policyholder = cur.fetchone()
        if not policyholder:
            raise ValidationError(f"Policyholder with ID {policy.policyholder_id} does not exist")
        if policy.start_date >= policy.end_date:
            raise ValidationError("Policy start date must be before end date")
        if policy.coverage_amount <= 0:
            raise ValidationError("Coverage amount must be positive")
        if policy.premium <= 0:
            raise ValidationError("Premium must be positive")
        # policyholder_dob = datetime.combine(policyholder['date_of_birth'], datetime.min.time())
        policyholder_dob = policyholder['date_of_birth']
        # Convert both to datetime.date if they are not already
        if isinstance(policyholder_dob, datetime):
            policyholder_dob = policyholder_dob.date()
        if isinstance(policy.start_date, datetime):
            policy.start_date = policy.start_date.date()
        if (policy.start_date - policyholder_dob).days < 18 * 365:
            raise BusinessRuleViolation("Policyholder must be at least 18 years old at policy start date")

    def _validate_claim(self, cur, claim: Claim) -> None:
        cur.execute("SELECT * FROM policies WHERE id = %(id)s", {'id': claim.policy_id})
        policy = cur.fetchone()
        if not policy:
            raise ValidationError(f"Policy with ID {claim.policy_id} does not exist")
        policy_sd = policy['start_date']
        policy_ed = policy['end_date']
        policy_ca = policy['coverage_amount']
        # Convert both to datetime.date if they are not already
        if isinstance(policy_sd, datetime):
            policy_sd = policy_sd.date()
        if isinstance(policy_ed, datetime):
            policy_ed = policy_ed.date()
        if isinstance(policy_ca, datetime):
            policy_ca = policy_ca.date()
        if isinstance(claim.date_of_incident, datetime):
            claim.date_of_incident = claim.date_of_incident.date()
        if isinstance(claim.date_submitted, datetime):
            claim.date_submitted = claim.date_submitted.date()
        if claim.date_of_incident < policy_sd or claim.date_of_incident > policy_ed:
            raise ValidationError("Claim date must be within policy period")
        if claim.amount <= 0 or claim.amount > policy_ca:
            raise ValidationError(f"Claim amount must be positive and not exceed policy coverage of {policy_ca}")
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

@app.route('/', methods=['GET'])
def hello():
    return "Welcome to the Claims Management System"

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

@app.errorhandler(DatabaseError)
def handle_database_error(error):
    return jsonify({"error": str(error)}), 500

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({"error": str(error)}), 400

@app.errorhandler(BusinessRuleViolation)
def handle_business_rule_violation(error):
    return jsonify({"error": str(error)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)