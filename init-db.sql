CREATE USER trader WITH PASSWORD 'change_me_secure_password';
CREATE DATABASE pulse_traders OWNER trader;
GRANT ALL PRIVILEGES ON DATABASE pulse_traders TO trader;
