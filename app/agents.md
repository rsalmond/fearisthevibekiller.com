# Python

at all times prefer clarity and readability over everything else

don't monkey patch any 3rd party libraries, if there's a version problem find a way to solve it or find an alternative library

all functions should have docstrings that clearly and succintly describe the _purpose_ of the function

when naming functions and methods, prefer names that describe what is being done, not how it is being done

all cli's must print clear and succint explanations for command line arguments, options, and flags

all cli arguments must be documented in a dedicated section in the readme
all config file directives which control the applications behaviour must be documented a dedicated section in the readme
all env vars which control the applications behaviour must be documented a dedicated section in the readme

for complex mathematical expressions (anything with more than two or three operations) document what's happening in plain english

## Testing

unless otherwise directed, always go ahead and run the test(s) you have just created or modified

# Docker

at all times prefer an efficient build for the Dockerfile
- system deps installed first
- app requirements afterwards
- source code last

never rebuild the image while iterating unless you need a new dep or requirement, just mount the source code as a volume and run
