# Submission checklist

Use this on Sunday evening. The deadline is **11:59 pm Delhi time on 15 November 2026**. Finish the form by **10:30 pm**.

Submit from the **Project** tab on the Mid-Sem Make Up team page at [spaceappschallenge.org](https://www.spaceappschallenge.org/). The team owner edits the page. Email and chat apps are not a submission.

## Before you paste anything

- The repository is public.
- The slide file is public. Test it in a private or incognito window.
- The map or result page opens in that same private window.
- Every number on the slides is the same number as in `RESULTS.md` and `sources.csv`.
- The project page text is English.
- Every person on the team is registered on the team page, and the team has at most six people.
- Generated images or video, if any, carry a visible watermark such as `Image: generated with [tool name]`. Do not draw a NASA logo, the NASA flag, or a mission patch into generated art.

## Form fields

Write in short sentences. Judges skim.

### Project name

Partial Match

Use another name if the team prefers one. Keep it short.

### High-level summary

Paste and edit the brackets.

> Mission Analog Readiness screens June 2024 Earth observations against the Shackleton–de Gerlache connecting ridge and documents the Arcadia Planitia ground-ice target. Among two compared Earth patches, Vinchina has the lower three-proxy score and a median slope inside the lunar target band; Kunlun is a lower-slope comparison. These are candidates for a terrain-only mobility study, not validated Moon or Mars analogs. The project identifies the missing Earth ice comparison and states where Earth cannot stand in for otherworldly conditions.

### Project demo

Link to the seven-slide PDF or slide deck. A video is allowed only if it is **30 seconds or shorter** and, if it is not in English, has English subtitles. The slides are the safer demo.

### Final project

Link to the public repository, or to the result page if the report is the product. If both exist, put the page a judge should open first in this field, and put the other link in Project Details.

### Project details

Cover these points in order:

1. The challenge question you answered: finding Earth rehearsals for a Moon base site and a Mars site, not a place that looks red or grey.
2. The two targets, with coordinates.
3. The Earth measurements and the datasets.
4. Site A and Site B, separating the three-proxy score from the later direct slope check.
5. The paired rover-mobility trial proposed for Vinchina and Kunlun, labeled as not yet run.
6. How to rerun the screen, or how the manual comparison was done.
7. What you would add with another week.

### Use of Super Intelligence

NASA’s 2026 forms ask about Super Intelligence tools. List what was actually used. Example shape, edited to be true:

> Cursor and Grok were used to draft the project notes, outline the screen, and edit text. Dataset values, site scores, and map outputs were computed from the cited NASA and partner data and checked in the repository. No measurements were taken from a model’s memory. Generated images: [none, or list them and say they are watermarked].

If a tool wrote code, say so. If no such tool was used, write `No Super Intelligence tools used.`

### NASA data and partner data

List only data that did work in the result. Include at least one Resources-tab source. Copy the name and the URL from [04-data-resources.md](04-data-resources.md). A minimum honest list looks like this, after you delete anything you did not open:

- NASA Worldview — browsed [layers] for [sites] — https://worldview.earthdata.nasa.gov/
- NASA Earthdata Search — downloaded [dataset name and version] — https://search.earthdata.nasa.gov/
- PDS LRO / Diviner or LOLA — [what you read] — https://pds-geosciences.wustl.edu/missions/lro/
- Partner data, if used — name, what it measured, URL

### References

Add everything that is not your measurement:

- Articles or NASA pages used to pick the Artemis region or the Mars region
- Software libraries (Python, Folium, rasterio, and so on)
- The Super Intelligence tools named above
- Images, including unaltered NASA images, with credit
- This planning folder only if you want it public; it is not a substitute for the result

## The seven slides

One idea per slide. Large type. A figure with a caption beats a paragraph.

| Slide | Title | What must be on it |
| --- | --- | --- |
| 1 | Mission Analog Readiness | Team name, Delhi, challenge name |
| 2 | The decision | State the mission question and that this is a field-study prescreen, not a flight-ready analog |
| 3 | Two targets, two evidence levels | Name the Moon ridge and Mars ground-ice target; distinguish published Mars target evidence from project measurements |
| 4 | A screen, then a direct check | Name the three proxy datasets, explain that slope is not in the score, and compare separately with the lunar slope band |
| 5 | The result changes the recommendation | Compare the scores and measured slopes; clearly name the stronger candidate and the contrasting site |
| 6 | A testable next step | Give a paired mobility-trial design, measurable outcomes, and state that it has not been run |
| 7 | What is still unknown | Confidence, cell scale, missing Earth ice comparison, links, and repository |

## Private-window test

Do this after submit, and again if you change a link.

- [ ] A fresh private/incognito visit opens the dashboard’s 90-second review; after dismissing it, the **90-sec review** button reopens it
- [ ] Project page loads while logged out
- [ ] Demo link loads without a request for access
- [ ] Final project link loads without a request for access
- [ ] The README result matches slide 5
- [ ] The NASA data field names a Resources-tab dataset you actually used
- [ ] The SI field matches the tools used to produce the repo
- [ ] The team page shows the project as submitted, not as a draft

## If a judge asks one hard question

Answer with the table, not with a new claim.

- “Why this Earth site?” Because it ranked on these measured features, and the famous site scored this way on the same features.
- “Is it the Moon?” No. It matches the listed features and fails gravity, vacuum, and radiation.
- “How sure are you?” Give the confidence line from the dossier and the largest missing dataset.
- “What would you do there?” Give the single rehearsal from the dossier, then stop.
