# Image credits

The demo catalogue (`make seed-demo`) shows one photo per sample vehicle. Every photo comes
from [Wikimedia Commons](https://commons.wikimedia.org/) under a free licence and is loaded from
Wikimedia's servers as its 960px thumbnail; nothing is copied into this repository. Vehicle
cards crop each photo to a fixed aspect ratio. Each photo keeps its own licence, listed below.

| Vehicle | Photo | Author | Licence |
| --- | --- | --- | --- |
| Tata Nexon | [Tata_Nexon_Blue_Dual_Tone.jpg](https://commons.wikimedia.org/wiki/File:Tata_Nexon_Blue_Dual_Tone.jpg) | Keithkberger | Public domain |
| Mahindra XUV700 | [2021_Mahindra_XUV700_2.2_AX7_(India)_front_view.png](https://commons.wikimedia.org/wiki/File:2021_Mahindra_XUV700_2.2_AX7_(India)_front_view.png) | DriveSpark | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) |
| Hyundai Creta | [2021_Hyundai_Creta_SX(O)_CRDi_(India)_front_view.jpg](https://commons.wikimedia.org/wiki/File:2021_Hyundai_Creta_SX(O)_CRDi_(India)_front_view.jpg) | Dairokkan9 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Maruti Suzuki Swift | [2018_Suzuki_Swift_SZ5_Boosterjet_SHVS_1.0_Front.jpg](https://commons.wikimedia.org/wiki/File:2018_Suzuki_Swift_SZ5_Boosterjet_SHVS_1.0_Front.jpg) | Vauxford | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Honda City | [Honda_City_(fifth_generation)_facelift.jpg](https://commons.wikimedia.org/wiki/File:Honda_City_(fifth_generation)_facelift.jpg) | Jason Lawrence from New York | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) |
| Toyota Hilux | [Toyota_HiLux_GR_Sport_1X7A7281.jpg](https://commons.wikimedia.org/wiki/File:Toyota_HiLux_GR_Sport_1X7A7281.jpg) | Alexander-93 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Kia Carnival | [2021_Kia_Carnival_SXL.jpg](https://commons.wikimedia.org/wiki/File:2021_Kia_Carnival_SXL.jpg) | Chanokchon | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
| Ford Mustang | [2018_Ford_Mustang_GT_5.0_Front.jpg](https://commons.wikimedia.org/wiki/File:2018_Ford_Mustang_GT_5.0_Front.jpg) | Vauxford | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |

`backend/tests/test_seed_demo.py` fails if a sample's photo is missing from this table, so
update it whenever `SAMPLE_LISTINGS` in `backend/app/scripts/seed_demo.py` changes.
