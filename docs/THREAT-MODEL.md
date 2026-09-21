# Threat Model

## Gegen wen OnionCall schützen soll

- Gegen eine Kommunikationsgegenstelle, die deine direkte öffentliche IP erfahren möchte.
- Gegen passive Beobachtung des Inhalts zwischen den Endpunkten.
- Gegen Netzwerkmanipulation des OnionCall-Anwendungsprotokolls.
- Gegen versehentliche direkte TCP-Verbindungen durch die bekannten Diagnosepfade.
- Gegen Identitätswechsel eines Kontakts nach dem ersten erfolgreichen Pinning.

## Nicht vollständig abgedeckt

- globaler passiver Beobachter / Timing-Korrelation,
- kompromittiertes Endgerät,
- physischer Zugriff,
- bösartige oder verwundbare System-Audio-Komponenten,
- vollständige Verfügbarkeitsgarantie gegen DoS.
