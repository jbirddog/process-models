DOCKER_IMG := process-models

IN_DEV := docker run -it -v .:/app $(DOCKER_IMG)

all: img-gen

img:
	docker build -t $(DOCKER_IMG) .

gen:
	$(IN_DEV) python scripts/gen.py

img-gen: img gen
	@/bin/true

sh:
	$(IN_DEV) /bin/sh

.PHONY: img gen img-gen \
	sh
