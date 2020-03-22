CREDENTIALS_DIRECTORY=auth
DIRECTORIES=$(CREDENTIALS_DIRECTORY) celery/out celery/processed celery/results photosets photosets-complete photosets-queue
FLICKR_CREDENTIALS_DATA=$(CREDENTIALS_DIRECTORY)/flickr_credentials.dat
GOOGLE_TOKEN_DATA=$(CREDENTIALS_DIRECTORY)/google_token.json
GOOGLE_CREDENTIALS_DATA=$(CREDENTIALS_DIRECTORY)/google_credentials.json

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build: $(DIRECTORIES) ## Set up the app ready to run
	docker-compose build

build_migration_list: $(FLICKR_CREDENTIALS_DATA) ## Build the photos migration list
	docker-compose start redis
	docker-compose run app python build_migration_photos_list.py

create_album_cache: $(GOOGLE_TOKEN_DATA) ## Build google photos album cache
	docker-compose run app python create_album_cache.py

create_migration_tasks: ## Create migration tasks for each photo in the photosets in each pickle file photosets-queue
	docker-compose run app python create_migration_tasks.py

run_migration_tasks: ## Run the migration tasks that have been created
	docker-compose run app celery -A celery_migration_app worker --loglevel=debug --concurrency=1 -E

$(DIRECTORIES): ## Create the directories required to run the app
	mkdir -p $@

$(FLICKR_CREDENTIALS_DATA): | $(CREDENTIALS_DIRECTORY) ## Set up authorisation to read flickr account
	docker-compose run app python build_flickr_verifier.py

$(GOOGLE_TOKEN_DATA): | $(CREDENTIALS_DIRECTORY) $(GOOGLE_CREDENTIALS_DATA) ## Set up authorisation to write to google photos account
	docker-compose exec app python oauth.py

$(GOOGLE_CREDENTIALS_DATA): | $(CREDENTIALS_DIRECTORY) ## Set up Google API credentials
	$(error "\
You need to set up your access to the Google Photos API. Google's https://developers.google.com/photos/  \
for the API has a number of useful guides that will help you get set up. You need to set up a project and user with  \
oauth2 access to your Google Photos library, so that in the end you end up with a ```google_credentials.json``` file" \
)
