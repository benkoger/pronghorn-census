ALTER TABLE usermanagement.users 
    ADD COLUMN email VARCHAR(320);
ALTER TABLE usermanagement.users 
    ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE usermanagement.users
	ADD CONSTRAINT unique_provider_user_id UNIQUE (external_auth_provider, external_auth_id);
ALTER TABLE usermanagement.users 
    ALTER COLUMN status SET DEFAULT 'invited';
ALTER TABLE usermanagement.users
	ADD COLUMN password_hash VARCHAR(255);
    UPDATE usermanagement.users 
    SET status = 'invited' 
    WHERE status IS NULL;