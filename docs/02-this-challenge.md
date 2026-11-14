# This challenge

**Full name:** Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars

**Official page:** [spaceappschallenge.org challenge](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/)

**Intro video:** [YouTube, NASA topic introduction](https://www.youtube.com/watch?v=Qiz_Pny-xjo)

Tags on the challenge include Earth science, planets and moons, software, and space exploration. It is open to beginner, intermediate, and advanced teams. A simple project can score well if the science is honest. A complex model does not score well if the judge cannot see what data went in.

## The idea in one minute

NASA chooses landing sites and base sites with more than a photo. Teams look at the shape of the ground, the rocks, the temperature, the light, the ice or minerals, the dust, and whether a robot or a person can work there.

Before flight, they practice in places on Earth that share **some** of those traits. Deserts, polar ground, volcanoes, impact craters, and caves are the usual classrooms. Atacama, Haughton Crater, and Death Valley are famous examples. They are useful, and they are still not fully measured. None of them is a perfect copy of the Moon or Mars.

The challenge asks for three things:

1. Use open Earth data together with open Moon and Mars data.
2. Find and describe one or more places, environments, or processes on Earth that could help prepare for a **permanent Moon base** or a **future Mars landing and exploration site**.
3. Say what is similar, how similar it is, what is different, and how the Earth site would actually be used.

A written report is allowed. So is a map, an app, a similarity score, a machine-learning search, or a story. The format is free. The reasoning is not.

## What “analog” means here

An analog is a stand-in. It is an Earth place or an Earth process that lets you study one piece of another world.

A good analog is specific. “This valley is dry and rocky, so it is Mars” is not specific. This is specific: “This valley matches the slope and the loose, vegetation-free ground of a chosen crater rim, so a team could test wheel slip there. It does not match the air, the gravity, or the radiation, so it cannot test a spacesuit or a landing engine.”

Two places can look alike and still be bad analogs. A salt flat can look like a Mars photo and still be the wrong rock, the wrong slope, and the wrong temperature for the test you care about. Data is how you tell those apart.

The match can be partial. NASA says so. A site can be a strong geology analog and a weak temperature analog. The job is to label the match, not to force a score of 100.

## The dimensions NASA asked teams to consider

You do not have to use every row. You do have to know which rows you used, and which rows you left out on purpose.

| Dimension | What to look at | Why a mission cares |
| --- | --- | --- |
| Geology and surface materials | Rock type, minerals, grain size, salts, volcanic ash | Instruments, sampling, and “what is this ground made of?” |
| Terrain | Elevation, slope, roughness, craters, ridges, canyons | Landing, driving, construction, line of sight |
| Temperature, light, and extremes | Day–night swing, polar night, sun angle, UV | Power, thermal design, human work hours |
| Water, ice, and other resources | Ice, permafrost, hydrated minerals, brines | Drinking water, fuel, and drilling practice |
| Dust, wind, and erosion | Dust storms, dunes, abrasion | Solar panels, seals, cameras, lungs of machines |
| Biology and habitability | Extremophiles, barren soil, biosignatures | How to search for life, and how to avoid contaminating a sample |
| Subsurface | Caves, lava tubes, mines, buried ice | Shelter from radiation, and a stable temperature |
| Operations | Landing, mobility, navigation, robots, construction | The test you would actually run on Earth |

Also think about **processes**, not only pins on a map. Sediment moving in wind, a dust storm, a lava flow, ice cracking, or water altering rock can teach a process that happens on Mars today or that happened on Mars or the Moon in the past.

Scale matters. A whole desert is usually too big to be one analog. A crater, a valley, a lava field, a cave, or a small patch inside a famous region is often the real match.

## What the challenge is asking us to avoid

- Rediscovering only Atacama, Antarctica, Iceland, Hawaii, Death Valley, or Haughton and stopping there. Those places are valid comparisons. They are a weak **entire** project if nothing new is measured or found.
- Treating visual similarity as the result. A red photo is not a geology result.
- Claiming one Earth site matches the Moon or Mars in every way.
- Ignoring Earth’s limits: gravity, vacuum, radiation, and air.
- A method with no site, or a site with no method. The brief allows either a single compelling place or a search method. The strongest weekend project has a method **and** at least one place it found.

## A weak answer and a strong answer

**Weak.** A slide that says “the Thar Desert looks like Mars” next to two photos, with no dataset, no target site on Mars, and no statement of what would be tested there.

**Strong.** A page that says:

- The Moon target is a named south-pole ridge region used in Artemis planning, with a slope range, a lighting pattern, and cold traps nearby.
- The Mars target is a named region, with one process called out (ground ice, or dust and salts).
- Earth was screened with named datasets for slope, bareness, temperature, and dryness.
- Site A is a global-screen discovery candidate; Site B is the best cell inside a defined Atacama-region hold-out, scored with the same method. Neither is presented as a validated analog.
- A separate, target-specific slope check shows whether either patch is inside the named lunar terrain band. Keep that check outside a score whose global slope data are missing.
- Gravity, vacuum, radiation, and air are listed as non-matches.
- The last section proposes a paired rover-mobility trial and says what would still need laboratory testing.

That shape hits relevance, validity, creativity, impact, and presentation at the same time.

## How this team will answer it

The working project is **Mission Analog Readiness**. Its core is a partial-match finder, described step by step in [05-master-plan.md](05-master-plan.md).

- Two targets, not “the whole Moon” and “the whole Mars.”
- A coarse global screen so the result is not a place chosen only because it is famous.
- One global discovery cell, plus the best cell in a held-out Atacama-region box scored through the same function.
- A direct lunar-slope comparison kept separate from the three-feature proxy score.
- A short dossier with three headings: **matches**, **breaks**, **how a mission would use it**.
- A map and a seven-slide demo.

The project’s contribution is not a novel distance formula or a claim that one site is “the best analog.” It makes the reviewer-facing workflow explicit: globally screen, compare against a held-out region, check a mission-relevant terrain measure directly, and turn the result into a falsifiable field-test proposal. The current evidence favors Vinchina for an in-band mobility study; Kunlun supplies a contrasting lower-slope case. Access and field validation remain open.

## The sentence to keep on the title slide

Earth cannot be the Moon or Mars. It can be a measured rehearsal for one hard part of going there, if we say which part, and if we show the data.
