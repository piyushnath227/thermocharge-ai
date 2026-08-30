# Data and evidence notes

ThermoCharge deliberately separates **real public inputs**, **FortyGuard environmental data**, **model estimates**, and **demonstrated actions**.

## Phoenix pilot charging assets

- EVgo Southgate Center, 7227 S Central Ave, Phoenix, AZ 85042. EVgo's public page lists PHILLIPA (100 kW), AIDY (100 kW), MARQUIS (350 kW), and QUAN (350 kW). https://www.evgo.com/find-a-charger/az/phoenix/7227-s-central-ave-499544/
- EVgo Laveen Village Center, 6260 S 35th Ave, Phoenix, AZ 85041. EVgo's public page lists MARE (100 kW), KIMIKO (100 kW), FELDER (350 kW), and ERMA (350 kW). https://www.evgo.com/find-a-charger/az/phoenix/6260-s-35th-ave-468934/
- DCFC Tracker independently lists Southgate Center as an operational Phoenix EVgo site with six DC fast stalls and a site maximum of 350 kW. https://dcfctracker.com/stations/255437

Coordinates are public-location coordinates for the site, not individual cabinet survey coordinates. All cabinets at a site therefore share the site's thermal tile in this hackathon model.

## Historical heat event

The U.S. National Weather Service Phoenix 2024 climate review reports 118°F in Phoenix on July 5 and July 8, 2024. ThermoCharge uses July 5, 2024 as the historical replay date. https://www.weather.gov/psr/yearinreview2024

## Thermal sensitivity evidence

- EvoCharge's published Integrated DC Fast Charger specification states that maximum charging current decreases 2% for each 1°C increase above +25°C, with an operating range to 50°C. ThermoCharge uses this only as a **public-reference sensitivity proxy**, not as a claim about EVgo's installed hardware. https://evocharge.com/wp-content/uploads/2023/07/DCFC-Integrated-Power-Station-Spec-Sheet-0723.pdf
- ABB's Terra 360 manual states an operating ambient range of -35°C to 55°C and notes derating from 40°C, demonstrating that ambient-temperature derating is a real design consideration across DC fast charging equipment. https://library.e.abb.com/public/d1b28f938964437b8d7068b8b791f4a1/Terra%20360%20Series%202_60-Operation%20and%20installation%20manual-EN-Rev.009.pdf

## Important limitations

- ThermoCharge does not know the specific OEM/model installed behind every public EVgo cabinet in this pilot.
- The capacity estimates are therefore scenario estimates using a transparent reference curve.
- A production system would ingest charger-model metadata and operator/OEM derating curves, then validate them against cabinet telemetry and delivered-power history.
- No real charger is controlled by this project. Rebalancing is an operational recommendation that could be sent to a CPO/CPMS integration in production.
