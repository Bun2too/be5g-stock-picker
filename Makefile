SHELL := /bin/bash

.PHONY: setup dev test package clean

setup:
	./scripts/setup.sh

dev:
	./scripts/dev.sh

test:
	./scripts/test.sh

package:
	./scripts/package.sh

clean:
	rm -rf apps/web/dist build
