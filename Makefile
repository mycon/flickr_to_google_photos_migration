DIRECTORIES=auth celery/out celery/processed celery/results photosets photosets-complete photosets-queue

build: $(DIRECTORIES) ## Set up the app ready to run
	docker build .
	
$(DIRECTORIES): ## Create the directories required to run the app
	mkdir -p $@

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)


