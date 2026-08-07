# OWNd — Roadmap

Stato al 2026-08-07 · stabile **v1.0.10** · in validazione **v1.0.11-beta**

## Stato della beta 1.0.11

La beta estende il parsing della termoregolazione emerso da un impianto BTicino 3550 / MyHomeServer1:

- separa correttamente le dimensioni 12 e 14, evitando che lo stato locale/effective e lo stato centrale si sovrascrivano;
- espone i valori grezzi della dimensione 13 e riconosce lo stato `local_override`;
- interroga esplicitamente la dimensione 19 durante l'aggiornamento completo;
- allinea la versione esposta a runtime con i metadata del pacchetto.

La regressione automatica comprende sei test dedicati alla termoregolazione. Ruff, mypy e i test unitari vengono eseguiti dalla CI a ogni push e pull request.

## Prima della promozione a v1.0.11

- Validazione dei nuovi frame su un impianto reale con centrale 3550 / MyHomeServer1.
- Breve soak test sull'impianto MH201 già usato come riferimento, per escludere regressioni nel traffico ordinario.
- Promozione coordinata con MyHOME 0.9.87, che contiene la migrazione necessaria alla nuova rappresentazione del produttore della centrale.

## Hardening successivo

- Rendere strettamente *fail-closed* la negoziazione autenticata: una risposta inattesa dopo l'invio della password deve chiudere la sessione invece di poter essere interpretata come successo. La modifica va sviluppata e validata in una beta separata, perché interessa direttamente l'accesso al gateway.
- Ampliare la copertura dei parser solo quando sono disponibili frame reali e hardware su cui verificare il comportamento.
