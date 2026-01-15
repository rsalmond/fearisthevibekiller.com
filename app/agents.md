# Overall

Everything happens inside a container. This project is intended to produce complete, container images which can be run anywhere.

# Python

at all times prefer clarity and readability over everything else

don't monkey patch any 3rd party libraries, if there's a version problem find a way to solve it or find an alternative library

all classes must have docstrings that clearly and succinctly describe the purpose of the class

all functions and methods must have docstrings that clearly and succintly describe the purpose of the function

when naming functions and methods, prefer names that describe what is being done, not how it is being done

for complex mathematical expressions (anything with more than two or three operations) document what's happening in plain english

all cli's must print clear and succint explanations for command line arguments, options, and flags

unless printing usage help, never print() anything, always log at an appropriate log level

all cli entrypoints must have their own section in the readme
- the purpose of the cli is briefly described
- all cli arguments are documented in a dedicated section in the readme
  - subcommands are listed first (eg. kubectl apply)
  - flags next (eg. kubectl apply -f)
  - options and any other arguments last

- all config file directives which control the applications behaviour must be documented a dedicated section in the readme
- all env vars which control the applications behaviour must be documented a dedicated section in the readme

## Testing

unless otherwise directed, always go ahead and run the test(s) you have just created or modified

# Docker

at all times prefer an efficient build for the Dockerfile
- system deps installed first
- app requirements afterwards
- source code last

never rebuild the image while iterating unless you need a new dep or requirement, just mount the source code as a volume and run


# Useful Commands

## run tests

sudo nerdctl run --rm --env-file /secure/.env -v /app:/app --entrypoint python instagram-event-pipeline -m unittest /app/app/tests/

## show progress

sudo nerdctl run --rm --env-file /secure/.env -v /app:/app --entrypoint python instagram-event-pipeline /app/app/main.py progress

## run extraction

nerdctl run --rm --env-file /secure/.env -e LOG_LEVEL=INFO -v /app:/app --entrypoint python instagram-event-pipeline /app/app/main.py extract-events
