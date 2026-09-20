# Réveil – intégration Home Assistant

Planificateur de réveil **basé sur des événements**. L'intégration calcule quand
le réveil doit sonner et l'annonce ; ce qui se passe ensuite (lumières, musique,
volets…) est décidé par vos automatisations ou par le blueprint fourni.
Elle est pensée pour cohabiter avec l'alarme de l'iPhone, qui reste active.

Prérequis : Home Assistant 2024.12 ou plus récent.

## Installation

1. Copier `custom_components/reveil/` dans `<config>/custom_components/`.
2. Copier `blueprints/automation/reveil/wake_up.yaml` dans
   `<config>/blueprints/automation/reveil/`.
3. Redémarrer Home Assistant.
4. **Paramètres → Appareils et services → Ajouter une intégration → Réveil.**
   Répéter autant de fois que de réveils souhaités (un appareil par réveil).

## Ce qui est créé pour chaque réveil

| Entité | Rôle |
|---|---|
| `switch` Activé | interrupteur global |
| 7 × `switch` Actif le … | jours où le réveil sonne (par défaut : lundi à vendredi) |
| `time` Heure par défaut | heure utilisée les jours sans surcharge |
| 7 × `time` Heure du … | surcharge par jour ; **vide = heure par défaut** |
| `sensor` Prochain réveil | horodatage du prochain déclenchement |
| `sensor` Début de la phase progressive | horodatage du prochain `reveil_pre_ring` |
| `sensor` Dernier réveil confirmé | horodatage du dernier `reveil_dismissed` |
| `binary_sensor` Sonne aujourd'hui | actif si le réveil est activé aujourd'hui et pas encore confirmé |
| `button` Je suis réveillé | équivalent du service `reveil.dismiss` |

La durée de la phase progressive se règle dans **Configurer** sur l'intégration
(0 = pas de phase progressive).

## Événements

| Événement | Quand |
|---|---|
| `reveil_pre_ring` | X minutes avant l'heure (X = phase progressive) |
| `reveil_ring` | à l'heure du réveil |
| `reveil_dismissed` | à l'appel de `reveil.dismiss` (ou du bouton) |

Données communes : `alarm_id`, `device_id`, `name`.
`reveil_pre_ring` et `reveil_ring` ajoutent `ring_at`, `alarm_time`, `weekday`,
`lead_minutes` ; `reveil_pre_ring` ajoute aussi `remaining_seconds`.
`reveil_dismissed` fournit `ring_at`, `dismissed_at` et `delay_seconds`
(temps écoulé entre la sonnerie et la confirmation, `null` si aucune sonnerie
récente).

Si vous modifiez l'heure alors que vous êtes déjà dans la fenêtre de progression,
`reveil_pre_ring` est émis immédiatement avec un `remaining_seconds` réduit. Au
démarrage de Home Assistant, aucun `reveil_pre_ring` de rattrapage n'est émis.

### Exemple d'automatisation sans blueprint

```yaml
triggers:
  - trigger: event
    event_type: reveil_ring
    event_data:
      name: Réveil semaine
actions:
  - action: media_player.play_media
    target:
      entity_id: media_player.chambre
    data:
      media_content_id: media-source://media_source/local/reveil.mp3
      media_content_type: music
```

## Services

Chaque service se cible par **appareil** ou par **entité** du réveil
(n'importe laquelle : `switch.reveil_semaine_actif_le_lundi` convient).

| Service | Données | Effet |
|---|---|---|
| `reveil.set_time` | `time` seul | change l'heure par défaut |
| | `day` + `time` | surcharge l'heure d'un jour |
| | `day` seul | efface la surcharge de ce jour |
| `reveil.set_days` | `days` (liste) | active exactement ces jours |
| `reveil.dismiss` | – | émet `reveil_dismissed` |

`day` prend les valeurs `monday` … `sunday`.

### Depuis l'app Raccourcis (iPhone)

Avec l'action **« Appeler le service »** de l'app Home Assistant :

- Service : `reveil.set_time`
- Données : `{"entity_id": "switch.reveil_semaine_actif_le_lundi", "day": "monday", "time": "06:30:00"}`

Les surcharges par jour ne peuvent pas être effacées depuis l'interface
(un sélecteur d'heure n'a pas de valeur « vide ») : utilisez `reveil.set_time`
avec `day` seul.

## Blueprint

**Paramètres → Automatisations → Blueprints → « Réveil – lumière progressive et
actions de sonnerie ».** Vous choisissez le réveil, les lumières, les
luminosités de départ et d'arrivée, une action libre à la sonnerie, et
éventuellement une entité de présence. La montée de lumière utilise
`transition = remaining_seconds`, donc elle se termine à l'heure du réveil.

## Carte Lovelace (sans JavaScript)

À coller dans une vue en mode YAML. Les identifiants d'entités sont donnés pour
un réveil nommé **« Réveil semaine »** en français ; adaptez-les à vos entités
réelles (Paramètres → Entités).

```yaml
type: vertical-stack
cards:
  - type: tile
    entity: sensor.reveil_semaine_prochain_reveil
    name: Prochain réveil
  - type: grid
    columns: 7
    square: false
    cards:
      - type: tile
        entity: switch.reveil_semaine_actif_le_lundi
        name: Lun
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_mardi
        name: Mar
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_mercredi
        name: Mer
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_jeudi
        name: Jeu
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_vendredi
        name: Ven
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_samedi
        name: Sam
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
      - type: tile
        entity: switch.reveil_semaine_actif_le_dimanche
        name: Dim
        vertical: true
        hide_state: true
        tap_action:
          action: toggle
  - type: entities
    entities:
      - switch.reveil_semaine_active
      - time.reveil_semaine_heure_par_defaut
      - time.reveil_semaine_heure_du_lundi
      - time.reveil_semaine_heure_du_mardi
      - time.reveil_semaine_heure_du_mercredi
      - time.reveil_semaine_heure_du_jeudi
      - time.reveil_semaine_heure_du_vendredi
      - time.reveil_semaine_heure_du_samedi
      - time.reveil_semaine_heure_du_dimanche
      - binary_sensor.reveil_semaine_sonne_aujourd_hui
  - type: button
    entity: button.reveil_semaine_je_suis_reveille
    name: Je suis réveillé
    show_state: false
    tap_action:
      action: toggle
```

## Migration depuis les helpers manuels

| Avant | Maintenant |
|---|---|
| 7 × `input_boolean` (jours) | 7 × `switch` Actif le … |
| `input_datetime` heure du réveil | `time` Heure par défaut (+ surcharges par jour) |
| `input_datetime` heure de réveil effectif | événement `reveil_dismissed` (`dismissed_at`) et capteur Dernier réveil confirmé |
| capteur binaire « sonne aujourd'hui » | `binary_sensor` Sonne aujourd'hui |

## Tests

La logique de calcul du prochain réveil (`schedule.py`) n'a aucune dépendance
à Home Assistant et est testée par `python tests/test_schedule.py`.
