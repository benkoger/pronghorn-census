ALTER TABLE usermanagement.organizations_users
	ADD role_id int not null default 0;

ALTER TABLE usermanagement.organizations_users
	DROP CONSTRAINT organizations_users_pkey;

ALTER TABLE usermanagement.organizations_users 
	ADD CONSTRAINT organizations_users_pkey PRIMARY KEY (organization_id, user_id, role_id);

ALTER TABLE usermanagement.organizations_users
	ADD CONSTRAINT orgainizations_users_role_id_fkey FOREIGN KEY (role_id) REFERENCES usermanagement.roles (role_id) ON DELETE CASCADE ON UPDATE CASCADE;
