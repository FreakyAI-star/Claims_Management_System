from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
import requests
from functools import wraps
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from urllib.parse import unquote

# New imports for Prometheus prometheus_metrics
from prometheus_flask_exporter import PrometheusMetrics
import psutil
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

app = Flask(__name__)
# Initialize Prometheus prometheus_metrics
prometheus_metrics = PrometheusMetrics(app)

CORS(app)

# Custom prometheus_metrics
prometheus_metrics.info('app_info', 'Application info', version='1.0.3')

# CPU and Memory usage
@prometheus_metrics.gauge('cpu_usage_percent', 'CPU Usage')
def cpu_usage():
    return psutil.cpu_percent()

@prometheus_metrics.gauge('memory_usage_percent', 'Memory Usage')
def memory_usage():
    return psutil.virtual_memory().percent

# Define custom metrics
http_request_total = Counter('http_request_total', 'Total HTTP request count',
                             ['method', 'status'])

request_by_path = Counter('request_by_path', 'Request count by request paths',
                          ['path'])

http_request_duration = Histogram('http_request_duration_seconds',
                                  'HTTP request duration in seconds',
                                  ['path', 'method'])

authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    },
}

api = Api(app, version='1.0', title='Claims Management System API Gateway',
          description='API Gateway for Claims Management System',
          authorizations=authorizations,
          security='Bearer Auth')

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
jwt = JWTManager(app)

# Your main application URL
MAIN_APP_URL = "http://127.0.0.1:5000"

# Database connection
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        dbname="claims_management",
        user="postgres",
        password="********",
        host="localhost",
        port="5432"
    )
    try:
        yield conn
    finally:
        conn.close()

# Models
user_model = api.model('User', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'role': fields.String(required=True, description='User role')
})

login_model = api.model('Login', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password')
})

post_model = api.model('Post', {
    'id': fields.Integer(required=True, description='Policyholder ID'),
    'name': fields.String(required=True, description='Policyholder name'),
    'contact_number': fields.String(required=True, description='Contact Number of Policyholder'),
    'email': fields.String(required=True, description='Email ID of Policyholder'),
    'date_of_birth': fields.Date(required=True, description='Date of Birth of Policyholder'),
})

put_model = api.model('Put', {
    'name': fields.String(required=True, description='Policyholder name'),
    'contact_number': fields.String(required=True, description='Contact Number of Policyholder'),
    'email': fields.String(required=True, description='Email ID of Policyholder'),
    'date_of_birth': fields.Date(required=True, description='Date of Birth of Policyholder'),
})

token_model = api.model('Token', {
    'access_token': fields.String(description='JWT access token')
})

error_model = api.model('Error', {
    'message': fields.String(description='Error message')
})

# Namespaces
ns_auth = api.namespace('auth', description='Authentication operations')
ns_gateway = api.namespace('gateway', description='Gateway operations')

# Authentication routes
@ns_auth.route('/register')
class Register(Resource):
    @api.expect(user_model)
    @api.response(201, 'User registered successfully')
    @api.response(400, 'Validation error', error_model)
    def post(self):
        """Register a new user"""
        data = request.json
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')

        if not username or not password or not role:
            return {'message': 'Missing required fields'}, 400

        hashed_password = generate_password_hash(password, method='sha256')

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                                (username, hashed_password, role))
                    conn.commit()
            return {'message': 'User registered successfully'}, 201
        except psycopg2.IntegrityError:
            return {'message': 'Username already exists'}, 400
        except Exception as e:
            return {'message': str(e)}, 500

@ns_auth.route('/login')
class Login(Resource):
    @api.expect(login_model)
    @api.response(200, 'Login successful', token_model)
    @api.response(401, 'Invalid username or password', error_model)
    def post(self):
        """Login and receive access token"""
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'message': 'Missing username or password'}, 400

        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cur.fetchone()

            if user and check_password_hash(user['password'], password):
                access_token = create_access_token(identity=user['id'])
                return {'access_token': access_token}, 200
            else:
                return {'message': 'Invalid username or password'}, 401
        except Exception as e:
            return {'message': str(e)}, 500
        
# Wrap the _forward_request method to capture metrics
def capture_metrics(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        path = request.path
        method = request.method
        
        # Increment request count
        request_by_path.labels(path=path).inc()
        
        # Measure request duration
        with http_request_duration.labels(path=path, method=method).time():
            response = func(*args, **kwargs)
        
        # Increment total request count
        http_request_total.labels(method=method, status=response[1]).inc()
        
        return response
    return wrapper

# Gateway routes
@ns_gateway.route('/<path:path>')
class Gateway(Resource):
    @api.doc(security='Bearer Auth')
    @jwt_required()
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @api.response(500, 'Internal server error', error_model)
    @capture_metrics
    def get(self, path):
        """Forward GET request to main application"""
        return self._forward_request('GET', path)

    @api.doc(security='Bearer Auth')
    @jwt_required()
    @api.expect(post_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @api.response(500, 'Internal server error', error_model)
    @capture_metrics
    def post(self, path):
        """Forward POST request to main application"""
        return self._forward_request('POST', path)

    @api.doc(security='Bearer Auth')
    @jwt_required()
    @api.expect(put_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @api.response(500, 'Internal server error', error_model)
    @capture_metrics
    def put(self, path):
        """Forward PUT request to main application"""
        return self._forward_request('PUT', path)

    @api.doc(security='Bearer Auth')
    @jwt_required()
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized', error_model)
    @api.response(500, 'Internal server error', error_model)
    @capture_metrics
    def delete(self, path):
        """Forward DELETE request to main application"""
        return self._forward_request('DELETE', path)

    def _forward_request(self, method, path):
        current_user_id = get_jwt_identity()
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user_id,))
                user_role = cur.fetchone()['role']

        headers = {key: value for (key, value) in request.headers if key != 'Host'}
        headers['X-User-Id'] = str(current_user_id)
        headers['X-User-Role'] = user_role
        
        try:
            decoded_path = unquote(path)
            response = requests.request(
                method=method,
                url=f"{MAIN_APP_URL}/{decoded_path}",
                headers=headers,
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False)
            
            return response.json(), response.status_code
        except requests.RequestException as e:
            return {'message': f"Error occurred while forwarding request: {str(e)}"}, 500

# Explicitly add metrics route
@app.route('/metrics')
@prometheus_metrics.do_not_track()
def metrics_route():
    print('Metrics route hit')
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(port=5001, debug=True)