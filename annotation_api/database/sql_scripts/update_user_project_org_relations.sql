DROP TABLE projectmanagement.projects_users;


CREATE TABLE projectmanagement.projects_users (
  project_id integer NOT NULL DEFAULT 0,
  user_id integer NOT NULL DEFAULT 0,
  role_id integer NOT NULL DEFAULT 0,
  PRIMARY KEY (project_id, user_id, role_id)
);

ALTER TABLE projectmanagement.projects_users
  ADD FOREIGN KEY (project_id) REFERENCES projectmanagement.projects (project_id) ON DELETE SET DEFAULT ON UPDATE CASCADE;

ALTER TABLE projectmanagement.projects_users
  ADD FOREIGN KEY (user_id) REFERENCES usermanagement.users (user_id) ON DELETE SET DEFAULT ON UPDATE CASCADE;

ALTER TABLE projectmanagement.projects_users
  ADD FOREIGN KEY (role_id) REFERENCES usermanagement.roles (role_id) ON DELETE SET DEFAULT ON UPDATE CASCADE;
