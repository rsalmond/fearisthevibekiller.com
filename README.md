# [Fear Is The Vibe Killer](https://fearisthevibekiller.com/)

This is a [quarto](https://quarto.org/) site hacked together with a little python. These [event files](./_events/) get sorted into one of two [templates](./_templates/) by the [builder script](./scripts/builder.py). If the date in the event filename is in the future (or is today) it gets added to [index.qmd](./index.qmd), if it's in the past it goes into [past.qmd](./past.qmd). The whole process [runs every night in an action](https://github.com/rsalmond/fearisthevibekiller.com/actions/workflows/render.yaml) and if there's a change a PR gets cut.

New events are added manually for the time being.
