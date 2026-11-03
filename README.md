# tonies (Toniebox) für Home Assistant

Inoffizielle Home-Assistant-Integration für die Toniebox-Einstellungen aus der **mytonies-Cloud** (my.tonies.com).
Kein TeddyCloud, kein Flashen – die Integration spricht dieselbe API wie die Webseite.

> **Hinweis:** Die API ist nicht öffentlich dokumentiert und kann sich jederzeit ändern. Nutzung auf eigene Gefahr; dieses Projekt steht in keiner Verbindung zur tonies GmbH.

## Funktionen

Pro Toniebox im Haushalt wird ein Gerät mit diesen Entitäten angelegt:

| Entität | Typ | Beschreibung |
|---|---|---|
| Maximale Lautstärke | select | 25 / 50 / 75 / 100 % |
| Maximale Kopfhörer-Lautstärke | select | 25 / 50 / 75 / 100 % |
| LED | select | Aus / Gedimmt / An |
| Vor- und Zurücksteuern | select | Kapitelrichtung links/rechts |
| Spulen und Klapsen | switch | Beschleunigungssensor |
| Einstellungen übernommen | binary_sensor | `on`, sobald die Box die Einstellungen von der Cloud abgeholt hat |
| Aktiv | binary_sensor | `on`, solange die Box wach ist (WLAN-Präsenz über einen `device_tracker`, z. B. FRITZ!Box); Attribut `last_active` |
| Firmware, Online-Status, Haushalt | sensor | Diagnose |
| Aktualisieren | button | Daten sofort neu laden |

Zusätzlich pro **Haushalt** ein Gerät mit:

| Entität | Typ | Beschreibung |
|---|---|---|
| Tonies | sensor | Anzahl Hörfiguren; Attribut `tonies` mit Titel, Serie, Bild, Sperre |
| Kreativ-Tonies | sensor | Anzahl Kreativ-Tonies |

und pro **Kreativ-Tonie** ein Gerät mit *Freier Speicher* und *Belegter Speicher* (Minuten, Attribut `live`).

Abfrageintervall: 15 Minuten (in den Integrations-Optionen einstellbar, min. 5); nach jeder Änderung sofort.

### Sensor „Aktiv“ – was gerade läuft?

Die Cloud weiß bei der klassischen Toniebox nicht, ob und was gerade gespielt wird. Die Box verbindet sich aber
nur mit dem WLAN, solange sie wach ist. Die Integration sucht deshalb automatisch den `device_tracker` mit der
MAC-Adresse der Box (FRITZ!Box-, UniFi-, Nmap-Integration o. ä.) und bildet daraus den Sensor **Aktiv**
(`on` = Box ist wach / spielt vermutlich, `off` = schläft). Wird kein Tracker gefunden, kann er in den
Integrations-Optionen je Box ausgewählt werden. Welcher Tonie aufliegt, ist damit nicht erkennbar – dafür
braucht es [TeddyCloud](https://github.com/toniebox-reverse-engineering/teddycloud).

## Wichtig: Die Box muss synchronisieren

Die Toniebox ist ein reiner Cloud-Client. Eine geänderte Einstellung landet sofort in der Cloud,
**die Box übernimmt sie aber erst beim nächsten Abgleich** – sicher durch Drücken eines Ohrs
(ca. 3 s, bis ein Ton kommt), ggf. auch beim nächsten Aufwachen aus dem Standby.
Ob die Box den neuen Stand hat, zeigt `binary_sensor.*_einstellungen_ubernommen`.

## Installation

### HACS
1. HACS → Integrationen → ⋮ → *Benutzerdefinierte Repositories*
2. `https://github.com/david120378/tonies-ha` als *Integration* hinzufügen
3. „tonies (Toniebox)“ installieren, Home Assistant neu starten

### Manuell
Ordner `custom_components/tonies` nach `/config/custom_components/` kopieren, Neustart.

### Einrichten
Einstellungen → Geräte & Dienste → Integration hinzufügen → **tonies** → E-Mail und Passwort des mytonies-Kontos.

## Zeitplan (Nachtmodus) – eingebaut

Pro Box gibt es einen Zeitplan, der ohne eigene Automation funktioniert. Alles wird über Entitäten im UI eingestellt
(Geräteseite → Konfiguration):

| Entität | Typ | Standard |
|---|---|---|
| Zeitplan Lautstärke | switch | aus |
| Nacht ab | time | 19:00 |
| Tag ab | time | 07:00 |
| Lautstärke nachts | select | 25 % |
| Lautstärke tagsüber | select | 50 % |
| Zeitplan auch für Kopfhörer | switch | aus |

Ist der Zeitplan an, setzt die Integration zu den beiden Uhrzeiten die maximale Lautstärke in der Cloud. Außerdem wird
beim Einschalten, bei jeder Änderung und nach einem HA-Neustart sofort der zur aktuellen Uhrzeit passende Wert
angewendet, falls er abweicht. Die Einstellungen werden in `.storage` gespeichert und überleben Neustarts.
Zeitfenster über Mitternacht (z. B. 19:00 → 07:00) werden korrekt behandelt.

Wer lieber eine eigene Automation baut, nutzt `select.select_option` auf `select.<box>_maximale_lautstarke`.

## Icon

Das Integrations-Icon liegt in `custom_components/tonies/brand/` und wird von Home Assistant (ab der Version mit
der „Brands“-Komponente, 2026) direkt von dort ausgeliefert – ein Eintrag im zentralen Brands-Repository ist nicht nötig.
Eigenes Bild gewünscht? Einfach `icon.png` (256×256) und `icon@2x.png` (512×512) in diesem Ordner ersetzen und HA neu starten.

## Technik

- Auth: Keycloak `login.tonies.com`, Realm `tonies`, Client `my-tonies`, Password-Grant + Refresh-Token
- API: `https://api.prod.tcs.toys/v2` – `GET /households`, `GET /households/{id}/tonieboxes`, `PATCH /households/{id}/tonieboxes/{boxId}` mit z. B. `{"maxVolume": 25}`; Tonies per `POST /graphql` (`households { contentTonies … creativeTonies … }`)

## Lizenz

MIT
