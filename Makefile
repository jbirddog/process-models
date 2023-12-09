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

.PHONY: img start img-start \
	sh
