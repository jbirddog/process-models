
MY_USER := $(shell id -u)
MY_GROUP := $(shell id -g)
ME := $(MY_USER):$(MY_GROUP)

SPIFF_ARENA_DIR := ../../sartography/spiff-arena
BPMN_SPEC_DIR := $(shell pwd)/bpmn

DOCKER_IMG := process-models
IN_DEV := docker run -it -v .:/app $(DOCKER_IMG)

all: img-start

img:
	docker build -t $(DOCKER_IMG) .

start:
	$(IN_DEV) python scripts/gen.py

img-start: img start
	@/bin/true

sh:
	$(IN_DEV) /bin/sh

take-ownership:
	sudo chown -R $(ME) .

check-ownership:
	find . ! -user $(MY_USER) ! -group $(MY_GROUP)

run-editor: stop-editor
	cd $(SPIFF_ARENA_DIR) && \
		SPIFF_EDITOR_URL_PATH=/process-groups/test-cases \
		./bin/run_editor $(BPMN_SPEC_DIR)

stop-editor:
	cd $(SPIFF_ARENA_DIR) && ./bin/stop_editor

update-editor:
	cd $(SPIFF_ARENA_DIR) && ./bin/update_editor

.PHONY: img start img-start \
	sh \
	take-ownership check-ownership \
	run-editor stop-editor update-editor
