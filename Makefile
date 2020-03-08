CREDENTIALS_DIRECTORY=auth
DIRECTORIES=$(CREDENTIALS_DIRECTORY) celery/out celery/processed celery/results photosets photosets-complete photosets-queue
FLICKR_CREDENTIALS_DATA=$(CREDENTIALS_DIRECTORY)/flickr_credentials.dat

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build: $(DIRECTORIES) ## Set up the app ready to run
	docker-compose build

build_migration_list: $(FLICKR_CREDENTIALS_DATA) ## Build the photos migration list
	docker-compose start redis
	docker-compose run app python build_migration_photos_list.py

$(DIRECTORIES): ## Create the directories required to run the app
	mkdir -p $@

$(FLICKR_CREDENTIALS_DATA): $(CREDENTIALS_DIRECTORY) ## Set up authorisation to read flickr account
	docker-compose run app python build_flickr_verifier.py
