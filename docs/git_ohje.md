# Git Commit -viestien käytännöt

Projektissa noudatetaan **Conventional Commits** -muotoa commit-viesteissä. Tämä helpottaa muutoslokin lukemista ja versiointia.

## Viestin muoto
`tyyppi: lyhyt kuvaus`

---

## Yleisimmät tyypit
| Tyyppi | Kuvaus |
| :--- | :--- |
| **feat** | Uusi ominaisuus |
| **fix** | Bugikorjaus |
| **docs** | Dokumentaatio-muutos |
| **style** | Muotoilu (ei vaikuta toimintaan, esim. whitespace, puolipisteet) |
| **refactor** | Koodin uudelleenjärjestely ilman toiminnallista muutosta |
| **test** | Testien lisäys tai muutos |
| **chore** | Ylläpitotehtävät (esim. riippuvuudet, build-skriptit) |

## Hyödylliset lisätyypit
| Tyyppi | Kuvaus |
| :--- | :--- |
| **perf** | Suorituskykyparannus |
| **build** | Build-järjestelmään liittyvät muutokset |
| **ci** | CI/CD-muutokset (esim. GitLab CI, GitHub Actions) |
| **revert** | Perutaan aiempi commit |
| **init** | Projektin alustus |
| **config** | Konfiguraatiot (esim. settings, .env) |
| **deps** | Riippuvuuksien päivitys |

---

## Esimerkkejä
- `feat: add heatmap visualization`
- `fix: correct hour sorting bug`
- `refactor: simplify data pipeline logic`
- `perf: optimize query for large dataset`
- `chore: update dependencies`
- `ci: add GitLab pipeline`
- `docs: update git commit guidelines`
