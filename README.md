# Assisted Labeling & Census Software

The annotation software is an SPA (Single Page Application) written in VueJS designed to assist in the production of labeled training data by implementing a method known as model assisted labeling with a few creative twists. In a greater scope, this tool is envisioned to be a ubiquitous tool for managing wildlife census projects using computer vision models. The goal is to create an intuitive interface that allows for the rapid scalining of specialized models capable of accurately tracking herd populations with minimal human oversight. 

This tool is designed to be easily and rapidly scalable using containerization tools such as podman or docker. The included compose and container files are compatible with any containerization service that implements the [OCI](https://opencontainers.org/) (Open Container Initiative) standards. It is recommended to deploy this project to a linux system, primarily as a windows based deployment has not currently been tested. This project was designed with modularity at its core, meaning each component in the stack can be used in isolation. For example, one could take the API and the database and write their own front end.

## Tech Stack

* Postgresql 
* Flask
* Gunicorn
* Valkey
* VueJS with Typescript
* Nginx
* CEPH Object Gateway S3 API (Interchangable with AWS S3)

### Major Components

1. **API:** The glue that holds this project together is its flask-based restful API built on top of a  custom database abstraction layer built with the psycopg3 package.

2. **Auto Cropper:** The auto cropper python package automates the process of creating cropped training data by leveraging machine learning predictions and human verification to dramatically increase the rate at which data can be prepared. 

3. **Database:** This project makes use of the SQL relational database Postgresql, which enables the rapid management of structured relational data (such as machine learning predictions and annotations).

4. **Valkey:** Valkey is an open source fork of the caching tool *redis*. Redis (valkey) caches are used to increase performance and enable scalability of web applications just like this one. [Valkey](https://valkey.io/) <-> [Redis](https://redis.io/).

5. **Frontend** The frontend is a lazily loaded SPA (Single Page Application) built with VueJS and typescript, allowing for a feature rich, high performance front end that enables a seamless user experience.

### Database Abstraction

In the interest of performance and scalability we opted not to use an ORM (Object Relational Mapper), and instead write our own SQL queries to be executed using the excellent [psycopg3](https://pypi.org/project/psycopg/) package. Our abstraction layer is a semi typed OOP module that makes use of a decorated private interface wrapped into a context manager that handles the connection pool. Effectively the entire context of the connection is abstracted away from the API layer. The database layer also automatically associates rows from Postgres to their class defined in the crop generator, effectively emulating one of the benefits of an ORM while avoiding the performance related drawbacks.

```python
	#THIS BLOCK IS OUTDATED 

	import database as db # Generic name for increased performance

	db_config = {
		'dbname': x,
		'user': y,
		'password': z,
		...
	}

	base = db.Database(db_config) # Instantiate with config dictionary

	project = base.create_project('example') # Object is created in the database and python, connection is automatically handeled by the package.

	print(project.name)

	project.name = 'example_2'

	base.update_project(project) # Database is informed of the change

	# Objects can also be modified directly by passing kwargs to to the update_x() method for the object.
	# Valid keywords are parsed and safely converted using psycopg's built in SQL library and used to construct the appropriate query.
	# This is NOT generated sql per se. 
	base.update_project(project, name='example_3')
```

The choice to write our own abstraction layer was very deliberate; there are well documented issues with ORMs such as sqlAlchemy when considering complex relationships and performance scaling for complex multi-user applications. The goal was to as closely emulate the ease of use of an ORM while avoiding the massive overhead and inefficient generated SQL statements. We did not make a better ORM, we made a high performance specialized abstraction layer specifically for this project.

## Deployment

### Acknowledgement

At this early stage in development parts of the set up process remains manual. For example, the initialization process of the database schema is not fully integrated, however a detailed ER diagram can be found on [dbdiagram.io](https://dbdiagram.io/d/Pronghorn-68542f3bf039ec6d36042887). As we progress torwards a more feature complete product we will begin to automate more of the installation process. 

This folder (annotation_software) contains a set of *container files* and *YAML Compose* files that are designed to *hopefully* automate most of the deployment process. Each major component gets it's own container managed using any OCI compliant container orchestration tool. Before composing our containers we must provide the nessacary *secrets* to the orchestration tool. *Be sure to have read the major components section to understand exactly what it is that you are deploying.*

### Requirements

* **Some Computer, Somewhere:** Thanks to our microservice architecture, this tool can be hosted on one bigger computer, or a few smaller computers. This guide assumes you will be using one big computer. It will be up to the user to alter the compose files if they wish to alter the configuration. There are no plans for any sort of install utility as of now.
  
* **Podman and Podman-Compose **OR** Docker and Compose Version:**
	* *podman: 5.7.1*
  	* *podman-compose: 1.5.0*
  	* *docker: 28.3.3* -- Needs checked 
  	* *docker compose: 2.39.1* -- needs checked

### Secrets

Below is a list of *secrets* that must be provided to the application in order for it work correctly. These secrets should be placed inside of a *.env* file in the same directory as the compose files. These secrets must either sourced or produced by the end user for their instance of the application. Note that the entirety of this application can be hosted on-prem, in the cloud, or in a hybrid structure, where you choose to host components will determine how you source quite a few of these secrets. 

* **APPLICATION_URL** -- This is the url the application will be served from. 

* **SECRET_KEY** -- The secret key is used by *flask_session* to cryptographically sign user session tokens to protect against common types of attacks such as Cross Site Request Forgery (CSRF) and ensure *cookie* integrity. This key is simply a unique, random string with a high degree of *entropy* that should not be reused between deployments. Reccomending a source to generate this key would be counter productive, and eventually we will implement a system for auto-generating this key for you.
  
* **VALKEY_HOST** -- The valkey host secret stores the URL for the valkey instance. If your database is one of the containers then you can simply use the name of the container. 

* **VALKEY_PASS** -- The valkey pass is used to control access to the cache server. Even if your valkey cache is on-prem it is still important to keep it secure.

* **AWS_ENDPOINT_S3** -- This secret stores the URL for your S3 compliant object storage provider of choice. Note that you are not required to use AWS, but you can if you want to.

* **DB_HOST** -- This secret stores the URL for the postgres database. If your database is one of the containers then you can simply use the name of the container.

* **DB_USER** -- This is the user in the database that will be used by the API to access data.

* **DB_PASS** -- This is the password associated with the above user.

* **DB_NAME** -- This is the name of the database.

* **AWS_ACCESS_KEY_ID** -- This is a key provided by your S3 compliant storage provider.

* **AWS_SECRET_ACCESS_KEY** -- This is another key provided by your S3 compliant storage provider. 

## Local development mode set up

Our software is designed to be ran in an enterprise environment consisting of multiple servers, this is largely due to the sheer volume of data its designed to handle. In order to scale out who can test and contribute to our software we have produced a set of containers built to be ran on a single host. Note that an internet connection is still required as we determined virtualizing a ceph cluster on the average laptop would somewhat- entirely futile. To get around this we have made a publicly accessible sampleset of imagery and a directory archive of a database relevant to those images available publicly. 

To run the local dev environment you must have a container orchestration tool installed on your system. The reccomended container orchestration platform is Podman with Podman-Compose. However, note that there currently is an issue on intel based macbooks that cause the podman machine to hang indefinitey, so intel mac users are reccomended to use docker. The commands are the same for both tool. Note that for both windows and macOS users a virtualization capable computer is required since those operating systems still do not support native containerization. 

After cloning down the repository the first thing you must do is create a .env file in the root of the directory. See [secrets](https://github.com/benkoger/pronghorn-census/edit/devel/README.md#secrets) for information on how to populate this. Please note that parameters relating to ssl should not be set for the local dev server, unless you have a set of certificates handy and wish to go the extra mile. 

Once you have a propperly populated .env file standing up the environmnet should go off without a hitch. 

### Linux & Applie Silicon Mac systems running Podman

```sh
	podman compose --f development.compose.yml up -d
```

### Intel based Mac systems running Docker

```sh
	docker compose --f development.compose.yml up -d
```

### Windows system 

**Important:** _Windows may automatically convert the restore.sh script in the local_db directory to use **CRLF** insead of **LF** ensure that this file is restored to use **LF** or never converted at all. Additional for some reason Windows podman's file flag uses one dash instead of two. _

```powershell
	podman compose -f production.compose.yml up -d
```

### Post orchestration reccomendations 

It is reccomended for development purposes to maintain a python virtual environment on your development system built from the included requirements.txt if you are using a python LSP like Pylane or Pyright. 


### Linux & MacOs (traditional venvv)

```sh
	# create a virtual environment (please don't push this to our repo)
	python -m venv .venv

	# active the virtual environment
	source .venv/bin/activate

	# install requirements
	pip install -r requirements.txt
```

### Windows

```powershell
	# create a virtual environment (please don't push this to our repo)
	python -m venv .venv

	# active the virtual environment
	.\\venv\\Scripts\\Activate.ps1

	# install requirements
	pip install -r requirements.txt
```

_Don't forget to point your LSP to this new environent for code completion._
It is also reccomended that you 


## Production set up

This section is out of date and needs rewritten. (Michael)

### Podman
In the same directory as production.compose.yml, run this command
```bash
	podman-compose up -d
```

### Docker
In the same directory as production.compose.yml, run this command
```bash
	docker compose up -d
```

## Using the app

### *This content is subject to change, components may be added, modified, or removed as they are developed.*
As previously stated in this readme, the front end for this project is an SPA (Singe Page Application) built with VueJS using their built in Vue-Router plugin. Single page applications are advantages as they reduce the number of requests made to the server for content. This application is lazy loaded, making it a middle ground between a true SPA and a traditional webpage, components are loaded on an as needed basis and then cached in the browser to avoid further requests to the server. This app also makes use of a global state Vue plugin known as [Pinia](https://pinia.vuejs.org), trading some memory consumption for reduced trips to the server. It is important to note that architecturally speaking the frontend is divorced frorm the API layer, meaning it can be hosted on a separate server. Another cool feature is the use of dynamic routes, meaning URLS are created on the fly by the webapp to allow you to access any component with any selection provided your user has access to the nedded data. 

### Authentication
All users must properly authenticate in order to access the project. Currently this project uses a secret token based authentication system for strictly local users. Each user is given a unique high-entropy randomly generated token used to authenticate into the application. The eventaul plan is to replace this with robust token exchange systsem detailed in Oauth2. 

### Dashboard
The dashboard is the first *component* (or page) loaded on a users first time login. The dashboard will display different content based on the user's *role*. The content of any user's dashboard is subject to change as development progresses. Its primary purpose is to be a centralized location to view and manage project's and their statistics. Other potential content includes user's *tasks* and *quick access tiles* to quickly access previously viewed components. 

### Label(er)
The label(er) component is used to produce a small set of preliminary data to build a bootstrap model, from there the user would move to the Auto Cropper module. 

### Auto Cropper
The Auto Cropper utility is the bread and butter of the application. This tool is used to rapidly generate training data for the computer vision models that make up the backbone of the census projects. The actual workflow is preceeded by the user's selection of contextual elements, which enable this tool to be used for move than one type of census on one instance. The user is then presented with small crops of an image that contain a prediction made by a computer vision model along with a toggleable bounding box, ability to change the predictions label (create a propper annotation from a false positive that happens to be a valid object of a different class in the schema). More than one user can use the Auto Cropper at the same time, working on the same *herd unit* and same model's predictions without producing conflicting information. 

### Uploader
The Uploader utility is designed to easily allow a user (with the propper role) to add imagery data to the platform. This tool is designed to robustly handle large volumes of image data, hundreds of gigabytes, with a degree of fault tolerance.

### Statistics *subject to change*
The statistics module is planned to contain a plethora of data visualization tools regarding model performance and other things that are statistical in nature. 

### User
The user module is planned to be another module that has slightly different content based on the user's roles. This module will be the hub for admin users to be able to manage users of their *organization*, assign users to projects, add and remove users, etc. For non admin users this page will simply show the information for thier profile, and be largley static. 

### Settings
The settings module is the eventual home for all configurable options for a user's account. Its pretty standard.
