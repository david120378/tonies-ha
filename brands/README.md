# Icon für die Integrationsliste / HACS

Home Assistant lädt Integrations-Icons nicht aus dem Repository, sondern aus
https://github.com/home-assistant/brands. Damit „tonies“ dort ein Icon bekommt:

1. Fork von `home-assistant/brands`
2. Ordner `custom_integrations/tonies/` anlegen und die vier PNGs aus diesem Verzeichnis hineinkopieren
   (`icon.png` 256×256, `icon@2x.png` 512×512, `logo.png`, `logo@2x.png`)
3. Pull Request stellen – nach dem Merge erscheint das Icon in HA und HACS automatisch

Die Grafik ist eine eigene, schlichte Marke (roter Kreis-Rechteck-Hintergrund, Lautsprecher-Glyphe) –
kein Markenlogo und keine Produktabbildung von tonies.
